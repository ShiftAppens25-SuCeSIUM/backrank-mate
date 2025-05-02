"""Fact-checking module for processing reviews using Google Fact Check API.
This module provides functionality to perform a fact check on a given query"""

from typing import List
import re
from fastapi import UploadFile
import app.core.preprocessing as pp
from .reviews_processing import process_query


def fact_check_text(query: str) -> dict:
    """
    Perform a fact check on the given query using Google Fact Check API and process the reviews.

    Args:
        query (str): The query to be fact-checked.

    Returns:
        dict: A dictionary containing the results of the fact check.
    """
    return process_query(query)


def fact_check_link(link: str) -> dict:
    """
    Perform a fact check on the given link using Google Fact Check API.
    This function checks if the link is a social media link and processes it accordingly.
    If the link is not a social media link, it processes it as a random URL.
    Args:
        link (str): The link to be fact-checked.
    Returns:
        dict: A dictionary containing the results of the fact check.
    """
    social_media = [
        {"function": pp.youtube_short, "regex": r"youtube\.com/shorts/[^/?]+"},
        {"function": pp.insta_post, "regex": r"instagram\.com/p/[^/?]+"},
        {"function": pp.tiktok, "regex": r"tiktok\.com/@[^/]+/video/([^/?]+)"},
        {"function": pp.tiktok, "regex": r"vm\.tiktok\.com/([^/?]+)"},
        {"function": pp.reddit, "regex": r"reddit\.com/r/[^/]+/comments/([^/?]+)"},
        {"function": pp.x_post, "regex": r"x\.com/.+/status/[^/?]+"},
    ]

    for sm in social_media:
        if re.search(sm["regex"], link) is not None:
            return sm["function"](link)
    return pp.random_url(link)


def fact_check_files(text: str, files: List[UploadFile]) -> dict:
    """
    Perform a fact check on the given text and files using Google Fact Check API.
    This function processes the text and files, and returns the results of the fact check.
    Args:
        text (str): The text to be fact-checked.
        files (List[UploadFile]): A list of files to be fact-checked.
    Returns:
        dict: A dictionary containing the results of the fact check.
    """
    return pp.user_request_with_files(text, files)
