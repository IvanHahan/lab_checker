"""Assignment-related data models."""

from typing import Optional

from pydantic import BaseModel, Field

from .base import EvaluationCriteria, TechnicalSpecs


class Task(BaseModel):
    """Represents a single task/assignment"""

    id: str
    title: str
    description: str
    requirements: list[str] = Field(default_factory=list)
    input_data: list[str] = Field(default_factory=list)
    deliverables: list[str] = Field(default_factory=list)
    technical_specs: Optional[TechnicalSpecs] = None
    evaluation: Optional[EvaluationCriteria] = None
    learning_objectives: list[str] = Field(default_factory=list)
    hints: list[str] = Field(default_factory=list)
    examples: list[str] = Field(default_factory=list)
    visual_references: list[str] = Field(default_factory=list)


class DocumentMetadata(BaseModel):
    """Metadata about the assignment document"""

    title: str
    course: Optional[str] = None
    academic_period: Optional[str] = None
    total_tasks: Optional[int] = None


class GlobalRequirements(BaseModel):
    """Global requirements applicable to all tasks"""

    general_guidelines: list[str] = Field(default_factory=list)
    submission_format: Optional[str] = None
    academic_integrity: Optional[str] = None


class Assignment(BaseModel):
    """Complete assignment extracted from a PDF document"""

    document_metadata: DocumentMetadata
    tasks: list[Task]
    global_requirements: Optional[GlobalRequirements] = None
