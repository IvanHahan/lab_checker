import json
import os
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
        # Check if assignment.json already exists, if not extract tasks
        if os.path.exists("assignment.json"):
            with open("assignment.json", "r") as f:
                task_responses = json.load(f)
                tasks = task_responses["result"]["tasks"]
        else:
            task_responses = self._extract_assignment(assignment_pdf)
            tasks = task_responses.result["tasks"]
            with open("assignment.json", "w") as f:
                f.write(task_responses.model_dump_json(indent=2, ensure_ascii=False))

        submission_pdf = parse_pdf(submission_pdf)
        task_submissions = []
        for i, task in enumerate(tasks):
            response = self._extract_submission_for_task(
                submission_pdf=submission_pdf,
                task=task,
            )
            with open(f"task_{i}.json", "w") as f:
                f.write(response.model_dump_json(indent=2, ensure_ascii=False))
            task_submissions.append(response.result)
            response = self._evaluate_task_submission(
                task, response.result, submission_pdf.get("visuals", {})
            )
            with open(f"task_{i}_eval.json", "w") as f:
                f.write(response.model_dump_json(indent=2, ensure_ascii=False))

        return response

    def _extract_assignment(self, assignment_pdf: str):
        parsed_content = parse_pdf(assignment_pdf)

        response = chain_json_with_thinking(self.llm).invoke(
            ASSIGNMENT_EXTRACTION_PROMPT.format(pdf_content=parsed_content["text"])
        )
        return response

    def _extract_submission_for_task(
        self, submission_pdf: Dict[str, any], task: Dict[str, Any]
    ):
        response = chain_json_with_thinking(self.llm).invoke(
            EXTRACT_TASK_PROMPT.format(
                pdf_content=submission_pdf["text"], task_description=task
            )
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

    def _evaluate_task_submission(
        self,
        task: Dict[str, Any],
        submission: Dict[str, Any],
        visuals: Dict[str, Any],
    ):
        visual_references = submission.pop("visual_references", [])
        visual_text = ""
        for visual_ref in visual_references:
            tag = visual_ref.get("tag", "")
            description = visual_ref.get("description", "")
            if tag:
                visual_text += f"\n{description}:\n{tag}\n"  # This will be replaced with actual image
        visual_content = prepare_message_with_visuals(
            text=visual_text,
            visuals=visuals,
        )
        message_content = [
            {
                "type": "input_text",
                "text": EVALUATE_PROMPT.format(
                    task_description=task,
                    student_submission=json.dumps(submission, ensure_ascii=False),
                ),
            },
            *visual_content,
        ]

        response = chain_json_with_thinking(self.llm).invoke(
            "",
            messages=[
                {
                    "role": "user",
                    "content": message_content,
                },
            ],
        )
        return response


EXTRACT_TASK_PROMPT = """
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
- Extract relevant code excerpts and visual references from the submission related to the task.
- Ensure the final output is valid JSON adhering to the specified structure.
- NEVER make up any information. If something is not present in the submission, indicate it as such.

## Response Template (strict - include start/end tags):
<reasoning>Step-by-step thought process with numbered points (8 steps max, <=20 words each)</reasoning>
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
- NEVER make up any information. If something is not present in the context, indicate it as such.

## Assignment PDF Content:
{pdf_content}

## Response Template (strict - include all tags):
<reasoning>Step-by-step thought process with numbered points (8 steps max, <=20 words each)</reasoning>
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
- NEVER make up any information. If something is not present in the context, indicate it as such.

## Response Template (strict - include all tags):
<reasoning>Step-by-step thought process with numbered points (8 steps max, <=20 words each)</reasoning>
<result>task_json</result>
"""


EVALUATE_PROMPT = """
# Student Submission Evaluation Prompt
You are an expert at evaluating student submissions for laboratory assignments.
Your task is to evaluate the student's submission based on the provided assignment specification and the student's work analysis.

## Task Specification:
{task_description}

## Student Task Submission:
{student_submission}

You must structure your evaluation in the following JSON format:
{{
    "completeness": "<complete|incomplete|partial>",
    "mistakes": ["<List of mistakes or omissions>"],
    "grade": "<0-100>",
}}
## Guidelines:
- Analyze given task specification and user submission for the specific task.
- Analyze visual references provided in the submission.
- Check if visual references contain task/variant requirements.
- Compare student's submission against the task and variant-specific requirements.
- Identify mistakes or omissions in the submission.
- Determine the completeness of the submission for the task.
- Assign a grade based on the quality of the submission.
- Ensure the final output is valid JSON adhering to the specified structure.
- NEVER make up any information. If something is not present in the context, indicate it as such.

## Response Template (strict - include start/end tags):
<reasoning>Step-by-step thought process with numbered points (8 steps max, <=20 words each)</reasoning>
<result>evaluation_json</result>

## Student Visual References:
"""
