"""Fact-checking module for processing reviews using Google Fact Check API.
This module provides functionality to perform a fact check on a given query"""

from typing import List
from .reviews_processing import process_query
import app.core.preprocessing as pp
import re
from fastapi import UploadFile

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
    return pp.user_request_with_files(text, files)