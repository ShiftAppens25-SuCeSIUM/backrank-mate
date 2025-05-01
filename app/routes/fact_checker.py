from enum import Enum
from typing import List, Optional
from fastapi import APIRouter
from pydantic import BaseModel
import app.core.preprocessing as pp
from app.core.core import fact_check

router = APIRouter()

class FactCheckStatus(str, Enum):
    TRUE = "true",
    FALSE = "false",
    MISLEADING = "misleading"
    UNKNOWN = "unknown"

class OutPublisher(BaseModel):
    name: str
    site: str

class OutSource(BaseModel):
    publisher: OutPublisher
    information_url: str
    review: str

class InText(BaseModel):
    query: str

class InInstaPost(BaseModel):
    shortcode: str

class OutFactChecking(BaseModel):
    status: FactCheckStatus
    agree_sources: List[OutSource]
    disagree_sources: List[OutSource]
    certainty: float

@router.post("/fact_check/insta_post", response_model=OutFactChecking)
def check_insta_post(payload: InInstaPost):
    content = pp.insta_post(payload.shortcode)
    return example_response()

@router.post("/fact_check/text", response_model=OutFactChecking)
def check_text(payload: InText):
    res = fact_check(payload.query)
    print(res)
    return res

def example_response():
    agree_source = OutSource(
        entity="O ChatGPT",
        link="https://chatgpt.com",
        explanation="Skill issue"
    )

    disagree_source = OutSource(
        entity="As vozes da minha cabeça",
        link=None,
        explanation="não se calam"
    )

    response = OutFactChecking(
        status=FactCheckStatus.MISLEADING,
        agree_sources=[agree_source],
        disagree_sources=[disagree_source],
        certainty=0.5
    )

    return response
