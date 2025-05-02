"""Process reviews using Google GenAI API.
This module provides functionality to process reviews and generate a fact-checking report.
levaraging  the Google GenAI API.
"""

import json
import os
from typing import List

from google import genai
from google.genai.types import GenerateContentConfig, GoogleSearch, Tool

from .google_fact_check import Review

api_key = os.getenv("API_KEY")

client = genai.Client(api_key=api_key)


def review_to_tuple(review: Review) -> tuple:
    """Convert a Review object to a tuple for processing.
    Args:
        review (Review): The Review object to convert.
    Returns:
        tuple: A tuple containing the review information.
    """
    return (
        review.rating,
        review.reviewDate.isoformat() if review.reviewDate else None,
        review.publisher.name,
        review.publisher.site,
        review.information_url,
    )


def process_reviews(query: str, reviews: List[Review]) -> dict:
    """
    Process reviews using Google GenAI API and generate a fact-checking report.
    Args:
        query (str): The query to be fact-checked.
        reviews (List[Review]): A list of Review objects to be processed.
    Returns:
        dict: A dictionary containing the results of the fact check.
    """
    google_search_tool = Tool(google_search=GoogleSearch())

    prompt = f"""
Given the query: {query}

and the reviews: [{','.join([str(review_to_tuple(i)) for i in reviews])}].\
    If there are no reviews, search the web and find your sources, filling in the information.

where each review is a tuple of (rating, reviewDate, publisher_name, publisher_site, information_url),
determine the following:
1. The overall truth of the query (e.g., "true", "false", "misleading", "innacuracy").
2. The sources that agree with the query and their information, sorted by most recent.
3. The sources that disagree with the query and their information, sorted by most recent.
4. The certainty of the overall truth (0-1 scale).
5. The query itself.


Your answer must be a valid JSON string (no extra text), following this schema.
Publisher = {{'name': str, 'site': str}}
Source = {{'publisher': Publisher, 'information_url': str, 'review': str}}
Return: {{"status": str, "agree_sources":\
    List[Source], "disagree_sources": List[Source], "certainty": float, "query": str}}
"""

    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=prompt,
        config=GenerateContentConfig(
            tools=[google_search_tool],
            response_modalities=["TEXT"],
        ),
    )
    t = response.text
    t = t.split("```json")[1]
    t = t.split("```")[0]
    data = json.loads(t)
    return data
