"""Parsing for immobilien websites"""
import json
import re
from typing import List

import telegram.constants
from bs4 import BeautifulSoup
from chardet.cli.chardetect import description_of

from app import setup_custom_logger
from app.scrapper.immo.error import ImmoParserError
from app.scrapper.immo.model import ImmoData, ImmoPriceKind
from app.scrapper.immo.website import ImmoWebsite
from app.scrapper.utils.image import scaled_image_size


logger = setup_custom_logger(__name__)


def html_to_plain_text(html_content):
    # Parse the HTML content
    soup = BeautifulSoup(html_content, 'lxml')

    # Get the plain text by stripping all HTML tags
    plain_text = soup.get_text()

    # Optionally, you can also clean up the text further by removing extra whitespace or newlines
    lines = (line.strip() for line in plain_text.splitlines())
    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
    plain_text = '\n'.join(chunk for chunk in chunks if chunk)

    return plain_text

class ImmoParser:
    """Parse different HTML Immo website listings"""

    @staticmethod
    def _parse_immoscout24(html: BeautifulSoup) -> List[ImmoData]:
        """Parse immoscout24.ch listings

        Returns:
            list[ImmoData]: ImmoData of listings on the immo website
        """
        # try to get the json that is inside of a specific script tag
        json_raw_data = html.find(
            lambda tag: tag.name == "script" and \
            tag.string and \
            tag.string.startswith("window.__INITIAL_STATE__=")
        ).text.lstrip("window.__INITIAL_STATE__=")

        # cleaning up not needed so just load the json
        listings_json = json.loads(json_raw_data)

        try:
            listings = listings_json["resultList"]["search"]["fullSearch"]["result"]["listings"]

        except KeyError:
            raise ImmoParserError("Listings json path changed.")

        immo_data_list = []
        for listing in listings:
            if lister_logo_url := listing.get("listerBranding"):
                lister_logo_url = lister_logo_url.get("logoUrl")

            # unwrap the listing
            listing = listing["listing"]
            primary_localization = listing["localization"]["primary"]
            try:
                title = listing["localization"][primary_localization]["text"]["title"]
                description = html_to_plain_text(listing["localization"][primary_localization]["text"]["description"])
                loc = listing["address"]["locality"]
                plz = listing["address"]["postalCode"]
                street = listing["address"]["street"]
                address = f"{street}, {plz} {loc}"
            except KeyError:
                address = None
                title = "Wohnung"
            url = f"/rent/{listing.get('id')}"
            rent = listing.get("prices").get("rent").get("gross") # gross
            rooms = listing.get("characteristics").get("numberOfRooms")
            living_space = listing.get("characteristics").get("livingSpace")
            # TODO: availability is not part of the JSON...
            balcony = listing.get("characteristics").get("hasBalcony")

            attachments = listing["localization"][primary_localization].get("attachments") or []
            images = [
                attachment["url"].encode().decode("unicode-escape")
                for attachment in attachments
                if attachment["type"] == "IMAGE"
            ]
            documents = [
                attachment["url"].encode().decode("unicode-escape")
                for attachment in attachments
                if attachment["type"] == "DOCUMENT"
            ]


            immo_data_list.append(
                ImmoData(
                    title=title,
                    description=description,
                    address=address,
                    url=url,
                    price=rent,
                    rooms=rooms,
                    living_space=living_space,
                    balcony=balcony,
                    images=images,
                    documents=documents,
                    lister_logo_url=lister_logo_url
                )
            )

        return immo_data_list

    @staticmethod
    def _parse_homegate(html: BeautifulSoup) -> List[ImmoData]:
        """Parse homegate.ch listings

        Returns:
            list[ImmoData]: ImmoData of listings on the immo website
        """
        script_tags = html.find_all("script")
        text_to_lstrip = "window.__INITIAL_STATE__="
        listings_json = None
        for script_tag in script_tags:
            if script_tag.text.startswith(text_to_lstrip):
                listings_json = json.loads(script_tag.text.lstrip(text_to_lstrip))

        if listings_json is None:
            raise ImmoParserError(
                "Can't find homegate.ch <script> with JSON data in HTML"
            )

        try:
            listings = listings_json["resultList"]["search"]["fullSearch"]["result"][
                "listings"
            ]
        except KeyError:
            raise ImmoParserError("Listings json path changed.")
        except TypeError as e:
            raise ImmoParserError(str(e))

        immo_data_list = []
        for listing in listings:
            try:
                listing = listing["listing"]
                localization = listing["localization"]
                primary_key = localization["primary"]
                title = localization[primary_key]["text"]["title"]
                description = html_to_plain_text(listing["localization"][primary_key]["text"]["description"])

                attachments = localization[primary_key].get("attachments") or []
                images = [
                    attachment["url"].encode().decode("unicode-escape")
                    for attachment in attachments
                    if attachment["type"] == "IMAGE"
                ]
                documents = [
                    attachment["url"].encode().decode("unicode-escape")
                    for attachment in attachments
                    if attachment["type"] == "DOCUMENT"
                ]

                address = None
                try:
                    loc = listing["address"]["locality"]
                    plz = listing["address"]["postalCode"]
                    street = listing["address"]["street"]
                    address = f"{street}, {plz} {loc}"
                except KeyError:
                    pass
                url = f"/rent/{listing['id']}"
                rent = listing["prices"]["rent"].get("gross")
                rooms, living_space = None, None
                if characteristics := listing.get("characteristics"):
                    rooms = str(characteristics.get("numberOfRooms"))
                    living_space = characteristics.get("livingSpace")
                    balcony = characteristics.get("hasBalcony")

                immo_data_list.append(
                    ImmoData(
                        title=title,
                        description=description,
                        address=address,
                        url=url,
                        price=rent,
                        rooms=rooms,
                        living_space=living_space,
                        balcony=balcony,
                        images=images,
                        documents=documents,
                    )
                )
            except KeyError:
                logger.error("homegate.ch key error: %s", listing)
                continue

        return immo_data_list

    @classmethod
    def parse_html(cls, website: ImmoWebsite, html: BeautifulSoup) -> list[ImmoData]:
        """Select the correct parser and parse the given html

        Returns:
            list[immo_data]: list of data about each listing
        """
        match website:
            case ImmoWebsite.IMMOSCOUT24:
                results = cls._parse_immoscout24(html)
            case ImmoWebsite.HOMEGATE:
                results = cls._parse_homegate(html)

        for immo_data in results:
            immo_data.url = f"https://{website.value}{immo_data.url}"

        return results
