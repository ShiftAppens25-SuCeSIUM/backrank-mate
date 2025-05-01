from enum import Enum
from typing import Optional
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()

class FactCheckStatus(str, Enum):
    TRUE = "true",
    FALSE = "false",
    MISLEADING = "misleading"

class OutSource(BaseModel):
    entity: str
    link: Optional[str]
    explanation: str


class InText(BaseModel):
    query: str

class OutFactChecking(BaseModel):
    status: FactCheckStatus
    agree_sources: list[OutSource]
    disagree_sources: list[OutSource]
    certainty: float

@router.post("/fact_check/text", response_model=OutFactChecking)
def check_text(payload: InText):
    agree_source = OutSource(
        entity="O ChatGPT",
        link="https://chatgpt.com",
        explanation=payload.query
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
