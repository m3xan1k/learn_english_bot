from enum import Enum, unique
from urllib.parse import urljoin
from typing import List, Dict

import requests
from requests.adapters import HTTPAdapter
from requests.exceptions import ConnectionError
from textblob import TextBlob


from conf import (
    BASE_URL, HTTP_TIMEOUT,
    PROXY
)
from models import User, Pair, UserPair


telegram_adapter = HTTPAdapter(max_retries=3)
session = requests.Session()
session.mount('https://api.telegram.org', telegram_adapter)

HELP_MESSAGE = """
    This bot helps you to learn new english/russian words by adding new pairs of words.
    You'll get notifications with questions you can answer them and bot will check if \
        your answer if correct.
    All interaction with bot is build on paradigms of commands.
    It reminds a REST API(for developers).
    Available commands:
    '/create_pair <english> <russian>' — creates a 'pair' of words and saves it to your \
        dictionary, order of words in 'pair' is not sensitive, bot will try to handle \
        detection of language
    '/update_pair <english> <russian>' — updates existing 'pair' in your dictionary
    '/delete_pair <english> <russian>' — deletes existing 'pair' from your dictionary
    '/show_dict' — displays all your dictionary
    '/answer <english> <russian>' — answer to bot's question, than you'll get a feedback \
        are you right or wrong
    '/help' — displays this help message
    """


@unique
class BotApiUrl(Enum):
    """
    Telegram bot API endpoints
    """
    GET_UPDATES = 'getUpdates'
    SEND_MESSAGE = 'sendMessage'


