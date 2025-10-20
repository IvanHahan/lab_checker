import asyncio
from pathlib import Path
from typing import Any, Dict, Optional

from agents import Agent, Runner, function_tool

from ..data_model import Assignment, StudentSubmission
from ..doc_parsing import parse_pdf
from ..llm import OpenAIModel


class WorkAgent:
    """
    Agent responsible for analyzing student submissions and extracting
    what the student implemented for each task in the assignment.
    """

    def __init__(self, llm: OpenAIModel):
        self.llm = llm
        self.system_prompt = self._load_prompt()
        self.parse_visual_prompt = self._load_parse_visual_prompt()

    def _load_prompt(self) -> str:
        """Load the system prompt from the prompts directory."""
        prompt_path = Path(__file__).parent.parent / "prompts" / "work_agent.md"
        with open(prompt_path, "r", encoding="utf-8") as f:
            return f.read()

    def _load_parse_visual_prompt(self) -> str:
        """Load the parse visual prompt from the prompts directory."""
        prompt_path = Path(__file__).parent.parent / "prompts" / "parse_visual.md"
        with open(prompt_path, "r", encoding="utf-8") as f:
            return f.read()

    def run(
        self,
        assignment: Assignment,
        submission_pdf: Optional[str] = None,
    ) -> Dict[str, Any]:
        self.doc_content = parse_pdf(submission_pdf)
        asyncio.set_event_loop(asyncio.new_event_loop())
        for task in assignment.tasks:
            work_subagent = Agent(
                "Student Work Agent",
                handoff_description="Analyze the student's work and provide feedback.",
                tools=[self._describe_image_tool],
                model="gpt-5-nano",
                output_type=StudentSubmission,
            )
            response = Runner.run_sync(
                work_subagent,
                input=self.system_prompt
                + "\n\nPDF CONTENT:\n"
                + self.doc_content.get("text", ""),
            )

    @property
    def _describe_image_tool(self):
        """Create a function_tool wrapper for describe_image without self in schema."""

        @function_tool
        def describe_image(image_tag: str) -> str:
            """
            Tool function to describe an image given its tag.

            Args:
                image_tag: The tag or identifier of the image to describe.

            Returns:
                A textual description of the image with type identification and structured parsing.
            """
            image = self.doc_content["visuals"].get(image_tag)
            return self.llm._call(prompt=self.parse_visual_prompt, image=image)

        return describe_image
