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


allowed_gemini_extensions = [".png", ".jpg", ".txt", ".mp4"]
api_key = os.getenv("API_KEY")
ms_token = os.getenv("MS_TOKEN", None)


def download_insta_post(shortcode: str):
    """Downloads the Instagram post with the given shortcode.
    Args:
        shortcode (str): The shortcode of the Instagram post to download.
    """
    base_dir = f"{os.getenv('TEMPORARY_DIRECTORY')}/insta"
    directory = f"{base_dir}/{shortcode}"
    os.makedirs(directory, exist_ok=True)

    insta = instaloader.Instaloader()
    post = instaloader.Post.from_shortcode(insta.context, shortcode)
    insta.download_post(post, target=Path(directory))


def gemini_wait_until_active(client: genai.Client, name: str, timeout: int = 60):
    """Waits until the Gemini file is in 'ACTIVE' state or timeout.
    Args:
        client (genai.Client): The GenAI client instance.
        name (str): The name of the file to check.
        timeout (int): The maximum time to wait in seconds.
    Raises:
        TimeoutError: If the file does not become 'ACTIVE' within the timeout period.
    """
    start = time.time()
    while time.time() - start < timeout:
        file_info = client.files.get(name=name)
        if file_info.state == "ACTIVE":
            return file_info
        time.sleep(1)
    raise TimeoutError(f"File {name} did not become ACTIVE in time.")


def summarize_insta_post(shortcode: str) -> str:
    """Summarizes the Instagram post with the given shortcode.
    Args:
        shortcode (str): The shortcode of the Instagram post to summarize.
    Returns:
        str: The summary of the Instagram post.
    """
    base_dir = f"{os.getenv('TEMPORARY_DIRECTORY')}/insta"
    directory = f"{base_dir}/{shortcode}"

    client = genai.Client(api_key=api_key)

    files = [
        os.path.join(directory, f)
        for f in os.listdir(directory)
        if os.path.isfile(os.path.join(directory, f))
    ]

    filtered_files = [f for f in files if Path(f).suffix in allowed_gemini_extensions]

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
    """Deletes the downloaded Instagram post files.
    Args:
        shortcode (str): The shortcode of the Instagram post to delete.
    """
    base_dir = f"{os.getenv('TEMPORARY_DIRECTORY')}/insta"
    directory = f"{base_dir}/{shortcode}"
    shutil.rmtree(directory)


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
    user_agent="my_reddit_app",
)


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


def download_media_reddit(shortcode: str, media: List[str]):
    """Downloads the media files from the Reddit post.
    Args:
        shortcode (str): The shortcode of the Reddit post.
        media (List[str]): A list of media URLs to download.
    """
    base_dir = f"{os.getenv('TEMPORARY_DIRECTORY')}/reddit"
    directory = f"{base_dir}/{shortcode}"
    os.makedirs(directory, exist_ok=True)
    for i, url in enumerate(media):
        response = requests.get(url, timeout=1000)
        file_type = url.split(".")[-1]
        if response.status_code == 200:
            with open(f"{directory}/{i}.{file_type}", "wb") as f:
                f.write(response.content)
        else:
            print(f"Failed to download {url}")


def summarize_reddit_post(shortcode: str, data: dict) -> str:
    """Summarizes the Reddit post with the given shortcode.
    Args:
        shortcode (str): The shortcode of the Reddit post.
        data (dict): A dictionary containing the post title, text, and media URLs.
    Returns:
        str: The summary of the Reddit post.
    """
    base_dir = f"{os.getenv('TEMPORARY_DIRECTORY')}/reddit"
    directory = f"{base_dir}/{shortcode}"

    files = [
        os.path.join(directory, f)
        for f in os.listdir(directory)
        if os.path.isfile(os.path.join(directory, f))
    ]

    filtered_files = [f for f in files if Path(f).suffix in allowed_gemini_extensions]
    client = genai.Client(api_key=os.getenv("API_KEY"))

    uploaded_files = [client.files.upload(file=f) for f in filtered_files]
    content = uploaded_files + [
        f"Summarize this reddit post with the following data:\
            title: {data['title']}, text: {data['text']}"
    ]

    # Wait for files to be uploaded
    for f in uploaded_files:
        gemini_wait_until_active(client, f.name)

    response = client.models.generate_content(
        model="gemini-2.0-flash", contents=content
    )

    return response.text


def delete_reddit_post(shortcode: str):
    """Deletes the downloaded Reddit post files.
    Args:
        shortcode (str): The shortcode of the Reddit post.
    """
    base_dir = f"{os.getenv('TEMPORARY_DIRECTORY')}/reddit"
    directory = f"{base_dir}/{shortcode}"
    shutil.rmtree(directory)


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
    try:
        data = get_reddit_post_data(shortcode)
        if "media" in data:
            download_media_reddit(shortcode, data["media"])
        return summarize_reddit_post(shortcode, data)
    finally:
        delete_reddit_post(shortcode)


