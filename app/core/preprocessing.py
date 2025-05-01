import asyncio
import os
from typing import List
from TikTokApi import TikTokApi
import instaloader
import os
from pathlib import Path
import shutil
from google import genai
import time
import tweepy
import praw
import requests

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
import re

allowed_gemini_extensions = [".png", ".jpg", ".txt", ".mp4"]
api_key=os.getenv("API_KEY")

def download_insta_post(shortcode: str):
    base_dir = f"{os.getenv("TEMPORARY_DIRECTORY")}/insta"
    directory = f"{base_dir}/{shortcode}"
    os.makedirs(directory, exist_ok=True)

    insta = instaloader.Instaloader()
    post = instaloader.Post.from_shortcode(insta.context, shortcode)
    insta.download_post(post, target=Path(directory))

def gemini_wait_until_active(client, name, timeout=60):
    """Waits until the Gemini file is in 'ACTIVE' state or timeout."""
    start = time.time()
    while time.time() - start < timeout:
        file_info = client.files.get(name=name)
        if file_info.state == "ACTIVE":
            return file_info
        time.sleep(1)
    raise TimeoutError(f"File {name} did not become ACTIVE in time.")





def summarize_insta_post(shortcode: str) -> str:
    base_dir = f"{os.getenv("TEMPORARY_DIRECTORY")}/insta"
    directory = f"{base_dir}/{shortcode}"

    client = genai.Client(api_key=api_key)

    files = [ 
        os.path.join(directory, f) for f in os.listdir(directory) 
        if os.path.isfile(os.path.join(directory, f))
    ]

    filtered_files = [
        f for f in files
        if Path(f).suffix in allowed_gemini_extensions
    ]
    
    client = genai.Client(api_key=os.getenv("API_KEY"))
    
    uploaded_files = [client.files.upload(file=f) for f in filtered_files]
    content = uploaded_files + [
        """
        Summarize this instagram post.
        Use this text schema.

        Return, in plain text, the main statements or insinuations the video makes.
        """
    ]

    # Wait for files to be uploaded
    for f in uploaded_files:
        gemini_wait_until_active(client, f.name)

    response = client.models.generate_content(
        model="gemini-2.0-flash", contents=content
    )

    return response.text


def delete_insta_post(shortcode: str):
    base_dir = f"{os.getenv("TEMPORARY_DIRECTORY")}/insta"
    directory = f"{base_dir}/{shortcode}"
    shutil.rmtree(directory)

def insta_post(shortcode: str) -> str:
    try:
        download_insta_post(shortcode)
        summary = summarize_insta_post(shortcode)
        return summary
    finally:
        delete_insta_post(shortcode)


reddit = praw.Reddit(
    client_id=os.getenv("REDDIT_CLIENT_ID"),
    client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
    user_agent="my_reddit_app"
)


def get_reddit_post_data(post_id: str) -> dict:
    submission = reddit.submission(id=post_id)
    result = {
        "title": submission.title,
        "text": submission.selftext or None,
    }

    if submission.is_reddit_media_domain and submission.url:
        result["media"] = [submission.url]
    elif submission.media and "reddit_video" in submission.media:
        result["media"] = [submission.media["reddit_video"]["fallback_url"]]
    elif hasattr(submission, "preview") and "images" in submission.preview:
        result["media"] = [img["source"]["url"] for img in submission.preview["images"]]
    return result


def download_media_reddit(shortcode : str,media: List[str]):
    base_dir = f"{os.getenv("TEMPORARY_DIRECTORY")}/reddit"
    directory = f"{base_dir}/{shortcode}"
    os.makedirs(directory, exist_ok=True)
    for i, url in enumerate(media):
        response = requests.get(url)
        file_type = url.split(".")[-1]
        if response.status_code == 200:
            with open(f"{directory}/{i}.{file_type}", "wb") as f:
                f.write(response.content)
        else:
            print(f"Failed to download {url}")
            

def summarize_reddit_post(shortcode: str,data : dict) -> str:
    base_dir = f"{os.getenv("TEMPORARY_DIRECTORY")}/reddit"
    directory = f"{base_dir}/{shortcode}"
    
    files = [ 
        os.path.join(directory, f) for f in os.listdir(directory) 
        if os.path.isfile(os.path.join(directory, f))
    ]

    filtered_files = [
        f for f in files
        if Path(f).suffix in allowed_gemini_extensions
    ]
    client = genai.Client(api_key=os.getenv("API_KEY"))
    
    uploaded_files = [client.files.upload(file=f) for f in filtered_files]
    content = uploaded_files + [f"Summarize this reddit post with the following data: title: {data['title']}, text: {data['text']}"]
def summarize_tiktok(url: str) -> str:
    output_filename = f"{os.getenv("TEMPORARY_DIRECTORY")}/tiktok/{extract_tiktok_video_id(url)}"

    client = genai.Client(api_key=api_key)

    files = [ 
        os.path(output_filename)
    ]
    
    uploaded_files = [client.files.upload(file=f) for f in files]
    content = files + [
        """
        Summarize this tiktok.
        Use this text schema.

        Return, in plain text, the main statements or insinuations the video makes.
        """
    ]

    # Wait for files to be uploaded
    for f in uploaded_files:
        gemini_wait_until_active(client, f.name)

    response = client.models.generate_content(
        model="gemini-2.0-flash", contents=content
    )

    return response.text

def delete_reddit_post(shortcode: str):
    base_dir = f"{os.getenv("TEMPORARY_DIRECTORY")}/reddit"
    directory = f"{base_dir}/{shortcode}"
    shutil.rmtree(directory)

def reddit_post(shortcode: str) -> dict:
    try:
        data = get_reddit_post_data(shortcode)
        if "media" in data:
            download_media_reddit(shortcode, data["media"])
            return summarize_reddit_post(shortcode,data)
    finally:
        delete_reddit_post(shortcode)
def delete_tiktok(id: str):
    output_filename = f"{os.getenv("TEMPORARY_DIRECTORY")}/tiktok/{(id)}"
    if os.path.exists(output_filename):
        os.remove(output_filename)


async def download_tiktok(id: str):
    async with TikTokApi() as api:
        base_dir = f"{os.getenv("TEMPORARY_DIRECTORY")}/tiktok"
        os.makedirs(base_dir, exist_ok=True)
        output_filename = f"{base_dir}/{id}"
        video = await api.video(url=f"url")
        video_data = await video.bytes()

        with open(output_filename, "wb") as f:
            f.write(video_data)


def tiktok(id: str) -> str:
    try:
        asyncio.run(download_tiktok(id))
        return summarize_tiktok(id)
    finally:
        delete_tiktok(id)
