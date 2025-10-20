from pathlib import Path
from typing import Any, Dict, Optional

from ..data_model import Assignment
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

    def _load_prompt(self) -> str:
        """Load the system prompt from the prompts directory."""
        prompt_path = Path(__file__).parent.parent / "prompts" / "work_agent.md"
        with open(prompt_path, "r", encoding="utf-8") as f:
            return f.read()

    def run(
        self,
        assignment: Assignment,
        submission_pdf: Optional[str] = None,
    ) -> Dict[str, Any]:
        doc_content = parse_pdf(submission_pdf)