def delete_tiktok(post_id: str):
    """Deletes the downloaded TikTok files.
    Args:
        id (str): The ID of the TikTok post.
    """
    output_directory = f"{os.getenv('TEMPORARY_DIRECTORY')}/tiktok/{post_id}"
    if os.path.exists(output_directory):
        shutil.rmtree(output_directory)


def summarize_tiktok(post_id: str) -> str:
    """Summarizes the TikTok post with the given ID.
    Args:
        post_id (str): The ID of the TikTok post.
    Returns:
        str: The summary of the TikTok post.
    """
    base_dir = f"{os.getenv('TEMPORARY_DIRECTORY')}/tiktok"
    directory = f"{base_dir}/{post_id}"

    files = [
        os.path.join(directory, f)
        for f in os.listdir(directory)
        if os.path.isfile(os.path.join(directory, f))
    ]

    filtered_files = [f for f in files if Path(f).suffix in allowed_gemini_extensions]

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


def download_tiktok(url: str, post_id: str):
    """Downloads the TikTok post with the given URL and ID.
    Args:
        url (str): The TikTok post URL.
        post_id (str): The ID of the TikTok post.
    """
    base_dir = f"{os.getenv('TEMPORARY_DIRECTORY')}/tiktok"
    directory = f"{base_dir}/{post_id}"
    os.makedirs(directory, exist_ok=True)

    ydl_opts = {
        "outtmpl": f"{directory}/{post_id}.%(ext)s",
        "format": "best/video",
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])


ms_token = os.getenv("MS_TOKEN", None)


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
    """Downloads and summarizes the TikTok post with the given URL.
    Args:
        url (str): The TikTok post URL.
    Returns:
        str: The summary of the TikTok post.
    Raises:
        ValueError: If the URL format is invalid.
    """
    post_id = tiktok_get_shortcode(url)
    try:
        download_tiktok(url, post_id)
        return summarize_tiktok(post_id)
    finally:
        delete_tiktok(post_id)


def download_youtube_short(url: str, post_id: str):
    """Downloads the YouTube Short with the given URL and ID.
    Args:
        url (str): The YouTube Short URL.
        post_id (str): The ID of the YouTube Short.
    """
    base_dir = f"{os.getenv('TEMPORARY_DIRECTORY')}/youtube_shorts"
    directory = f"{base_dir}/{post_id}"
    os.makedirs(directory, exist_ok=True)

    ydl_opts = {
        "outtmpl": f"{directory}/{post_id}.%(ext)s",
        "format": "best/video",
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])


def summarize_youtube_short(post_id: str) -> str:
    """Summarizes the YouTube Short with the given ID.
    Args:
        post_id (str): The ID of the YouTube Short.
    Returns:
        str: The summary of the YouTube Short.
    """
    base_dir = f"{os.getenv('TEMPORARY_DIRECTORY')}/youtube_shorts"
    directory = f"{base_dir}/{post_id}"

    files = [
        os.path.join(directory, f)
        for f in os.listdir(directory)
        if os.path.isfile(os.path.join(directory, f))
    ]

    filtered_files = [f for f in files if Path(f).suffix in allowed_gemini_extensions]

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


def delete_youtube_short(post_id: str):
    """Deletes the downloaded YouTube Short files.
    Args:
        post_id (str): The ID of the YouTube Short.
    """
    output_directory = f"{os.getenv('TEMPORARY_DIRECTORY')}/youtube_shorts/{post_id}"
    if os.path.exists(output_directory):
        shutil.rmtree(output_directory)


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
    try:
        download_youtube_short(url, post_id)
        return summarize_youtube_short(post_id)
    finally:
        delete_youtube_short(post_id)


def summarize_random_page(text: str) -> str:
    """Summarizes the content of a random page.
    Args:
        text (str): The text content of the page to summarize.
    Returns:
        str: The summary of the page.
    """
    client = genai.Client(api_key=os.getenv("API_KEY"))

    content = [
        text,
        """
        Summarize this page.
        Use this text schema.

        Return, in plain text, the main statements or insinuations the page makes.
        """,
    ]

    response = client.models.generate_content(
        model="gemini-2.0-flash", contents=content
    )

    return response.text


def random_url(url: str) -> str:
    """Downloads the content from a random URL and summarizes it.
    Args:
        url (str): The URL of the page to download and summarize.
    Returns:
        str: The summary of the page.
    """
    page = requests.get(url, timeout=1000)
    t = page.text
    return summarize_random_page(t)


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


