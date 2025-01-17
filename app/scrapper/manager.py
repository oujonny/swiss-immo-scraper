from __future__ import annotations

import asyncio
from typing import List, Optional
from urllib.parse import urlparse

from aiohttp import ClientSession
from pymongo import MongoClient
from telegram import Update
from telegram.ext import Application, CallbackContext

from app import setup_custom_logger
from app.bot import main as telegram_bot
from app.scrapper.immo.error import ImmoParserError
from app.scrapper.immo.model import ImmoData
from app.scrapper.immo.parser import ImmoParser
from app.scrapper.immo.website import ImmoWebsite
from app.scrapper.scraper import Scraper, ScraperNetworkError


class ImmoManager:
    """Manage scraping apartment and estate listings every n seconds while posting new ones to Discord."""

    def __init__(
        self,
        immo_website_url: str,
        session: ClientSession,
        n_seconds_sleep: int,
        telegram_app: Application,
        chat_id: int,
        mongo_username: str,
        mongo_password: str,
        mongo_host: str,
        mongo_port: int,
    ):
        """
        Args:
            immo_website_url: the URL this manager will scrape
            session: shared aiohttp.ClientSession
        """
        self.immo_website_url = immo_website_url
        self.session = session
        self.n_seconds_sleep = n_seconds_sleep

        # Telegram
        self.telegram_app = telegram_app
        self.chat_id = chat_id

        # Model
        parsed_url = urlparse(immo_website_url)
        hostname = parsed_url.hostname
        self.immo_website = ImmoWebsite(hostname)
        self.listings = None

        # MongoDB
        mongu_uri = f"mongodb://{mongo_username}:{mongo_password}@{mongo_host}:{mongo_port}/"
        client = MongoClient(mongu_uri)
        self.listings_collection = client['immo_db']['listings']

        # Instances
        self.logger = setup_custom_logger(".".join([__name__, hostname]))
        self.scraper = Scraper(url=immo_website_url, session=session)

        self.logger.info(f"Initialized for scraping: {immo_website_url}")

    async def _send_telegram_message(self, listing):
        distance_results = None

        update = Update(0)
        context = CallbackContext(self.telegram_app, chat_id=self.chat_id)


        await telegram_bot.send_listing(
            update=update,
            context=context,
            immo_data=listing,
            hostname=self.immo_website.value,
            host_url=self.immo_website_url,
        )
        self.logger.debug("sent %s", listing.url)

    async def _process_fresh_listings(self, fresh_listings: List[ImmoData]):
        """Search through latest fresh_listings, tagging any new (previously unseen) listings
        and then posting them to Discord.
        """
        for fresh_listing in fresh_listings:
            if not self.listings_collection.find_one({'url': fresh_listing.url}):
                self.logger.info(f"New listing found: {fresh_listing.url}")

                # Insert new listing into the database
                self.listings_collection.insert_one({
                    'url': fresh_listing.url,
                    'title': fresh_listing.title,
                    'address': fresh_listing.address,
                    'price': fresh_listing.price,
                    'rooms': fresh_listing.rooms,
                    'living_space': fresh_listing.living_space,
                    'images': fresh_listing.images,
                })

                # Send the new listing to Telegram
                if 1 ==1:
                    self.logger.debug("Sending new listing to Telegram")
                    await self._send_telegram_message(fresh_listing)

    async def start(self):
        """Scrape, send and save information about latest listings"""

        while True:
            try:
                # Scrape
                fresh_listings_html = await self.scraper.scrape()
                # Parse HTML into fresh listings
                fresh_listings = ImmoParser.parse_html(
                    self.immo_website, fresh_listings_html
                )
            except ScraperNetworkError as e:
                self.logger.warning(
                    f"Caught ScraperNetworkError, skipping this round of scraping: {e}"
                )
                await asyncio.sleep(self.n_seconds_sleep)
                continue
            except (KeyError, ImmoParserError) as e:
                self.logger.warning(f"Caught parsing error, html likely changed: {e}")
                await asyncio.sleep(self.n_seconds_sleep)
                continue

            self.logger.debug("Scraped %s fresh listings", len(fresh_listings))
            await self._process_fresh_listings(fresh_listings)

            # wait
            await asyncio.sleep(self.n_seconds_sleep)
