import urllib.parse
import aiohttp
from datetime import datetime,timedelta,timezone
import logging
from pomice import Track
from typing import Optional

WIB = timezone(timedelta(hours=7))

def format_duration(ms):
    seconds = ms // 1000
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    return f"{hours}:{minutes:02}:{seconds:02}" if hours else f"{minutes}:{seconds:02}"


def get_thumbnail(track):
    if "youtube" in track.uri:
        return f"https://img.youtube.com/vi/{track.identifier}/hqdefault.jpg"
    elif "spotify" in track.uri:
        return track.info.get("artworkUrl")
    return None


# Di luar class manapun
def build_progress_bar(position_ms: int, duration_ms: int, bar_length: int = 12) -> str:
    if duration_ms == 0:
        return "─" * bar_length

    progress = int((position_ms / duration_ms) * bar_length)
    bar = "─" * progress + "•" + "─" * (bar_length - progress - 1)
    return f"▶︎ {bar}"

class TZFormatter(logging.Formatter):
    def formatTime(self, record, datefmt=None):
        dt = datetime.fromtimestamp(record.created, WIB)
        if datefmt:
            return dt.strftime(datefmt)
        return dt.isoformat()

# Atur logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

handler = logging.StreamHandler()
formatter = TZFormatter('[%(asctime)s] [%(levelname)s] %(name)s: %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
handler.setFormatter(formatter)
logger.addHandler(handler)


def format_afk_duration(delta: timedelta) -> str:
    total_seconds = int(delta.total_seconds())

    if total_seconds < 60:
        return "Baru saja"

    minutes = (total_seconds // 60) % 60
    hours = (total_seconds // 3600) % 24
    days = total_seconds // 86400

    parts = []

    if days > 0:
        parts.append(f"{days} hari")
    if hours > 0:
        parts.append(f"{hours} jam")
    if minutes > 0:
        parts.append(f"{minutes} menit")

    return " ".join(parts) + " yang lalu"



async def yt_search(query: str, api_key: str, mode: str="official") -> Optional[str]:
    ytsearch = "https://www.googleapis.com/youtube/v3/search"

    if mode == "official":
        query += " official"
    elif mode == "lyric":
        query += " lyrics"

    params = {
        "part" : "snippet",
        "q" : query,
        "type" : "video",
        "videoCategoryId": "10",
        "maxResults" :1,
        "key" :   api_key
    }

    async with aiohttp.ClientSession() as session:
        async with session.get(ytsearch, params=params) as resp:
            data = await resp.json()

            items = data.get("items")
            if not items:
                return None

            # Prioritaskan video dari channel resmi dan judul yang mengandung "official" / "lyric"
            for item in items:
                snippet = item["snippet"]
                title = snippet["title"].lower()
                channel = snippet["channelTitle"].lower()

                if mode == "official" and "official" in title:
                    return f"https://www.youtube.com/watch?v={item['id']['videoId']}"
                elif mode == "lyric" and ("lyric" in title or "lyrics" in title):
                    return f"https://www.youtube.com/watch?v={item['id']['videoId']}"
                elif mode == "normal":
                    return f"https://www.youtube.com/watch?v={item['id']['videoId']}"

            # Fallback: kembalikan hasil pertama jika tidak ketemu filter yang cocok
            return f"https://www.youtube.com/watch?v={items[0]['id']['videoId']}"
            