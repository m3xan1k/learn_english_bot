from enum import Enum, unique
from urllib.parse import urljoin

import requests
from requests.adapters import HTTPAdapter
from requests.exceptions import ConnectionError

from conf import (
    BASE_URL, HTTP_TIMEOUT,
    PROXY
)


telegram_adapter = HTTPAdapter(max_retries=3)
session = requests.Session()
session.mount('https://api.telegram.org', telegram_adapter)


@unique
class BotApiUrl(Enum):
    """
    Telegram bot API endpoints
    """
    GET_UPDATES = 'getUpdates'


class Bot:

    @staticmethod
    def get_updates(offset: int or None = None) -> requests.Response:
        url: str = urljoin(BASE_URL, BotApiUrl.GET_UPDATES.value)
        params = {'timeout': 300, 'offset': offset}
        try:
            response = session.get(url, params=params, timeout=HTTP_TIMEOUT, proxies=PROXY)
        except ConnectionError:
            return None
        return response

    def dispatch_message(self, message: str) -> callable or None:
        words = message.split()
        if len(words) == 1:
            pass
        elif len(words) == 2:
            self.save_pair(words)

    @staticmethod
    def save_pair(words: list):
        pass

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
                message = update['message']['text']
                print(offset, chat_id, message)
