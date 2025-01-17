import string
from datetime import datetime
from typing import List, Dict, Tuple
import aiohttp
import telegram

from app.scrapper.immo.model import ImmoData


def divide_chunks(l, n):
    """Divide list into chunks"""
    for i in range(0, len(l), n):
        yield l[i:i + n]

async def prepare_message(images: List[str], caption: string, session: aiohttp.ClientSession) -> List[telegram.InputMediaPhoto]:
    """Download images and store it temporarily"""
    media_images = []

    for image_url in images:
        async with session.get(image_url) as response:
            if response.status == 200:
                image = await response.read()
                # for first image add caption
                if not media_images:
                    media_images.append(telegram.InputMediaPhoto(media=image, caption=caption, parse_mode=telegram.ParseMode.HTML))
                else:
                    media_images.append(telegram.InputMediaPhoto(media=image))
    return media_images

async def generate_message(
    immo_data: ImmoData,
    hostname: str,
    host_url: str,
):
    """Send listing to user"""
    time_stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Generate html text message
    html_message = f"""
<a href="{immo_data.url}"><b>{immo_data.title}</b></a>

<b>Rent:</b> {immo_data.price}
<b>Rooms:</b> {immo_data.rooms}
<b>Living space:</b> {immo_data.living_space}

{immo_data.address}

<blockquote> <a href="{host_url}">{hostname}</a>, {time_stamp}</blockquote>
"""

    return html_message

