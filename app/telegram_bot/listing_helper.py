from datetime import datetime
from typing import List, Dict, Tuple
import aiohttp
import telegram

from immo.model import ImmoData


async def download_images(images: List[str], session: aiohttp.ClientSession) -> List[telegram.InputMediaPhoto]:
    """Download images and store it temporarily"""
    media_images = []

    for image_url in images:
        async with session.get(image_url) as response:
            if response.status == 200:
                image = await response.read()
                media_images.append(telegram.InputMediaPhoto(media=image))
    return media_images

async def generate_message(
    immo_data: ImmoData,
    hostname: str,
    host_url: str,
    immo_distances: Dict[str, Tuple[str, str]],
):
    """Send listing to user"""
    time_stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Generate html text message
    distance_message = ""
    if immo_distances is not None:
        mode_emoji_map = {
            "driving": "🚙",
            "transit": "🚋",
            "bicycling": "🚲",
        }
        # Add embed for each distance and travel duration type
        for mode, (distance, duration) in immo_distances.items():
            distance_message += f"""
Distance {mode_emoji_map[mode]}: {distance} ({duration})
"""

    html_message = f"""
<a href="{immo_data.url}"><b>{immo_data.title}</b></a>

<b>Rent:</b> {immo_data.price}
<b>Rooms:</b> {immo_data.rooms}
<b>Living space:</b> {immo_data.living_space}

{immo_data.address}

{distance_message}

<blockquote> <a href="{host_url}">{hostname}</a>, {time_stamp}</blockquote>
"""

    return html_message

