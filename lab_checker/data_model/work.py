"""Work agent output data models."""

from typing import Optional

from pydantic import BaseModel, Field


class TaskAnswer(BaseModel):
    """Student's answer/implementation for a single task"""

    task_id: str
    task_title: str
    status: str = Field(
        description="Completion status: not_attempted | partial | complete"
    )
    input_data: list[str] = Field(default_factory=list)
    implementation_summary: str
    code_excerpts: dict[str, str] = Field(
        default_factory=dict, description="Filename to code excerpt mapping"
    )
    deviations_from_requirements: list[str] = Field(default_factory=list)
    missing_elements: list[str] = Field(default_factory=list)
    extra_features: list[str] = Field(default_factory=list)


class OverallSubmissionQuality(BaseModel):
    """Overall quality assessment of the submission"""

    code_organization: str
    naming_conventions: str
    documentation_level: str = Field(description="poor | fair | good | excellent")
    completeness: str


class WorkAnalysis(BaseModel):
    """Complete work analysis from Work Agent"""

    submission_metadata: dict[str, Optional[str]] = Field(
        default_factory=dict,
        description="Student name, group, course, variant, submission date, etc.",
    )
    task_answers: list[TaskAnswer] = Field(default_factory=list)
    overall_submission_quality: Optional[OverallSubmissionQuality] = None
    general_observations: list[str] = Field(default_factory=list)
