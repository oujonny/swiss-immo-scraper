"""Main module"""
import asyncio
import threading
from typing import Type

import sentry_sdk

from app import init_client_session, setup_custom_logger
from app.manager import ImmoManager
from app.config import Config
from telegram_bot.bot import TelegramBot

log = setup_custom_logger(__name__)


async def main(config: Config, manager_class: Type[ImmoManager] = ImmoManager):
    """Create an ImmoManager for each immo website and start scraping"""
    session = init_client_session()

    # Initialize the Telegram Bot
    telegram_bot = TelegramBot(config.telegram_bot_token)

    managers, tasks = [], []

    if not config.scrape_urls:
        log.info("No URLs for scraping provided. Exiting...")
        return

    for url in config.scrape_urls:
        manager = manager_class(
            immo_website_url=url,
            session=session,
            n_seconds_sleep=config.scraping_interval,
            mongo_username=config.mongo_username,
            mongo_password=config.mongo_password,
            mongo_host=config.mongo_host,
            mongo_port=config.mongo_port,
            google_maps_destination=config.google_maps_destination,
            google_maps_api_key=config.google_maps_api_key,
        )
        managers.append(manager)

        tasks.append(asyncio.create_task(manager.start()))

    # Start the Telegram Bot
    tasks.append(asyncio.create_task(telegram_bot.start()))


    # Wait for all tasks to finish (ideally never)
    await asyncio.gather(*tasks)

    await session.close()


if __name__ == "__main__":
    # Load the ENV Variables into a config instance
    config = Config()

    # Setup Sentry if needed
    if dsn := config.sentry_dsn:
        sentry_sdk.init(
            dsn=dsn, traces_sample_rate=1.0, ignore_errors=[KeyboardInterrupt]
        )

    asyncio.run(main(config))
