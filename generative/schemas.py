# generative/schemas.py
"""Pydantic schemas the LLM is constrained to (Ollama structured outputs)."""
from typing import Literal
from pydantic import BaseModel, Field


class ComplianceFinding(BaseModel):
    requirement:    str
    status:         Literal["PASS", "FAIL", "REVIEW"]
    explanation:    str
    recommendation: str
    quote: str = Field(description="Verbatim excerpt from the document supporting the status; empty if none")


class ComplianceReport(BaseModel):
    items: list[ComplianceFinding]


class ActionItem(BaseModel):
    task:     str
    priority: Literal["High", "Medium", "Low"]
    owner:    str = "Unassigned"
    deadline: str = "Not specified"
    status:   Literal["Pending", "In Progress", "Done"] = "Pending"


class ActionItemList(BaseModel):
    items: list[ActionItem]
