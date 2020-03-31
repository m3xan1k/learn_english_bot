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

    # business logic

    def dispatch_message(self, message: str) -> callable or None:
        """
        Decides what to do with the message, returns action(function)
        """
        if message.startswith('/'):
            return self.map_command(message)
        words = message.split()
        if len(words) == 1:
            pass
        elif len(words) == 2:
            return self.save_pair

    def map_command(self, command: str) -> callable:
        """
        Maps command-message to action(function)
        """
        command_mapper = {
            '/show_dict': self.show_dictionary,
        }

        return command_mapper.get(command)

    def save_pair(self, chat_id: int, user_name: str, message: list) -> str:
        """
        Saves new pair of words and binds it to user
        """
        pair = message.split()
        russian, english = self.determine_language_pairs(pair)
        try:
            user = User.get(chat_id=chat_id)
        except User.DoesNotExist:
            user = User.create(chat_id=chat_id, name=user_name)
        pair, _ = Pair.get_or_create(
            russian_word=russian,
            english_word=english,
        )
        new_user_pair, status = UserPair.get_or_create(user=user, pair=pair)
        if status:
            return 'Created'
        return 'Exist'

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
                break
            updates: dict = response.json()
            if not updates.get('ok'):
                print(updates)
                break
            result: list = updates.get('result')
            for update in result:
                if not update:
                    continue
                offset = update['update_id'] + 1
                chat_id = update['message']['chat']['id']
                message_text = update['message']['text']
                user_name = self.get_user_name(update['message'])
                action = self.dispatch_message(message_text)
                answer = action(chat_id, user_name, message_text)
                response = self.send_message(chat_id, answer)
                print(response.status_code, response.json())


if __name__ == '__main__':
    pass
