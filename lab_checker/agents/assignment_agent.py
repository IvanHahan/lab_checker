from pathlib import Path
from typing import Optional

from ..doc_parsing import parse_pdf
from ..llm import OpenAIModel
from ..message_utils import prepare_message_with_visuals
from ..rlm import RecursiveLanguageModel


class AssignmentAgent:
    def __init__(self, llm: OpenAIModel, rlm: Optional[RecursiveLanguageModel] = None):
        self.llm = llm
        self.rlm = rlm or RecursiveLanguageModel(llm)
        self.system_prompt = self._load_prompt()

    def _load_prompt(self) -> str:
        """Load the system prompt from the prompts directory."""
        prompt_path = Path(__file__).parent.parent / "prompts" / "assignment_agent.md"
        with open(prompt_path, "r", encoding="utf-8") as f:
            return f.read()

    def run(self, pdf: str):
        # Process the PDF to extract text and images
        parsed_content = parse_pdf(pdf)
        message_content = self._prepare_message(parsed_content)
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": message_content},
        ]
        response = self.llm._call(
            messages=messages,
            reasoning_effort="medium",
        )
        return response

    def _prepare_message(self, doc: dict) -> list:
        """
        Convert parsed PDF content into OpenAI message format.

        Splits text by visual tokens (<<IMAGE_N>>, <<DIAGRAM_N>>) and inserts
        the corresponding images at those positions.

        Args:
            doc: Dictionary with 'text' and 'visuals' keys from parse_pdf()

        Returns:
            List of content entries for OpenAI API with alternating text and image_url entries
        """
        text = doc.get("text", "")
        visuals = doc.get("visuals", [])

        if not text:
            return []

        return prepare_message_with_visuals(text, visuals)

    def _extract_metadata(self, doc: dict) -> dict:
        visuals = doc.get("visuals", doc.get("images", []))
        visual_meta = []
        for visual in visuals:
            if not isinstance(visual, dict):
                continue
            visual_meta.append(
                {
                    "global_index": visual.get("global_index"),
                    "type": visual.get("type"),
                    "page": visual.get("page"),
                    "description": visual.get("description"),
                }
            )

        return {
            "page_count": doc.get("page_count"),
            "visual_tokens": visual_meta,
        }
