"""Assignment extraction agent for parsing assignment PDFs and extracting task structures."""

import os
from typing import Any, Dict

from ..chains import chain_json_with_thinking
from ..doc_parsing import parse_pdf
from ..llm import OpenAIModel


class AssignmentExtractionAgent:
    """
    Agent responsible for extracting assignment tasks and requirements from PDF documents.
    This agent focuses on understanding assignment specifications and structuring them
    for further processing by other agents.
    """

    def __init__(self, llm: OpenAIModel):
        self.llm = llm

    def extract_assignment(self, assignment_pdf: str) -> Dict[str, Any]:
        """
        Extract assignment tasks and structure from a PDF document.

        Args:
            assignment_pdf: Path to assignment PDF file

        Returns:
            Dictionary containing structured assignment data with tasks and requirements
        """
        parsed_content = parse_pdf(assignment_pdf)

        response = chain_json_with_thinking(self.llm).invoke(
            self.ASSIGNMENT_EXTRACTION_PROMPT.format(pdf_content=parsed_content["text"])
        )

        return response

    def save_assignment(
        self, assignment_data: Dict[str, Any], output_path: str = "assignment.json"
    ) -> None:
        """
        Save extracted assignment data to a JSON file.

        Args:
            assignment_data: Structured assignment data from extract_assignment
            output_path: Path where to save the assignment JSON file
        """
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w") as f:
            f.write(assignment_data.model_dump_json(indent=2, ensure_ascii=False))

    @property
    def ASSIGNMENT_EXTRACTION_PROMPT(self) -> str:
        """Prompt template for assignment extraction."""
        return """
# Assignment Task Extraction Prompt
You are an expert at analyzing laboratory assignment specifications.
Your task is to carefully examine the provided assignment specification content, which may include text and visual elements such as images or diagrams.
Based on your analysis, extract and list all tasks defined in the assignment along with their detailed requirements

You must structure your response in the following JSON format:
{{
  "course": "<Course Name>",
  "tasks": [
    {{
        "name": "<Task Name>",
        "description": "<Task Description>",
        "deliverables": "<List of required deliverables>",
        "requirements": "<Detailed requirements for the task>",
        "evaluation_criteria": ["<Criteria for evaluating the task must be inferred if not stated>"],
        }},
    ...
  ]
}}

## Guidelines:
- Thoroughly analyze both textual and visual content in the assignment specification.
- Identify each task and its requirements based on the assignment specification.
- Ensure the final output is valid JSON adhering to the specified structure.
- Understand how to evaluate the task and come up with evaluation criteria. Don't be harsh, including stylistic aspects.
- NEVER make up any information. If something is not present in the context, indicate it as such.

## Assignment PDF Content:
{pdf_content}

## Response Template (strict - include all tags):
<reasoning>Step-by-step thought process with numbered points (8 steps max, <=20 words each)</reasoning>
<result>task_list_json</result>
"""
