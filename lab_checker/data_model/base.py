"""Base data models for the lab checker system."""

from typing import Optional

from pydantic import BaseModel, Field


class TechnicalSpecs(BaseModel):
    """Technical specifications for a task"""

    languages: list[str] = Field(default_factory=list)
    frameworks: list[str] = Field(default_factory=list)
    tools: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)


class EvaluationCriteria(BaseModel):
    """Evaluation criteria for a task"""

    total_points: Optional[str] = None
    criteria: list[str] = Field(default_factory=list)
    deadline: Optional[str] = None
