"""Google Fact Check API client.
This module provides functionality to interact with the Google Fact Check API
and retrieve claims and reviews related to a given query.
It includes classes for representing claims, reviews, and publishers,
as well as functions for making API requests and processing the results.
"""

import os
from datetime import datetime
from typing import List

import requests
from pydantic import BaseModel

BASE_URL = "https://factchecktools.googleapis.com/"
API_VERSION = "v1alpha1"
api_key = os.getenv("API_KEY")


class CustomBaseModel(BaseModel):
    """Custom BaseModel to handle JSON encoding and decoding."""

    class Config:
        """Configuration for BaseModel."""

        json_encoders = {datetime: lambda v: v.isoformat()}
        json_decoders = {datetime: datetime.fromisoformat}


class Publisher(BaseModel):
    """Publisher information for the claim review."""

    name: str
    site: str | None = None


class ClaimReview(CustomBaseModel):
    """Claim review information."""

    publisher: Publisher
    url: str
    title: str
    reviewDate: datetime | None = None
    languageCode: str
    textualRating: str


class Claim(CustomBaseModel):
    """Claim information."""

    text: str
    claimant: str | None = None
    claimDate: datetime | None = None
    claimReview: List[ClaimReview]


class Review(CustomBaseModel):
    """Review information."""

    rating: str
    reviewDate: datetime | None = None
    publisher: Publisher
    information_url: str | None = None


def get_claims(query: str) -> Claim:
    """Get claims related to the given query from the Google Fact Check API.
    Args:
        query (str): The query to search for claims.
    Returns:
        List[Claim]: A list of Claim objects containing claim information.
    """
    url = f"{BASE_URL}{API_VERSION}/claims:search"
    params = {"query": query, "pageSize": 10, "key": api_key}
    response = requests.get(url, params=params, timeout=1000)
    response_json = response.json()
    claims = []
    for claim in response_json.get("claims", []):
        claims.append(Claim(**claim))
    return claims


def get_reviews_ratings(claim: Claim) -> List[Review]:
    """Get reviews and ratings for a given claim.
    Args:
        claim (Claim): The claim object to get reviews for.
    Returns:
        List[Review]: A list of Review objects containing review information.
    """
    ratings = []
    for review in claim.claimReview:
        ratings.append(
            Review(
                rating=review.textualRating,
                reviewDate=review.reviewDate,
                information_url=review.url,
                publisher=review.publisher,
            )
        )
    return ratings


def get_reviews_text(query: str) -> List[Review]:
    """Get reviews and ratings for a given query.
    Args:
        query (str): The query to search for reviews.
    Returns:
        List[Review]: A list of Review objects containing review information.
    """
    claims = get_claims(query)
    reviews = []
    for claim in claims:
        reviews.extend(get_reviews_ratings(claim))

    return reviews
