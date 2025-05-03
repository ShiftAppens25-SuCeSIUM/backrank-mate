import os
import re
from enum import Enum
from typing import Callable, List, Optional

from fastapi import APIRouter, File, Form, UploadFile
from pydantic import BaseModel

import app.core.preprocessing as pp
from app.core.cache import cached_fact_check, cached_fact_check_link
from app.core.core import fact_check_files
from app.core.reviews_processing import GeminiBogusError
from fastapi import HTTPException

router = APIRouter()


class FactCheckStatus(str, Enum):
    TRUE = ("true",)
    FALSE = ("false",)
    MISLEADING = "misleading"
    UNKNOWN = "unknown"


class OutPublisher(BaseModel):
    name: str
    site: str | None


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


@router.post("/fact_check/link", response_model=OutFactChecking)
def check_link(payload: InText):
    url = payload.query
    try:
        return cached_fact_check_link(url)
    except GeminiBogusError as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.post("/fact_check/text", response_model=OutFactChecking)
def check_text(payload: InText):
    try:
        return cached_fact_check(payload.query)
    except GeminiBogusError as e:
        raise HTTPException(status_code=422, detail=str(e))


class InFileUpload(BaseModel):
    query: str


@router.post("/fact_check/file", response_model=OutFactChecking)
async def check_file(query: str = Form(...), files: List[UploadFile] = File(...)):
    try:
        return fact_check_files(query, files)
    except GeminiBogusError as e:
        raise HTTPException(status_code=422, detail=str(e))
