from __future__ import annotations

import asyncio
from typing import List, Optional
from urllib.parse import urlparse

from aiohttp import ClientSession
from discord import Webhook, AsyncWebhookAdapter
from pymongo import MongoClient

from app import setup_custom_logger
from app.immo.model import ImmoData
from app.immo.parser import ImmoParser, ImmoParserError
from app.immo.website import ImmoWebsite
from app.scraper import Scraper, ScraperNetworkError
from app.utils.discord import send_discord_listing_embed
from app.utils.google_maps import compute_distance
from models import listings_collection
from app.telegram_bot.bot import TelegramBot


class ImmoManager:
    """Manage scraping apartment and estate listings every n seconds while posting new ones to Discord."""

    def __init__(
        self,
        immo_website_url: str,
        session: ClientSession,
        n_seconds_sleep: int,
        mongo_username: str,
        mongo_password: str,
        mongo_host: str,
        mongo_port: int,
        google_maps_destination: Optional[str],
        google_maps_api_key: Optional[str] = None,
    ):
        """
        Args:
            immo_website_url: the URL this manager will scrape
            session: shared aiohttp.ClientSession
            google_maps_destination: human readable destin
            ation string (e.g. "Raemistrasse, Zurich")
            google_maps_api_key: Google Maps API Key
        """
        self.immo_website_url = immo_website_url
        self.session = session
        self.google_maps_api_key = google_maps_api_key
        self.google_maps_destination_address = google_maps_destination
        self.n_seconds_sleep = n_seconds_sleep

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
        if self.google_maps_api_key:
            distance_results = await compute_distance(
                self.scraper.session,
                self.google_maps_api_key,
                origin_address=listing.address,
                destination_address=self.google_maps_destination_address,
            )
        else:
            distance_results = None

        # await send_discord_listing_embed(
        #     self.discord,
        #     session=self.session,
        #     immo_data=listing,
        #     hostname=self.immo_website.value,
        #     host_url=self.immo_website_url,
        #     host_icon_url=self.immo_website.author_icon_url,
        #     immo_distances=distance_results,
        # )
        self.logger.debug("sent %s", listing.url)

    async def _process_fresh_listings(self, fresh_listings: List[ImmoData]):
        """Search through latest fresh_listings, tagging any new (previously unseen) listings
        and then posting them to Discord.
        """
        for fresh_listing in fresh_listings:
            if not self.listings_collection.find_one({'url': fresh_listing.url}):
                # Send new listing to Discord
                await self._send_telegram_message(fresh_listing)
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

            await self._process_fresh_listings(fresh_listings)

            # wait
            await asyncio.sleep(self.n_seconds_sleep)
