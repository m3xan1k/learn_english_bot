import os


API_TOKEN = os.environ.get('API_TOKEN')
BASE_URL = f'https://api.telegram.org/bot{API_TOKEN}/'
HTTP_TIMEOUT = 5

PROXY_LOGIN = os.environ.get('PROXY_LOGIN')
PROXY_PASS = os.environ.get('PROXY_PASS')
PROXY_HOST = os.environ.get('PROXY_HOST')
PROXY_PORT = os.environ.get('PROXY_PORT')

USE_PROXY = True

if USE_PROXY:
    if not any([PROXY_LOGIN, PROXY_PASS, PROXY_HOST, PROXY_PORT]):
        raise NotImplementedError('Proxy settings not provided')
    PROXY = {
        'http': f'socks5://{PROXY_LOGIN}:{PROXY_PASS}@{PROXY_HOST}:{PROXY_PORT}',
        'https': f'socks5://{PROXY_LOGIN}:{PROXY_PASS}@{PROXY_HOST}:{PROXY_PORT}',
    }
else:
    PROXY = None
