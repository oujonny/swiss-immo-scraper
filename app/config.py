from typing import List, Optional

from pydantic import AnyHttpUrl, BaseSettings


class Config(BaseSettings):
    # Telegram Bot Token
    telegram_bot_token: str

    # Time delta between individual scrapes in seconds
    scraping_interval: int = 120

    # MongoDB connection
    mongo_username: str
    mongo_password: str
    mongo_host: str = "localhost"
    mongo_port:  int = 27017