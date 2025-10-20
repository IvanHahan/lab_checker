"""Data models package for lab checker system."""

# Base models
# Assignment models
from .assignment import Assignment, DocumentMetadata, GlobalRequirements, Task
from .base import EvaluationCriteria, TechnicalSpecs

# Submission models
from .submission import StudentSubmission

# Work analysis models
from .work import OverallSubmissionQuality, TaskAnswer, WorkAnalysis

__all__ = [
    # Base models
    "TechnicalSpecs",
    "EvaluationCriteria",
    # Assignment models
    "Task",
    "DocumentMetadata",
    "GlobalRequirements",
    "Assignment",
    # Work analysis models
    "TaskAnswer",
    "OverallSubmissionQuality",
    "WorkAnalysis",
    # Submission models
    "StudentSubmission",
]
