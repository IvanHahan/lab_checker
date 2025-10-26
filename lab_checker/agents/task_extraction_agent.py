"""Task extraction agent for analyzing student submissions for specific tasks."""

from typing import Any, Dict

from ..chains import chain_json_with_thinking
from ..llm import OpenAIModel


class TaskExtractionAgent:
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
            )
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

You must structure your response in the following JSON format:
{{
    "variant_requirements": "<Variant Specific Requirements>",
    "implemented_solution": "<Detailed description of what the student implemented>",
    "code_excerpts": ["<Relevant code excerpts from the submission>"],
    "visual_references": [
        {{"tag": "<<Image/Diagram Tag with brackets>>", "description": "<Description of relevance>"}},
        ...
    ]
}}

## Guidelines:
- Analyze given task specification and what is required to be implemented.
- Identify the content relevant to the specific task.
- Analyze what the student has actually implemented for the task.
- Extract ONLY relevant code excerpts and visual references from the submission related to the task.
- Ensure the final output is valid JSON adhering to the specified structure.
- NEVER make up any information. If something is not present in the submission, indicate it as such.

## Response Template (strict - include start/end tags):
<reasoning>Step-by-step thought process with numbered points (8 steps max, <=20 words each)</reasoning>
<result>task_json</result>
"""
