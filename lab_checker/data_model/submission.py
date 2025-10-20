"""Student submission data models."""

from pydantic import BaseModel


class StudentSubmission(BaseModel):
    """Represents a student's submission information"""

    student_id: str
    assignment_id: str
    variant: int | None = None
