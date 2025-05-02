"""
This module contains functions to download, summarize, and delete files
including Instagram, Reddit, TikTok, YouTube Shorts, and X (formerly Twitter).
It also includes functions to handle user-uploaded files and summarize their content.
The summarization is done using the Google GenAI API.
"""

import re
import os
import shutil
import time
from pathlib import Path
from typing import List
from uuid import uuid4

import instaloader
import praw
import requests
import tweepy
import yt_dlp
from fastapi import UploadFile
from google import genai
from .reviews_processing import process_query


allowed_gemini_extensions = [".png", ".jpg", ".txt", ".mp4"]
api_key = os.getenv("API_KEY")
ms_token = os.getenv("MS_TOKEN", None)
reddit = praw.Reddit(
    client_id=os.getenv("REDDIT_CLIENT_ID"),
    client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
    user_agent="my_reddit_app",
)
ms_token = os.getenv("MS_TOKEN", None)


def create_directory(app_name: str, request_id: str) -> str:
    base_dir = f"{os.getenv('TEMPORARY_DIRECTORY')}/{app_name}"
    directory = f"{base_dir}/{request_id}"
    os.makedirs(directory, exist_ok=True)
    return directory


def delete_folder(directory: str):
    shutil.rmtree(directory)


def download_insta_post(shortcode: str,directory: str):
    insta = instaloader.Instaloader()
    post = instaloader.Post.from_shortcode(insta.context, shortcode)
    insta.download_post(post, target=Path(directory))


def instagram_get_shortcode(url: str) -> str:
    """Extracts the shortcode from the Instagram post URL.
    Args:
        url (str): The Instagram post URL.
    Returns:
        str: The shortcode of the Instagram post.
    Raises:
        ValueError: If the URL format is invalid.
    """
    pattern = r"instagram\.com/p/([^/?]+)"
    match = re.search(pattern, url)
    if match:
        return match.group(1)
    raise ValueError("Invalid Instagram URL format. Please provide a valid post URL.")


def insta_post(url: str) -> str:
    """Downloads and summarizes the Instagram post with the given URL.
    Args:
        url (str): The Instagram post URL.
    Returns:
        str: The summary of the Instagram post.
    Raises:
        ValueError: If the URL format is invalid.
    """
    shortcode = instagram_get_shortcode(url)
    directory = create_directory("insta", shortcode)
    try:
        download_insta_post(shortcode,directory)
        return process_query(
            f"Use the data in the files",
            directory,
        )
    finally:
        delete_folder(directory)


def get_reddit_post_data(post_id: str) -> dict:
    """Fetches the Reddit post data using the given post ID.
    Args:
        post_id (str): The ID of the Reddit post.
    Returns:
        dict: A dictionary containing the post title, text, and media URLs.
    """
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


def download_media_reddit(media: List[str],directory: str):
    for i, url in enumerate(media):
        response = requests.get(url, timeout=1000)
        file_type = url.split(".")[-1]
        if response.status_code == 200:
            with open(f"{directory}/{i}.{file_type}", "wb") as f:
                f.write(response.content)
        else:
            print(f"Failed to download {url}")



def reddit_get_shortcode(url: str) -> str:
    """Extracts the shortcode from the Reddit post URL.
    Args:
        url (str): The Reddit post URL.
    Returns:
        str: The shortcode of the Reddit post.
    Raises:
        ValueError: If the URL format is invalid.
    """
    pattern = r"reddit\.com/r/[^/]+/comments/([^/?]+)"
    match = re.search(pattern, url)
    if match:
        return match.group(1)
    raise ValueError("Invalid Reddit URL format. Please provide a valid post URL.")


def reddit_post(url: str) -> dict:
    """Downloads and summarizes the Reddit post with the given URL.
    Args:
        url (str): The Reddit post URL.
    Returns:
        dict: A dictionary containing the summary of the Reddit post.
    Raises:
        ValueError: If the URL format is invalid.
    """
    shortcode = reddit_get_shortcode(url)
    directory = create_directory("reddit", shortcode)
    try:
        data = get_reddit_post_data(shortcode)
        if "media" in data:
            download_media_reddit(data["media"],directory)
        
        return process_query(
        f"Summarize this reddit post with the following data:\
            title: {data['title']}, text: {data['text']}",directory)
    finally:
        delete_folder(directory)




def download_tiktok(url: str, post_id: str,directory: str):
    """Downloads the TikTok post with the given URL and ID.
    Args:
        url (str): The TikTok post URL.
        post_id (str): The ID of the TikTok post.
    """
    ydl_opts = {
        "outtmpl": f"{directory}/{post_id}.%(ext)s",
        "format": "best/video",
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])




def tiktok_get_shortcode(url: str) -> str:
    """Extracts the shortcode from the TikTok post URL.
    Args:
        url (str): The TikTok post URL.
    Returns:
        str: The shortcode of the TikTok post.
    Raises:
        ValueError: If the URL format is invalid.
    """
    if "www.tiktok.com" in url:
        pattern = r"tiktok\.com/@[^/]+/video/([^/?]+)"
        match = re.search(pattern, url)
        if match:
            return match.group(1)
        raise ValueError("Invalid TikTok URL format. Please provide a valid post URL.")
    if "vm.tiktok.com" in url:
        pattern = r"vm\.tiktok\.com/([^/?]+)"
        match = re.search(pattern, url)
        if match:
            return match.group(1)
        raise ValueError("Invalid TikTok URL format. Please provide a valid post URL.")
    raise ValueError("Invalid TikTok URL format. Please provide a valid post URL.")

                
