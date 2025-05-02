import os
import re
from enum import Enum
from typing import Callable, List, Optional

from fastapi import APIRouter, File, Form, UploadFile
from pydantic import BaseModel

import app.core.preprocessing as pp
from app.core.cache import cached_fact_check

router = APIRouter()


class FactCheckStatus(str, Enum):
    TRUE = ("true",)
    FALSE = ("false",)
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
        {"function": pp.x_post, "regex": r"x\.com/.+/status/[^/?]+"},
    ]

    for sm in social_media:
        if re.search(sm["regex"], url) is not None:
            return sm["function"]


@router.post("/fact_check/link", response_model=OutFactChecking)
def check_link(payload: InText):
    url = payload.query
    fn = get_social_media(url)

    if fn is None:
        cached_fact_check(pp.random_url(url))

    return cached_fact_check(fn(url))


@router.post("/fact_check/text", response_model=OutFactChecking)
def check_text(payload: InText):
    return cached_fact_check(payload.query)


class InFileUpload(BaseModel):
    query: str


def store_files(request_id: str, files: List[UploadFile]):
    base_dir = f"{os.getenv('TEMPORARY_DIRECTORY')}/user_data"
    directory = f"{base_dir}/{request_id}"
    os.makedirs(directory, exist_ok=True)
    for file in files:
        with open(f"{directory}/{file.filename}", "wb") as f:
            f.write(file.file.read())


def delete_files(request_id: str):
    base_dir = f"{os.getenv('TEMPORARY_DIRECTORY')}/user_data"
    directory = f"{base_dir}/{request_id}"
    if os.path.exists(directory):
        for file in os.listdir(directory):
            os.remove(f"{directory}/{file}")
        os.rmdir(directory)


@router.post("/fact_check/file", response_model=OutFactChecking)
async def check_file(query: str = Form(...), files: List[UploadFile] = File(...)):
    return cached_fact_check(pp.user_request_with_files(query, files))
