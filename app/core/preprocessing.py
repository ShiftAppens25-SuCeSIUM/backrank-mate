import asyncio
import os
from typing import List
import instaloader
import os
from pathlib import Path
import shutil
from google import genai
import time
import tweepy
import praw
import requests
import yt_dlp

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
import re

allowed_gemini_extensions = [".png", ".jpg", ".txt", ".mp4"]
api_key=os.getenv("API_KEY")
ms_token = os.getenv("MS_TOKEN",None)

def download_insta_post(shortcode: str):
    base_dir = f"{os.getenv('TEMPORARY_DIRECTORY')}/insta"
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
    base_dir = f"{os.getenv('TEMPORARY_DIRECTORY')}/insta"
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
    base_dir = f"{os.getenv('TEMPORARY_DIRECTORY')}/insta"
    directory = f"{base_dir}/{shortcode}"
    shutil.rmtree(directory)

def instagram_get_shortcode(url: str) -> str:
    pattern = r"instagram\.com/p/([^/?]+)"
    match = re.search(pattern, url)
    if match:
        return match.group(1)
    else:
        raise ValueError("Invalid Instagram URL format. Please provide a valid post URL.")

def insta_post(url: str) -> str:
    try:
        shortcode = instagram_get_shortcode(url)
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
    base_dir = f"{os.getenv('TEMPORARY_DIRECTORY')}/reddit"
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
    base_dir = f"{os.getenv('TEMPORARY_DIRECTORY')}/reddit"
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
    
    # Wait for files to be uploaded
    for f in uploaded_files:
        gemini_wait_until_active(client, f.name)

    response = client.models.generate_content(
        model="gemini-2.0-flash", contents=content
    )

    return response.text


def delete_reddit_post(shortcode: str):
    base_dir = f"{os.getenv('TEMPORARY_DIRECTORY')}/reddit"
    directory = f"{base_dir}/{shortcode}"
    shutil.rmtree(directory)


def reddit_get_shortcode(url: str) -> str:
    pattern = r"reddit\.com/r/[^/]+/comments/([^/?]+)"
    match = re.search(pattern, url)
    if match:
        return match.group(1)
    else:
        raise ValueError("Invalid Reddit URL format. Please provide a valid post URL.")

def reddit_post(url: str) -> dict:
    shortcode = reddit_get_shortcode(url)
    try:
        data = get_reddit_post_data(shortcode)
        if "media" in data:
            download_media_reddit(shortcode, data["media"])
            return summarize_reddit_post(shortcode,data)
    finally:
        delete_reddit_post(shortcode)
        
        
        
        
        
        
        
        
        
        
        

def delete_tiktok(id: str):
    output_directory = f"{os.getenv('TEMPORARY_DIRECTORY')}/tiktok/{id}"
    if os.path.exists(output_directory):
        shutil.rmtree(output_directory)

def summarize_tiktok(id: str) -> str:
    base_dir = f"{os.getenv('TEMPORARY_DIRECTORY')}/tiktok"
    directory = f"{base_dir}/{id}"
    
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

def download_tiktok(url: str, id: str):
    base_dir = f"{os.getenv('TEMPORARY_DIRECTORY')}/tiktok"
    directory = f"{base_dir}/{id}"
    os.makedirs(directory, exist_ok=True)
    
    ydl_opts = {
        'outtmpl': f'{directory}/{id}.%(ext)s',
        'format': 'best/video',
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
    

ms_token = os.getenv("MS_TOKEN",None)

def tiktok_get_shortcode(url: str) -> str:
    if "www.tiktok.com" in url:
        pattern = r"tiktok\.com/@[^/]+/video/([^/?]+)"
        match = re.search(pattern, url)
        if match:
            return match.group(1)
        else:
            raise ValueError("Invalid TikTok URL format. Please provide a valid post URL.")
    elif "vm.tiktok.com" in url:
        pattern = r"vm\.tiktok\.com/([^/?]+)"
        match = re.search(pattern, url)
        if match:
            return match.group(1)
        else:
            raise ValueError("Invalid TikTok URL format. Please provide a valid post URL.")
    else:
        raise ValueError("Invalid TikTok URL format. Please provide a valid post URL.")
    

def tiktok(url: str) -> str:
    id = tiktok_get_shortcode(url)
    try:
        download_tiktok(url,id)
        return summarize_tiktok(id)
    finally:
        delete_tiktok(id)

def download_youtube_short(url: str, id: str):
    base_dir = f"{os.getenv('TEMPORARY_DIRECTORY')}/youtube_shorts"
    directory = f"{base_dir}/{id}"
    os.makedirs(directory, exist_ok=True)
    
    ydl_opts = {
        'outtmpl': f'{directory}/{id}.%(ext)s',
        'format': 'best/video',
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

def summarize_youtube_short(id: str) -> str:
    base_dir = f"{os.getenv('TEMPORARY_DIRECTORY')}/youtube_shorts"
    directory = f"{base_dir}/{id}"
    
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
        Summarize this YouTube Short.
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

def delete_youtube_short(id: str):
    output_directory = f"{os.getenv('TEMPORARY_DIRECTORY')}/youtube_shorts/{id}"
    if os.path.exists(output_directory):
        shutil.rmtree(output_directory)

def youtube_short_get_shortcode(url: str) -> str:
    pattern = r"youtube\.com/shorts/([^/?]+)"
    match = re.search(pattern, url)
    if match:
        return match.group(1)
    else:
        raise ValueError("Invalid YouTube Shorts URL format. Please provide a valid URL.")

def youtube_short(url: str) -> str:
    id = youtube_short_get_shortcode(url)
    try:
        download_youtube_short(url, id)
        return summarize_youtube_short(id)
    finally:
        delete_youtube_short(id)


def summarize_random_page(text: str) -> str:
    client = genai.Client(api_key=os.getenv("API_KEY"))
    
    content = [
        text,
        """
        Summarize this page.
        Use this text schema.

        Return, in plain text, the main statements or insinuations the page makes.
        """
    ]

    response = client.models.generate_content(
        model="gemini-2.0-flash", contents=content
    )

    return response.text

def random_url(url: str) -> str:
    page = requests.get(url)
    t = page.text
    return summarize_random_page(t)