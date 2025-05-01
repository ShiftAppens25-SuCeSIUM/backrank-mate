from enum import Enum
from typing import Callable, List, Optional
from fastapi import APIRouter
from pydantic import BaseModel
import app.core.preprocessing as pp
from app.core.core import fact_check
import re

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

class OutFactChecking(BaseModel):
    status: str
    agree_sources: List[OutSource]
    disagree_sources: List[OutSource]
    certainty: float
    query: str

def get_social_media(url: str) -> Optional[Callable[[str], OutFactChecking]]:
    social_media = [
        {"function": pp.youtube_short, "regex": r"youtube\.com/shorts/[^/?]+"},
        {"function": pp.insta_post, "regex": r"instagram\.com/p/[^/?]+"},
        {"function": pp.tiktok, "regex": r"tiktok\.com/@[^/]+/video/([^/?]+)"},
        {"function": pp.tiktok, "regex": r"vm\.tiktok\.com/([^/?]+)"},
        {"function": pp.reddit, "regex": r"reddit\.com/r/[^/]+/comments/([^/?]+)"},
    ]

    for sm in social_media:
        if re.search(sm["regex"], url) is not None:
            return sm["function"]

@router.post("/fact_check/link", response_model=OutFactChecking)
def check_link(payload: InText):
    url = payload.query
    fn = get_social_media(url)

    if fn is None:
        pass # TODO: Feed directly to Gemini

    return fact_check(fn(url))

@router.post("/fact_check/text", response_model=OutFactChecking)
def check_text(payload: InText):
    return fact_check(payload.query)
