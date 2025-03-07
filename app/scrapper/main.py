"""Main module"""
import asyncio
import threading
from typing import Type

import sentry_sdk
from pymongo import MongoClient
from telegram import Update
from telegram.ext import ContextTypes

from app import setup_custom_logger
from app.scrapper.manager import ImmoManager
from app.config import Config

from app.scrapper import utils, init_client_session
from app.scrapper.utils.url_generator import immoscount24_url_generator, homegate24_url_generator

log = setup_custom_logger(__name__)

def generate_scrape_urls(entry) -> list:
    """Generate a list of URLs to scrape from the settings collection in the db"""
    scrape_urls = []
    scrape_urls.append(immoscount24_url_generator(entry["zip"], entry["min_rooms"]))
    # TODO: disabled to avoid conflicts, update needed to the parsing; scrape_urls.append(homegate24_url_generator(entry["zip"], entry["min_rooms"]))

    return scrape_urls

async def main(config: Config, context: ContextTypes.DEFAULT_TYPE, chat_id: int, manager_class: Type[ImmoManager] = ImmoManager):
    mongo_uri = f"mongodb://{config.mongo_username}:{config.mongo_password}@{config.mongo_host}:{config.mongo_port}/"

    mongo_client = MongoClient(mongo_uri)
    db = mongo_client.immo_db
    settings_collection = db["settings"]

    for entry in settings_collection.find():
        scrape_urls = generate_scrape_urls(entry)

        """Create an ImmoManager for each immo website and start scraping"""

        if not scrape_urls:
            log.info("No URLs for scraping provided. Exiting...")
            return

        for url in scrape_urls:
            session = init_client_session()
            manager = manager_class(
                immo_website_url=url,
                session=session,
                n_seconds_sleep=config.scraping_interval,
                mongo_username=config.mongo_username,
                mongo_password=config.mongo_password,
                mongo_host=config.mongo_host,
                mongo_port=config.mongo_port,
                chat_id=chat_id,
            )
            await manager.start()
            await session.close()


if __name__ == "__main__":
    # Load the ENV Variables into a config instance
    config = Config()

    asyncio.run(main(config))
