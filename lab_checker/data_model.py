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


class StudentSubmission(BaseModel):
    student_id: str
    assignment_id: str
    variant: int | None = None


# Work Agent Output Models


class CodeExcerpts(BaseModel):
    """Code excerpts extracted from student submission"""

    filename: str
    code: str = Field(default="")


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
