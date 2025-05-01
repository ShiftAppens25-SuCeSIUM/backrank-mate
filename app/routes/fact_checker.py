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
    status: str
    agree_sources: List[OutSource]
    disagree_sources: List[OutSource]
    certainty: float
    query: str

@router.post("/fact_check/insta_post", response_model=OutFactChecking)
def check_insta_post(payload: InInstaPost):
    content = pp.insta_post(payload.shortcode)
    return fact_check(content)

@router.post("/fact_check/tiktok", response_model=OutFactChecking)
def check_insta_post(payload: InInstaPost):
    content = pp.tiktok(payload.shortcode)
    return fact_check(content)

@router.post("/fact_check/text", response_model=OutFactChecking)
def check_text(payload: InText):
    return fact_check(payload.query)
