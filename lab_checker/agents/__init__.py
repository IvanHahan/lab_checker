"""
Lab Checker Agents Module

This module provides specialized agents for different aspects of laboratory assignment checking:

- AssignmentAgent: Comprehensive assignment analysis using structured prompts
- AssignmentExtractionAgent: Simple assignment task extraction
- TaskExtractionAgent: Extract task-specific content from submissions
- TaskSubmissionAgent: Comprehensive task submission analysis
- TaskEvaluationAgent: Task evaluation and grading
- LabCheckerCoordinator: Orchestrates the entire workflow
- WorkAgentLarge: Legacy agent with backward compatibility
"""

from .assignment_extraction_agent import AssignmentExtractionAgent
from .evaluation_agent import TaskEvaluationAgent
from .lab_checker_coordinator import LabCheckerCoordinator
from .task_extraction_agent import TaskExtractionAgent
from .task_submission_agent import TaskSubmissionAgent

__all__ = [
    "AssignmentExtractionAgent",
    "TaskExtractionAgent",
    "TaskSubmissionAgent",
    "TaskEvaluationAgent",
    "LabCheckerCoordinator",
]


def create_lab_checker(llm_model) -> LabCheckerCoordinator:
    """
    Convenience function to create a lab checker coordinator with all agents.

    Args:
        llm_model: The LLM model to use for all agents

    Returns:
        LabCheckerCoordinator instance ready for use
    """
    return LabCheckerCoordinator(llm_model)
