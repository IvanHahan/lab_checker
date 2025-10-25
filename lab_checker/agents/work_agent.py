from typing import Any, Dict, Optional

from ..chains import chain_json_with_thinking
from ..data_model import Assignment, Task
from ..data_model.work import SubmissionMetadata, TaskAnswer
from ..doc_parsing import parse_pdf
from ..llm import OpenAIModel
from ..utils import load_prompt
from .image_agent import ImageAgent


class WorkAgent:
    """
    Agent responsible for analyzing student submissions and extracting
    what the student implemented for each task in the assignment.
    """

    def __init__(self, llm: OpenAIModel):
        self.llm = llm
        self.metadata_prompt = load_prompt("submission_metadata_agent")
        self.single_task_prompt = load_prompt("single_task_agent")
        self.parse_visual_prompt = load_prompt("parse_visual")
        self.doc_content = None

    def run(
        self,
        assignment: Assignment,
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
        self.doc_content = parse_pdf(submission_pdf)
        image_agent = ImageAgent(self.llm)
        for visual_tag, image in self.doc_content.get("visuals", {}).items():
            response = image_agent.run(image["image"])
            self.doc_content["visuals"][visual_tag] = response

        # Analyze each task
        task_analyses = []
        for task in assignment.tasks:
            analysis = self._parse_single_task(task)
            task_analyses.append(analysis)

        # Extract submission metadata first
        metadata = self._parse_submission_metadata()

        return {
            "metadata": metadata.model_dump(),
            "task_analyses": [analysis.model_dump() for analysis in task_analyses],
        }

    def _parse_submission_metadata(self) -> SubmissionMetadata:
        """
        Extract submission metadata from student submission.

        Returns:
            SubmissionMetadata with student info
        """
        response = self.llm.client.responses.parse(
            model=self.llm.model,
            input=[
                {
                    "role": "system",
                    "content": self.metadata_prompt,
                },
                {
                    "role": "user",
                    "content": "SUBMISSION CONTENT:\n"
                    + self.doc_content.get("text", ""),
                },
            ],
            text_format=SubmissionMetadata,
        )
        return response

    def _parse_single_task(self, task: Task) -> TaskAnswer:
        """
        Analyze a single task from the submission.

        Args:
            task: Task specification from assignment

        Returns:
            TaskAnswer with task-specific analysis
        """
        # Format task specification

        # Fill the single task prompt with context
        filled_prompt = self.single_task_prompt.format(
            TASK_ID=f"Task ID: {task.id}",
            TASK_TITLE=f"Task Title: {task.title}",
            TASK_DESCRIPTION=f"Description: {task.description}",
            TASK_REQUIREMENTS=f"Requirements: {', '.join(task.requirements)}",
            TASK_DELIVERABLES=f"Deliverables: {', '.join(task.deliverables)}",
            SUBMISSION_CONTENT=self.doc_content.get("text", ""),
        )

        response = chain_json_with_thinking(
            self.llm,
        ).invoke(
            filled_prompt,
            tools=[
                {
                    "type": "function",
                    "name": "describe_image",
                    "description": "Describe an image given its tag.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "image_tag": {
                                "type": "string",
                                "description": "The tag or identifier of the image to describe.",
                            },
                        },
                    },
                }
            ],
        )
        return response

    def describe_image(self, image_tag: str) -> str:
        """
        Tool function to describe an image given its tag.

        Args:
            image_tag: The tag or identifier of the image to describe.

        Returns:
            A textual description of the image with type identification and structured parsing.
        """
        image = self.doc_content["visuals"].get(image_tag)
        return self.llm._call(prompt=self.parse_visual_prompt, image=image)
