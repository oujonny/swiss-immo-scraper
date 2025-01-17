"""Main module"""
import asyncio
import threading
from typing import Type

import sentry_sdk
from pymongo import MongoClient

from app import setup_custom_logger
from app.scrapper.manager import ImmoManager
from app.config import Config

from app.bot.main import telegram_app

from app.scrapper import utils, init_client_session
from app.scrapper.utils.url_generator import immoscount24_url_generator, homegate24_url_generator

log = setup_custom_logger(__name__)

def generate_scrape_urls(entry) -> list:
    """Generate a list of URLs to scrape from the settings collection in the db"""
    scrape_urls = []
    scrape_urls.append(immoscount24_url_generator(entry["zip"], entry["min_rooms"]))
    scrape_urls.append(homegate24_url_generator(entry["zip"], entry["min_rooms"]))

    return scrape_urls

async def main(config: Config, manager_class: Type[ImmoManager] = ImmoManager):
    mongo_uri = f"mongodb://{config.mongo_username}:{config.mongo_password}@{config.mongo_host}:{config.mongo_port}/"

    mongo_client = MongoClient(mongo_uri)
    db = mongo_client.immo_db
    settings_collection = db["settings"]

    for entry in settings_collection.find():
        scrape_urls = generate_scrape_urls(entry)

        """Create an ImmoManager for each immo website and start scraping"""
        session = init_client_session()

        managers, tasks = [], []

        if not scrape_urls:
            log.info("No URLs for scraping provided. Exiting...")
            return

        for url in scrape_urls:
            manager = manager_class(
                immo_website_url=url,
                session=session,
                n_seconds_sleep=config.scraping_interval,
                telegram_app = telegram_app,
                chat_id = entry["chat_id"],
                mongo_username=config.mongo_username,
                mongo_password=config.mongo_password,
                mongo_host=config.mongo_host,
                mongo_port=config.mongo_port,
            )
            managers.append(manager)

            tasks.append(asyncio.create_task(manager.start()))

        # Wait for all tasks to finish (ideally never)
        await asyncio.gather(*tasks)

        await session.close()


if __name__ == "__main__":
    # Load the ENV Variables into a config instance
    config = Config()

    asyncio.run(main(config))
