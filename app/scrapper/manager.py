from __future__ import annotations

import logging
from typing import List, Optional
from urllib.parse import urlparse

from aiohttp import ClientSession
from pymongo import MongoClient

from app import setup_custom_logger
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

        # Model
        parsed_url = urlparse(immo_website_url)
        hostname = parsed_url.hostname
        self.immo_website = ImmoWebsite(hostname)
        self.listings = None

        # Telegram Chat ID
        self.chat_id = chat_id

        # MongoDB
        mongu_uri = f"mongodb://{mongo_username}:{mongo_password}@{mongo_host}:{mongo_port}/"
        client = MongoClient(mongu_uri)
        self.listings_collection = client['immo_db'][f"listings-{self.chat_id}"]

        # Instances
        self.logger = setup_custom_logger(".".join([__name__, hostname]))
        self.scraper = Scraper(url=immo_website_url, session=session)


        self.logger.info(f"Initialized for scraping: {immo_website_url}")

    async def _process_fresh_listings(self, fresh_listings: List[ImmoData]):
        """Search through latest fresh_listings, tagging any new (previously unseen) listings
        and then posting them to Disc ord.
        """
        # load all listings from the database int self.listings to immoData objects
        self.listings = list(self.listings_collection.find())[::-1]

        if self.listings:
            for new_listing in fresh_listings:
                # Check if listing is already in the database (maybe also from another portal, therefore excluding the listing URL)
                counter = 0
                if not self.listings_collection.find_one({'title': new_listing.title, 'address': new_listing.address, 'price': new_listing.price, 'living_space': new_listing.living_space}):
                    self.logger.info(f"New listing found: {new_listing.url}")
                    counter += 1

                    # Insert new listing into the database
                    self.logger.debug(f"Inserting new listing: {new_listing}")
                    self.listings_collection.insert_one({
                        'title': new_listing.title,
                        'description': new_listing.description,
                        'url': new_listing.url,
                        'images': new_listing.images,
                        'documents': new_listing.documents,
                        'address': new_listing.address,
                        'price': new_listing.price,
                        'rooms': new_listing.rooms,
                        'living_space': new_listing.living_space,
                        'balcony': new_listing.balcony,
                    })
                self.logger.info(f"Inserted {counter} new listings")
        elif len(self.listings) < 1:
            # initial run, store all listings in the database
            self.logger.info("Initial run, storing all listings in the database")
            for listing in fresh_listings:
                self.listings_collection.insert_one({
                    'title': listing.title,
                    'description': listing.description,
                    'url': listing.url,
                    'images': listing.images,
                    'documents': listing.documents,
                    'address': listing.address,
                    'price': listing.price,
                    'rooms': listing.rooms,
                    'living_space': listing.living_space,
                    'balcony': listing.balcony,
                })

    async def start(self):
        """Scrape, send and save information about latest listings"""
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
        except (KeyError, ImmoParserError) as e:
            self.logger.warning(f"Caught parsing error, html likely changed: {e}")

        self.logger.debug("Scraped %s listings", len(fresh_listings))
        if len(fresh_listings) > 0:
            await self._process_fresh_listings(fresh_listings)

