import base64
import re
from io import BytesIO
from pathlib import Path
from typing import Optional

from ..doc_parsing import parse_pdf
from ..rlm import RecursiveLanguageModel


class AssignmentAgent:
    def __init__(self, llm, rlm: Optional[RecursiveLanguageModel] = None):
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

        # Create a mapping from visual tokens to visual data
        visual_map = {}
        for visual in visuals:
            global_idx = visual.get("global_index")
            visual_type = visual.get("type", "image").upper()
            if global_idx:
                token = f"<<{visual_type}_{global_idx}>>"
                visual_map[token] = visual

        # Pattern to match visual tokens: <<IMAGE_N>> or <<DIAGRAM_N>>
        token_pattern = r"<<(IMAGE|DIAGRAM)_(\d+)>>"

        # Split text by visual tokens while keeping the tokens
        parts = re.split(f"({token_pattern})", text)

        content_entries = []

        for part in parts:
            # Check if this part is a visual token
            match = re.match(token_pattern, part)

            if match:
                # This is a visual token - add the corresponding image
                visual = visual_map.get(part)
                if visual and "image" in visual:
                    # Convert PIL Image to base64
                    pil_image = visual["image"]
                    buffered = BytesIO()
                    pil_image.save(buffered, format="PNG")
                    img_base64 = base64.b64encode(buffered.getvalue()).decode("utf-8")

                    content_entries.append(
                        {
                            "type": "input_image",
                            "image_url": f"data:image/png;base64,{img_base64}",
                        }
                    )
            elif (
                part
                and not re.match(r"^\(IMAGE|DIAGRAM\)$", part)
                and not part.isdigit()
            ):
                # This is text content (not the captured groups from regex)
                text_content = part.strip()
                if text_content:
                    content_entries.append({"type": "input_text", "text": text_content})

        return content_entries

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
