from typing import Any, Dict, List, Optional

from lab_checker.message_utils import prepare_message_with_visuals

from ..chains import chain_json_with_thinking
from ..doc_parsing import parse_pdf
from ..llm import OpenAIModel


class WorkAgentLarge:
    """
    Agent responsible for analyzing student submissions and extracting
    what the student implemented for each task in the assignment.
    """

    def __init__(self, llm: OpenAIModel):
        self.llm = llm

    def run(
        self,
        assignment_pdf: Optional[str] = None,
        submission_pdf: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Analyze a student submission for all tasks in an assignment.

        Args:
            assignment: Assignment specification with tasks
            submission_pdf: Path to submission PDF file

        Returns:
            Dictionary with submission analysis results
        """
        task_responses = self._extract_tasks(assignment_pdf)

        with open("assignment.json", "w") as f:
            f.write(task_responses.model_dump_json(indent=2, ensure_ascii=False))

        task_submissions = []
        for task in task_responses.result["tasks"]:
            messages = self._prepare_pdf_messages(
                submission_pdf,
                EXTRACT_TASK_PROMPT.format(task_description=task),
            )
            response = chain_json_with_thinking(self.llm).invoke("", messages=messages)
            with open(f"task_{task['name']}.json", "w") as f:
                f.write(response.model_dump_json(indent=2, ensure_ascii=False))
            task_submissions.append(response.result)

        messages = self._prepare_pdf_messages(submission_pdf, WORK_AGENT_PROMPT)
        response = chain_json_with_thinking(self.llm).invoke("", messages=messages)
        return response

    def _extract_tasks(self, assignment_pdf: str):
        parsed_content = parse_pdf(assignment_pdf)

        response = chain_json_with_thinking(self.llm).invoke(
            ASSIGNMENT_EXTRACTION_PROMPT.format(pdf_content=parsed_content["text"])
        )
        return response

    def _prepare_pdf_messages(self, pdf: str, system_prompt: str) -> List[dict]:
        parsed_content = parse_pdf(pdf)
        message_content = prepare_message_with_visuals(
            parsed_content["text"],
            parsed_content["visuals"],
        )
        messages = [
            {
                "role": "system",
                "content": system_prompt,
            },
            {
                "role": "user",
                "content": message_content,
            },
        ]
        return messages


EXTRACT_TASK_PROMPT = """
# Task Extraction Prompt
You are an expert at analyzing laboratory assignment specifications.
Your task is to analyze given task specification and extract all the context from student submission that is relevant to the task.

## Task Specification:
{task_description}

You must structure your response in the following JSON format:
{{
    "variant_requirements": "<Variant Specific Requirements>",
    "implemented_solution": "<Detailed description of what the student implemented>",
    "code_excerpts": ["<Relevant code excerpts from the submission>"],
    "visual_references": ["<References to any images or diagrams from the submission>"]
}}
## Guidelines:
- Thoroughly analyze both textual and visual content in the submission.
- Identify each task and its requirements based on the assignment specification.
- Understand exactly what must be implemented for each task, including any variant-specific requirements.
- Analyze what the student has actually implemented for each task.
- Compare the implemented solution against the task requirements to identify any mistakes or omissions.
- Ensure the final output is valid JSON adhering to the specified structure.
## Response Format (Strict, including tags):
<reasoning>brief, numbered steps. No secrets or hidden scratchwork.</reasoning>
<result>task_json</result>
"""


ASSIGNMENT_EXTRACTION_PROMPT = """
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
        }},
    ...
  ]
}}
## Guidelines:
- Thoroughly analyze both textual and visual content in the assignment specification.
- Identify each task and its requirements based on the assignment specification.
- Ensure the final output is valid JSON adhering to the specified structure. 

## Assignment PDF Content:
{pdf_content}

## Response Format (Strict, including tags):
<reasoning>brief, numbered steps. No secrets or hidden scratchwork.</reasoning>
<result>task_list_json</result>
"""


WORK_AGENT_PROMPT = """
# Student Submission Analysis Prompt
You are an expert at analyzing student submissions for laboratory assignments.

Your task is to carefully examine the provided student submission content, which may include text and visual elements such as images or diagrams.
Based on your analysis, provide a detailed breakdown of what the student has implemented for each task in the assignment.

You must structure your response in the following JSON format:
{{
  "course": "<Course Name>",
  "student_name": "<Student Name>",
  "assignment_variant": "<Assignment Variant>",
  "teacher_name": "<Teacher Name>",
  "tasks": [
    {{
        "task_name": "<Task Name>",
        "task_description": "<Task Description>",
        "variant_requirements": "<Variant Specific Requirements>",
        "implemented_solution": "<Detailed description of what the student implemented>",
        "mistakes_or_omissions": "<List any mistakes or omissions>",
        "status": <complete|incomplete|partial>,
    }},
    ...
  ]
}}

## Guidelines:
- Thoroughly analyze both textual and visual content in the submission.
- Identify each task and its requirements based on the assignment specification.
- Understand exactly what must be implemented for each task, including any variant-specific requirements.
- Analyze what the student has actually implemented for each task.
- Compare the implemented solution against the task requirements to identify any mistakes or omissions.
- Determine the completion status for each task
- Ensure the final output is valid JSON adhering to the specified structure.

## Response Format (Strict, including tags):
<reasoning>brief, numbered steps. No secrets or hidden scratchwork.</reasoning>
<result>task_json</result>
"""
