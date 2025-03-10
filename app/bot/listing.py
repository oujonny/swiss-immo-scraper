import string
from datetime import datetime
from time import sleep
from typing import List, Dict, Tuple
import aiohttp
import cloudscraper
import telegram
from pymongo import MongoClient
from telegram import Update
from telegram.ext import ContextTypes

from app.scrapper.immo import model as immo_model

from urllib.parse import urlsplit, urlunsplit

from app.config import Config
from app.scrapper.immo.model import ImmoData

from app import setup_custom_logger

logger = setup_custom_logger(__name__)

async def send_listing(context: ContextTypes.DEFAULT_TYPE, immo_data: ImmoData, chat_id: int):
    message_content = await generate_message(immo_data)

    # Attach Images to message
    if immo_data.images:
        async with aiohttp.ClientSession() as session:
            downloaded_images = await prepare_message(immo_data.images, message_content, session)
            if downloaded_images:
                if len(downloaded_images) > 1:
                    await context.bot.send_media_group(chat_id, downloaded_images)
                else:
                    await context.bot.send_photo(chat_id=chat_id, photo=downloaded_images[0])
            else:
                # Handle the case where no images were downloaded
                await context.bot.send_message(chat_id=chat_id, text=message_content, parse_mode="HTML")

    # sleep to avoid rate limiting
    sleep(1)

async def callback_scrape_immo_listing(context: ContextTypes.DEFAULT_TYPE, ):
    config = Config()
    await scrape_immo_listing(context, config, chat_id=context.job.chat_id)

async def scrape_immo_listing(context: ContextTypes.DEFAULT_TYPE, config: Config, chat_id: int):
    """Scrape immo listing"""
    mongo_uri = f"mongodb://{config.mongo_username}:{config.mongo_password}@{config.mongo_host}:{config.mongo_port}/"

    mongo_client = MongoClient(mongo_uri)
    db = mongo_client.immo_db

    collection = db[f"listings-{chat_id}"]

    for entry in collection.find():
        immo_data = immo_model.ImmoData(
            title=entry["title"],
            description=entry["description"],
            url=entry["url"],
            images=entry["images"],
            documents=entry["documents"],
            address=entry["address"],
            price=entry["price"],
            rooms=entry["rooms"],
            living_space=entry["living_space"],
            balcony=entry["balcony"],
        )

        if not entry.get("sent"):
            await send_listing(
                context=context,
                immo_data=immo_data,
                chat_id=chat_id,
            )
            collection.update_one({"url": immo_data.url}, {"$set": {"sent": True}})

def divide_chunks(l, n):
    """Divide list into chunks"""
    for i in range(0, len(l), n):
        yield l[i:i + n]

async def prepare_message(images: List[str], caption: string, session: aiohttp.ClientSession) -> List[telegram.InputMediaPhoto]:
    """Download images and store it temporarily"""
    media_images = []

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Referer": "https://www.immoscout24.ch/",
        "DNT": "1",
        "Sec-Fetch-Dest": "image",
        "Sec-Fetch-Mode": "no-cors",
        "Sec-Fetch-Site": "same-site"
    }

    if len(images) > 10:
        caption += f"\n\n <b>More images available on the listing</b>"

    for image_url in images[:10]:
        scraper = cloudscraper.create_scraper()  # returns a CloudScraper instance
        response = scraper.get(image_url)
        if response.status_code == 200:
            logger.info(f"Downloading image: {image_url}")
            image = response.content
            # for first image add caption
            if not media_images:
                media_images.append(telegram.InputMediaPhoto(media=image, caption=caption, parse_mode="HTML"))
            else:
                media_images.append(telegram.InputMediaPhoto(media=image))
        else:
            logger.error(f"Failed to download image: {image_url} with status code: {response.status}")
            logger.error({response})
    return media_images

def short_description(description: str) -> str:
    """Shorten description to 1024 characters"""
    max_len = 600
    if len(description) > max_len:
        description = description[:(max_len-3)] + "..."
    return description

async def generate_message(
    immo_data: ImmoData,
):


    """Send listing to user"""
    time_stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # get base url from url
    hostname = urlsplit(immo_data.url).hostname

    # Generate html text message
    html_message_head = f"""
<a href="{immo_data.url}"><b>{immo_data.title}</b></a>

<b>Rent:</b> {immo_data.price}
<b>Rooms:</b> {immo_data.rooms}
<b>Living space:</b> {immo_data.living_space}
<b>Balcony:</b> {immo_data.balcony}

{immo_data.address}
"""

    if len(immo_data.documents) > 0:
        html_message_head += f"""
<b>Documents:</b>
{immo_data.documents}
"""

    html_message = f"""
{html_message_head}
<b>Description:</b>
{short_description(immo_data.description)}

<blockquote> <a href="{immo_data.url}">{hostname}</a>, {time_stamp}</blockquote>
"""

    return html_message

async def callback_stop_scrape(context: ContextTypes.DEFAULT_TYPE, chat_id: int):
    config = Config()
    await stop_scrape(context, config, chat_id)

async def stop_scrape(context: ContextTypes.DEFAULT_TYPE, config: Config, chat_id: int):
    await context.job_queue.stop()
    await context.job_queue.schedule_removal()

    """Scrape immo listing"""
    mongo_uri = f"mongodb://{config.mongo_username}:{config.mongo_password}@{config.mongo_host}:{config.mongo_port}/"

    mongo_client = MongoClient(mongo_uri)
    db = mongo_client.immo_db

    collection = db[f"listings-{chat_id}"]
    db.drop_collection(collection)

    settings_collection = db["settings"]
    settings_collection.delete_one({"chat_id": chat_id})