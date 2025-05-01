import os
from datetime import datetime
from typing import List
from pydantic import BaseModel
import requests

base_url = "https://factchecktools.googleapis.com/"
api_version = "v1alpha1"
api_key = os.getenv("API_KEY")

class Publisher(BaseModel):
    name: str
    site: str | None = None


class ClaimReview(BaseModel):
    publisher: Publisher
    url: str
    title: str
    reviewDate: datetime | None = None
    languageCode: str
    textualRating: str

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
        json_decoders = {
            datetime: lambda v: datetime.fromisoformat(v)
        }
    
    
class Claim(BaseModel):
    text: str
    claimant: str
    claimDate: datetime
    claimReview: List[ClaimReview]

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
        json_decoders = {
            datetime: lambda v: datetime.fromisoformat(v)
        }


class Review(BaseModel):
    rating: str
    reviewDate: datetime | None = None
    publisher : Publisher
    information_url : str | None = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
        json_decoders = {
            datetime: lambda v: datetime.fromisoformat(v)
        }
    


def get_claims(query: str) -> Claim:
    url = f"{base_url}{api_version}/claims:search"
    params = {
        "query": query,
        "pageSize": 10,
        "key": api_key
    }
    response = requests.get(url, params=params)
    response_json = response.json()
    claims = []
    for claim in response_json.get("claims", []):
        claims.append(Claim(**claim))
    return claims

def get_claims_image(image_uri: str) -> Claim:
    url = f"{base_url}{api_version}/claims:imageSearch"
    params = {
        "imageUri": image_uri,
        "key": api_key
    }
    response = requests.get(url, params=params)
    response_json = response.json()
    print(response.status_code)
    print(response_json)
    claims = []
    for claim in response_json.get("claims", []):
        claims.append(Claim(**claim))
    return claims



def get_reviews_ratings(claim: Claim) -> List[Review]:
    ratings = []
    for review in claim.claimReview:
        ratings.append(Review(
            rating=review.textualRating,
            reviewDate=review.reviewDate,
            information_url=review.url,
            publisher=review.publisher
        ))
    return ratings

def get_reviews_text(query : str) -> List[Review]:
    claims = get_claims(query)
    reviews = []
    for claim in claims:
        reviews.extend(get_reviews_ratings(claim))
    return reviews




def get_reviews_image(uri : str) -> List[Review]:
    claims = get_claims_image(uri)
    reviews = []
    for claim in claims:
        reviews.extend(get_reviews_ratings(claim))
    return reviews