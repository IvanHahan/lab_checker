"""Task extraction agent for analyzing student submissions for specific tasks."""

from typing import Any, Dict

from ..chains import chain_json_with_thinking
from ..llm import OpenAIModel


class TaskSubmissionAgent:
    """
    Agent responsible for extracting what a student implemented for a specific task
    from their submission. This agent focuses on identifying task-specific content
    and implementation details.
    """

    def __init__(self, llm: OpenAIModel):
        self.llm = llm

    def extract_task_submission(
        self, submission_content: Dict[str, Any], task: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Extract student's implementation for a specific task from their submission.

        Args:
            submission_content: Parsed submission content (text and visuals)
            task: Task specification from assignment

        Returns:
            Dictionary containing task-specific submission analysis
        """
        response = chain_json_with_thinking(self.llm).invoke(
            self.EXTRACT_TASK_PROMPT.format(
                pdf_content=submission_content["text"], task_description=task
            ),
            refine_response=True,
        )

        return response

    def save_task_submission(
        self, task_data: Dict[str, Any], task_index: int, output_dir: str = "."
    ) -> None:
        """
        Save extracted task submission data to a JSON file.

        Args:
            task_data: Task submission data from extract_task_submission
            task_index: Index of the task (for filename generation)
            output_dir: Directory where to save the task JSON file
        """
        output_path = f"{output_dir}/task_{task_index}.json"
        with open(output_path, "w") as f:
            f.write(task_data.model_dump_json(indent=2, ensure_ascii=False))

    @property
    def EXTRACT_TASK_PROMPT(self) -> str:
        """Prompt template for task extraction from submission."""
        return """
# Task Extraction Prompt
You are an expert at analyzing laboratory assignment specifications.
Your task is to analyze given task specification and extract all the context from student submission that is relevant to the specific task.

## Task Specification:
{task_description}

## PDF Content:
{pdf_content}

Task Submission JSON Schema:
{{
    "variant_requirements": "<Variant Specific Requirements only if specified>",
    "implemented_solution": "<Detailed description of what the student implemented for this task>",
    "code_excerpts": ["<Relevant code excerpts for the task>"],
    "visual_references": [
        {{"tag": "<<Image/Diagram Tag with brackets>>", "description": "<Description of the visual content if available>"}},
        ...
    ]
}}

## Guidelines:
- Analyze given task specification carefully.
- Identify the content related to the given task.
- Identify any variant-specific requirements if applicable.
- Extract ONLY relevant context including code excerpts and visual references.
- Ensure the final output is valid JSON adhering to the specified structure.
- NEVER make up any information. If something is not present in the submission, indicate it as such.

## Response Template (strictly follow):
THINKING: <Step-by-step thought process with numbered points (8 steps max, <=20 words each)>
FINAL_OUTPUT: <task_json>
"""
