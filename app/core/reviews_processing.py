import json
from typing import List
from google import genai
import os
from .google_fact_check import Review 
api_key = os.getenv("API_KEY")

client = genai.Client(api_key=api_key)


def review_to_tuple(review: Review) -> tuple:
    return (
        review.rating,
        review.reviewDate.isoformat() if review.reviewDate else None,
        review.publisher.name,
        review.publisher.site,
        review.information_url
    )

def process_reviews(query : str,reviews: List[Review]): 
    prompt = f"""
Given the query: {query}

and the reviews: [{','.join([str(review_to_tuple(i)) for i in reviews])}]

where each review is a tuple of (rating, reviewDate, publisher_name, publisher_site, information_url),
determine the following:
1. The overall truth of the query (e.g., "true", "false", "misleading", "innacuracy").
2. The sources that agree with the query and their information.
3. The sources that disagree with the query and their information.
4. The certainty of the overall truth (0-1 scale).


Use this JSON schema:
Publisher = {{'name': str, 'site': str}}
Source = {{'publisher': Publisher, 'information_url': str, 'review': str}}
Return: {{"status": str, "agree_sources": List[Source], "disagree_sources": List[Source], "certenty": float}}
"""

    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=prompt,
    )

    data = json.loads(response.text[7:-3])
    return data

