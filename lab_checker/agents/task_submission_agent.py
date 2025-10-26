"""Task submission agent for comprehensive analysis of student work for specific tasks."""

import json
from typing import Any, Dict, List

from lab_checker.message_utils import prepare_message_with_visuals

from ..chains import chain_json_with_thinking
from ..doc_parsing import parse_pdf
from ..llm import OpenAIModel


class TaskSubmissionAgent:
    """
    Agent responsible for comprehensive analysis of student submissions for specific tasks.
    This agent combines task requirements with student implementation to provide
    detailed analysis of what was submitted.
    """

    def __init__(self, llm: OpenAIModel):
        self.llm = llm

    def analyze_task_submission(
        self,
        submission_pdf: str,
        task: Dict[str, Any],
        assignment_context: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        """
        Analyze student submission for a specific task.

        Args:
            submission_pdf: Path to submission PDF file
            task: Task specification from assignment
            assignment_context: Additional assignment context if available

        Returns:
            Dictionary containing comprehensive task submission analysis
        """
        # Parse the submission PDF
        submission_content = parse_pdf(submission_pdf)

        # Prepare messages for the LLM
        messages = self._prepare_submission_messages(
            submission_content, task, assignment_context
        )

        # Get analysis from LLM
        response = chain_json_with_thinking(self.llm).invoke("", messages=messages)

        return response

    def _prepare_submission_messages(
        self,
        submission_content: Dict[str, Any],
        task: Dict[str, Any],
        assignment_context: Dict[str, Any] = None,
    ) -> List[Dict[str, Any]]:
        """
        Prepare messages for LLM analysis including visual content.

        Args:
            submission_content: Parsed submission content
            task: Task specification
            assignment_context: Additional assignment context

        Returns:
            List of formatted messages for LLM
        """
        # Prepare visual content
        message_content = prepare_message_with_visuals(
            submission_content["text"],
            submission_content.get("visuals", {}),
        )

        # Prepare system prompt with task and context
        system_prompt = self.TASK_SUBMISSION_ANALYSIS_PROMPT.format(
            task_description=json.dumps(task, ensure_ascii=False),
            assignment_context=(
                json.dumps(assignment_context, ensure_ascii=False)
                if assignment_context
                else "No additional context"
            ),
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

    def save_analysis(
        self, analysis_data: Dict[str, Any], task_index: int, output_dir: str = "."
    ) -> None:
        """
        Save task submission analysis to a JSON file.

        Args:
            analysis_data: Analysis data from analyze_task_submission
            task_index: Index of the task (for filename generation)
            output_dir: Directory where to save the analysis JSON file
        """
        output_path = f"{output_dir}/task_{task_index}_submission.json"
        with open(output_path, "w") as f:
            f.write(analysis_data.model_dump_json(indent=2, ensure_ascii=False))

    @property
    def TASK_SUBMISSION_ANALYSIS_PROMPT(self) -> str:
        """Prompt template for comprehensive task submission analysis."""
        return """
# Task Submission Analysis Prompt

You are an expert at analyzing student laboratory submissions for specific tasks.
Your role is to comprehensively examine what a student has submitted for a particular task
and provide detailed analysis of their implementation, approach, and completeness.

## Task Specification:
{task_description}

## Assignment Context:
{assignment_context}

## Analysis Guidelines:

### 1. Task Understanding
- Analyze the task requirements and deliverables
- Understand what the student was supposed to implement
- Identify any variant-specific requirements

### 2. Submission Analysis
- Extract what the student actually implemented
- Identify code structures, algorithms, and approaches used
- Analyze documentation and comments
- Review any visual elements (diagrams, screenshots, etc.)

### 3. Implementation Assessment
- Compare implementation against requirements
- Identify completed vs missing elements
- Note any extra features or creative solutions
- Assess code quality and organization

You must structure your response in the following JSON format:
{{
    "task_understanding": {{
        "task_name": "<Task name/identifier>",
        "requirements_summary": "<Summary of what was required>",
        "variant_requirements": "<Specific variant requirements if any>",
        "expected_deliverables": ["<List of expected outputs>"]
    }},
    "implementation_analysis": {{
        "status": "<not_attempted|partial|complete>",
        "implemented_features": ["<List of implemented features>"],
        "implementation_approach": "<Description of student's approach>",
        "code_excerpts": ["<Relevant code snippets>"],
        "algorithms_used": ["<Algorithms or techniques identified>"],
        "data_structures": ["<Data structures used>"]
    }},
    "quality_assessment": {{
        "code_organization": "<Assessment of code structure>",
        "naming_conventions": "<Assessment of variable/function names>",
        "documentation_level": "<poor|fair|good|excellent>",
        "error_handling": "<Description of error handling if present>",
        "testing_evidence": "<Evidence of testing if any>"
    }},
    "visual_elements": [
        {{
            "type": "<diagram|screenshot|chart|etc>",
            "description": "<What the visual shows>",
            "relevance": "<How it relates to the task>",
            "tag": "<<Visual reference tag>>"
        }}
    ],
    "completeness_analysis": {{
        "completed_requirements": ["<Requirements that were met>"],
        "missing_elements": ["<Requirements not addressed>"],
        "extra_features": ["<Additional features beyond requirements>"],
        "deviations": ["<Any deviations from specified approach>"]
    }},
    "observations": ["<Additional notes about the submission>"]
}}

## Guidelines:
- Be thorough in analyzing both code and documentation
- Pay attention to visual elements and their relevance to the task
- Assess implementation quality objectively
- Note both strengths and weaknesses in the submission
- Identify creative solutions or alternative approaches
- Be precise about what is present vs missing
- NEVER make up information not present in the submission

## Response Template (strict - include all tags):
<reasoning>Step-by-step analysis process with numbered points (10 steps max, <=25 words each)</reasoning>
<result>analysis_json</result>
"""