def tiktok(url: str) -> str:
    """Downloads and summarizes the Instagram post with the given URL.
    Args:
        url (str): The Instagram post URL.
    Returns:
        str: The summary of the Instagram post.
    Raises:
        ValueError: If the URL format is invalid.
    """
    shortcode = tiktok_get_shortcode(url)
    directory = create_directory("tiktok", shortcode)
    try:
        download_tiktok(url,shortcode,directory)
        return process_query(
            f"Use the data in the files",
            directory,
        )
    finally:
        delete_folder(directory)


def download_youtube_short(url: str, post_id: str,directory: str):
    ydl_opts = {
        "outtmpl": f"{directory}/{post_id}.%(ext)s",
        "format": "best/video",
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])


def youtube_short_get_shortcode(url: str) -> str:
    """Extracts the shortcode from the YouTube Short URL.
    Args:
        url (str): The YouTube Short URL.
    Returns:
        str: The shortcode of the YouTube Short.
    Raises:
        ValueError: If the URL format is invalid.
    """
    pattern = r"youtube\.com/shorts/([^/?]+)"
    match = re.search(pattern, url)
    if match:
        return match.group(1)
    raise ValueError("Invalid YouTube Shorts URL format. Please provide a valid URL.")


def youtube_short(url: str) -> str:
    """Downloads and summarizes the YouTube Short with the given URL.
    Args:
        url (str): The YouTube Short URL.
    Returns:
        str: The summary of the YouTube Short.
    Raises:
        ValueError: If the URL format is invalid.
    """
    post_id = youtube_short_get_shortcode(url)
    directory = create_directory("youtube_short", post_id)
    try:
        download_youtube_short(url, post_id,directory)
        return process_query(
            f"Use the data in the files",
            directory,
        )
    finally:
        delete_folder(directory)



def random_url(url: str) -> str:
    """Downloads the content from a random URL and summarizes it.
    Args:
        url (str): The URL of the page to download and summarize.
    Returns:
        str: The summary of the page.
    """
    page = requests.get(url, timeout=1000)
    t = page.text
    return process_query(
        f"Summarize this page with the following data: {t}",
        None
    )


def x_get_shortcode(url: str) -> str:
    """Extracts the shortcode from the X (formerly Twitter) post URL.
    Args:
        url (str): The X post URL.
    Returns:
        str: The shortcode of the X post.
    Raises:
        ValueError: If the URL format is invalid.
    """
    pattern = r"x\.com/.+/status/([^/?]+)"
    match = re.search(pattern, url)
    if match:
        return match.group(1)
    raise ValueError("Invalid X URL format. Please provide a valid post URL.")


def get_tweet(post_id: str) -> tweepy.Tweet:
    """Fetches the tweet data using the given post ID.
    Args:
        post_id (str): The ID of the tweet.
    Returns:
        tweepy.Tweet: The tweet object containing the tweet data.
    """
    client = tweepy.Client(bearer_token=os.getenv("X_BEARER_TOKEN"))
    tweet = client.get_tweet(
        id=post_id, expansions=["attachments.media_keys"], media_fields=["url"]
    )
    return tweet


def download_x_post(directory: str,tweet: tweepy.Tweet = None):
    """Downloads the X post with the given ID.
    Args:
        post_id (str): The ID of the X post.
        tweet (tweepy.Tweet, optional): The tweet object containing the tweet data.
    """
    media = tweet.includes["media"]
    for i, m in enumerate(media):
        if m.type == "photo":
            url = m.url
            response = requests.get(url, timeout=1000)
            file_type = url.split(".")[-1]
            with open(f"{directory}/{i}.{file_type}", "wb") as f:
                f.write(response.content)
        elif m.type == "video":
            url = m.url
            response = requests.get(url, timeout=1000)
            file_type = url.split(".")[-1]
            with open(f"{directory}/{i}.{file_type}", "wb") as f:
                f.write(response.content)
        elif m.type == "animated_gif":
            url = m.url
            response = requests.get(url, timeout=1000)
            file_type = url.split(".")[-1]
            with open(f"{directory}/{i}.{file_type}", "wb") as f:
                f.write(response.content)

def x_post(url: str) -> str:
    """Downloads and summarizes the X post with the given URL.
    Args:
        url (str): The X post URL.
    Returns:
        str: The summary of the X post.
    Raises:
        ValueError: If the URL format is invalid.
    """
    post_id = x_get_shortcode(url)
    directory = create_directory("x", post_id)
    t = get_tweet(post_id)
    try:
        download_x_post(directory,t)
        return process_query(t.data.text, directory)
    finally:
        delete_folder(directory)


def store_user_files(request_id: str, files: List[UploadFile],directory: str):
    for file in files:
        with open(f"{directory}/{file.filename}", "wb") as f:
            f.write(file.file.read())


def user_request_with_files(text: str, files: List[UploadFile]) -> str:
    """Handles the user request with uploaded files and text.
    Args:
        text (str): The text content to summarize.
        files (List[UploadFile]): A list of user-uploaded files.
    Returns:
        str: The summary of the user-uploaded files.
    """

    request_id = str(uuid4())
    directory = create_directory("user_files", request_id)
    try:
        store_user_files(request_id, files,directory)
        return process_query(
            text,
            directory,
        )
    finally:
        delete_folder(directory)
