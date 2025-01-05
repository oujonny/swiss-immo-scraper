from typing import List, Optional

from pydantic import AnyHttpUrl, BaseSettings


class Config(BaseSettings):
    # Telegram Bot Token
    telegram_bot_token: str

    # Google Maps API key
    google_maps_api_key: Optional[str]
    # Used to compute the distance from the
    # apartment to the destination address
    google_maps_destination: Optional[str]

    # Sentry DSN for monitoring potential exceptions
    sentry_dsn: Optional[AnyHttpUrl]

    # List of Immo URLs that will be scraped.
    # You can use multiple URLs per one Immo website.
    scrape_urls: List[AnyHttpUrl]

    # Time delta between individual scrapes in seconds
    scraping_interval: int = 120

    # MongoDB connection
    mongo_username: str
    mongo_password: str
    mongo_host: str = "localhost"
    mongo_port:  int = 27017