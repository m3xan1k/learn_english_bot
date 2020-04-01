from models import create_tables
from bot import Bot


if __name__ == '__main__':
    create_tables()
    Bot().run()