def download_x_post(post_id: str, tweet: tweepy.Tweet = None):
    """Downloads the X post with the given ID.
    Args:
        post_id (str): The ID of the X post.
        tweet (tweepy.Tweet, optional): The tweet object containing the tweet data.
    """
    base_dir = f"{os.getenv('TEMPORARY_DIRECTORY')}/x"
    directory = f"{base_dir}/{post_id}"
    os.makedirs(directory, exist_ok=True)

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


def summarize_x_post(post_id: str, tweet: tweepy.Tweet) -> str:
    """Summarizes the X post with the given ID.
    Args:
        post_id (str): The ID of the X post.
        tweet (tweepy.Tweet): The tweet object containing the tweet data.
    Returns:
        str: The summary of the X post.
    """
    base_dir = f"{os.getenv('TEMPORARY_DIRECTORY')}/x"
    directory = f"{base_dir}/{post_id}"

    files = [
        os.path.join(directory, f)
        for f in os.listdir(directory)
        if os.path.isfile(os.path.join(directory, f))
    ]

    filtered_files = [f for f in files if Path(f).suffix in allowed_gemini_extensions]

    client = genai.Client(api_key=os.getenv("API_KEY"))

    uploaded_files = [client.files.upload(file=f) for f in filtered_files]
    content = uploaded_files + [
        f"""
        Summarize this X tweet where the post text was {tweet.data.text}.
        Use this text schema.

        Return, in plain text, the main statements or insinuations the video makes.
        """
    ]

    response = client.models.generate_content(
        model="gemini-2.0-flash", contents=content
    )
    return response.text


def delete_x_post(post_id: str):
    """Deletes the downloaded X post files.
    Args:
        post_id (str): The ID of the X post.
    """
    base_dir = f"{os.getenv('TEMPORARY_DIRECTORY')}/x"
    directory = f"{base_dir}/{post_id}"
    shutil.rmtree(directory)


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
    t = get_tweet(post_id)
    try:
        download_x_post(post_id, t)
        return summarize_x_post(post_id, t)
    finally:
        delete_x_post(post_id)


def store_user_files(request_id: str, files: List[UploadFile]):
    """Stores the user-uploaded files in a temporary directory.
    Args:
        request_id (str): The unique request ID for the user.
        files (List[UploadFile]): A list of user-uploaded files.
    """
    base_dir = f"{os.getenv('TEMPORARY_DIRECTORY')}/user_data"
    directory = f"{base_dir}/{request_id}"
    os.makedirs(directory, exist_ok=True)
    for file in files:
        with open(f"{directory}/{file.filename}", "wb") as f:
            f.write(file.file.read())


def delete_user_files(request_id: str):
    """Deletes the user-uploaded files from the temporary directory.
    Args:
        request_id (str): The unique request ID for the user.
    """
    base_dir = f"{os.getenv('TEMPORARY_DIRECTORY')}/user_data"
    directory = f"{base_dir}/{request_id}"
    if os.path.exists(directory):
        for file in os.listdir(directory):
            os.remove(f"{directory}/{file}")
        os.rmdir(directory)


def summarize_user_files(request_id: str, text: str) -> str:
    """Summarizes the user-uploaded files with the given request ID.
    Args:
        request_id (str): The unique request ID for the user.
        text (str): The text content to summarize.
    Returns:
        str: The summary of the user-uploaded files.
    """
    base_dir = f"{os.getenv('TEMPORARY_DIRECTORY')}/user_data"
    directory = f"{base_dir}/{request_id}"

    files = [
        os.path.join(directory, f)
        for f in os.listdir(directory)
        if os.path.isfile(os.path.join(directory, f))
    ]

    filtered_files = [f for f in files if Path(f).suffix in allowed_gemini_extensions]

    client = genai.Client(api_key=os.getenv("API_KEY"))

    uploaded_files = [client.files.upload(file=f) for f in filtered_files]
    content = uploaded_files + [
        f"""
        Summarize the content of these files contexting with the text: {text}.
        Use this text schema.

        Return, in plain text, the main statements or insinuations the files make.
        """
    ]

    # Wait for files to be uploaded
    for f in uploaded_files:
        gemini_wait_until_active(client, f.name)

    response = client.models.generate_content(
        model="gemini-2.0-flash", contents=content
    )

    return response.text


def user_request_with_files(text: str, files: List[UploadFile]) -> str:
    """Handles the user request with uploaded files and text.
    Args:
        text (str): The text content to summarize.
        files (List[UploadFile]): A list of user-uploaded files.
    Returns:
        str: The summary of the user-uploaded files.
    """

    request_id = str(uuid4())
    try:
        store_user_files(request_id, files)
        return summarize_user_files(request_id, text)
    finally:
        delete_user_files(request_id)
