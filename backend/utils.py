# utils.py
import re
from youtube_transcript_api import YouTubeTranscriptApi, NoTranscriptFound
from pytube import YouTube
import requests
from bs4 import BeautifulSoup

def extract_video_id(url: str) -> str:
    if "v=" in url:
        return url.split("v=")[-1].split("&")[0]
    else:
        return url.rstrip("/").split("/")[-1]

def fetch_transcript(video_url: str) -> str:
    video_id = extract_video_id(video_url)
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        return " ".join([t["text"] for t in transcript])
    except NoTranscriptFound:
        return None
    except Exception:
        return None

def fetch_title_description(video_url: str):
    # Try pytube first
    try:
        yt = YouTube(video_url)
        return yt.title, yt.description or ""
    except Exception:
        # Fallback: scrape meta tags (may be blocked sometimes)
        try:
            html = requests.get(video_url, timeout=10).text
            soup = BeautifulSoup(html, "html.parser")
            title = soup.title.string if soup.title else "Unknown Title"
            desc_tag = soup.find("meta", {"name": "description"})
            description = desc_tag["content"] if desc_tag else ""
            return title, description
        except Exception:
            return "Unknown Title", ""