class Bot:

    # API methods

    @staticmethod
    def get_updates(offset: int or None = None) -> requests.Response:
        """
        Retrieves updates from telegram bot API
        """
        url: str = urljoin(BASE_URL, BotApiUrl.GET_UPDATES.value)
        params = {'timeout': 300, 'offset': offset}
        try:
            response = session.get(url, params=params, timeout=HTTP_TIMEOUT, proxies=PROXY)
        except ConnectionError:
            return None
        return response

    @staticmethod
    def send_message(chat_id: int, text: str) -> requests.Response:
        print(text)
        url: str = urljoin(BASE_URL, BotApiUrl.SEND_MESSAGE.value)
        headers = {'Content-type': 'Application/json'}
        data = {'chat_id': chat_id, 'text': text}
        post_params = {
            'url': url, 'json': data, 'headers': headers,
            'timeout': HTTP_TIMEOUT, 'proxies': PROXY,
        }
        try:
            response = session.post(**post_params)
        except ConnectionError:
            return None
        return response

    # command handlers

    def dispatch_message(self, message: str) -> callable or None:
        """
        Decides what to do with the message, returns action(function)
        """
        if message.startswith('/'):
            command, *_ = message.split()
            print(command)
            return self.map_command(command)
        return 'Command not recognized'

    def map_command(self, command: str) -> callable:
        """
        Maps command-message to action(function)
        """
        command_mapper = {
            '/create_pair': self.create_pair,
            '/update_pair': self.update_pair,
            '/delete_pair': self.delete_pair,
            '/show_dict': self.show_dictionary,
            '/answer': self.answer,
            '/help': self.help,
        }

        return command_mapper.get(command)

    # business logic

    @staticmethod
    def show_dictionary(chat_id: int, *args, **kwargs) -> str or None:
        query: List[Dict] = (
            Pair
            .select(Pair.russian_word, Pair.english_word)
            .join(UserPair)
            .join(User).where(User.chat_id == chat_id)
            .dicts()
        )
        answer = ''
        for pair in query:
            row = f"{pair['russian_word']}: {pair['english_word']}\n"
            answer += row
        print(answer)
        return answer

    def create_pair(self, chat_id: int, user_name: str, message: str) -> str:
        """
        Saves new pair of words and binds it to user
        """
        command, *pair = message.split()
        if len(pair) != 2:
            return "'/create_pair' command takes 2 args(russian and english word)"
        pair: List[str] = [word.lower().strip() for word in pair]
        russian, english = self.determine_language_pairs(pair)
        try:
            user = User.get(chat_id=chat_id)
        except User.DoesNotExist:
            user = User.create(chat_id=chat_id, name=user_name)
        db_pair, _ = Pair.get_or_create(
            russian_word=russian,
            english_word=english,
        )
        new_user_pair, status = UserPair.get_or_create(user=user, pair=db_pair)
        if status:
            return 'Created'
        return 'Exist'

    def update_pair(self, chat_id: int, user_name: str, message: str) -> str:
        """
        Updates pair of words for user
        """
        command, *pair = message.split()
        if len(pair) != 2:
            return "'/update_pair' command takes 2 args(russian and english word)"
        pair: List[str] = [word.lower().strip() for word in pair]
        try:
            User.get(chat_id=chat_id)
        except User.DoesNotExist:
            return 'You dont have a dictionary to update yet'
        old_pair = (
            Pair
            .select()
            .where((Pair.russian_word << pair) | (Pair.english_word << pair))
            .join(UserPair)
            .join(User)
            .where(User.chat_id == chat_id).first()
        )
        if not old_pair:
            return 'Pair not found'
        russian, english = self.determine_language_pairs(pair)
        old_pair.russian_word = russian
        old_pair.english_word = english
        result = old_pair.save()
        if result:
            return 'Updated'
        return 'Not updated'

    def delete_pair(self, chat_id: int, user_name: str, message: str) -> str:
        """
        Delete pair of words for user
        """
        command, *pair = message.split()
        if len(pair) != 2:
            return "'/delete_pair' command takes 2 args(russian and english word)"
        pair: List[str] = [word.lower().strip() for word in pair]
        try:
            User.get(chat_id=chat_id)
        except User.DoesNotExist:
            return 'You dont have a dictionary to delete yet'
        russian, english = self.determine_language_pairs(pair)
        old_pair = (
            Pair.select()
            .where((Pair.russian_word ** russian) & (Pair.english_word ** english))
            .first()
        )
        if old_pair:
            result: int = old_pair.delete_instance()
            if result:
                return 'Deleted'
            return 'Not deleted'
        return 'Pair not found'

    def answer(self, chat_id: int, user_name: str, message: str) -> str:
        """
        Handle user's answer
        """
        command, *pair = message.split()
        pair = [word.lower().strip() for word in pair]
        if len(pair) != 2:
            return '/answer command takes 2 args(russian and english word pair)'
        try:
            User.get(chat_id=chat_id)
        except User.DoesNotExist:
            return 'You dont have a dictionary to answer yet'
        russian, english = self.determine_language_pairs(pair)
        old_pair = (
            Pair.select()
            .where((Pair.russian_word ** russian) | Pair.english_word ** english)
            .join(UserPair).join(User).where(User.chat_id == chat_id)
            .first()
        )
        if not old_pair:
            'Pair not found at all'
        if old_pair.russian_word == russian and old_pair.english_word == english:
            return f"That's right {user_name or ''}! {english} is '{russian}' in Russian."
        return f"You're wrong {user_name or ''}! {english} is '{russian}' in Russian."

    @staticmethod
    def help(*args, **kwargs):
        return HELP_MESSAGE

    @staticmethod
    def determine_language_pairs(pair: list) -> tuple:
        dictionary_map = {
            'ru': None,
            'en': None
        }
        for word in pair:
            b = TextBlob(word)
            lang = b.detect_language()
            dictionary_map[lang] = word
        return dictionary_map['ru'], dictionary_map['en']

    @staticmethod
    def get_user_name(message: dict) -> str:
        chat = message.get('chat')
        first_name = chat.get('first_name')
        if first_name:
            return first_name
        username = chat.get('username')
        if username:
            return username
        return None

    def run(self):
        offset = None
        while True:
            response = self.get_updates(offset)
            if not response:
                print('No response')
                continue
            updates: dict = response.json()
            if not updates.get('ok'):
                print('not ok')
                print(updates)
                break
            result: list = updates.get('result')
            for update in result:
                if not all([update, update.get('message')]):
                    continue
                offset = update['update_id'] + 1
                chat_id = update['message']['chat']['id']
                message_text = update['message']['text']
                user_name = self.get_user_name(update['message'])
                action = self.dispatch_message(message_text)
                if not action:
                    return 'Wrong action'
                answer = action(chat_id, user_name, message_text)
                response = self.send_message(chat_id, answer)
                # print(response.status_code, response.json())


if __name__ == '__main__':
    pass
