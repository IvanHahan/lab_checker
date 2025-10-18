from enum import Enum
from pathlib import Path

from ..doc_parsing import parse_pdf
from ..llm import OpenAIModel
from ..message_utils import (
    prepare_message_with_visuals,
    process_chunks_with_accumulated_context,
)


class ProcessingMode(Enum):
    """Enum for PDF processing modes."""

    PARSED = "parsed"  # Extract text and images, then process with accumulated context
    IMAGES = "images"  # Load PDF as page images and process iteratively


class AssignmentAgent:
    def __init__(
        self,
        llm: OpenAIModel,
        processing_mode: ProcessingMode = ProcessingMode.IMAGES,
    ):
        """
        Initialize the AssignmentAgent.

        Args:
            llm: OpenAI language model instance
            processing_mode: How to process PDFs (PARSED or IMAGES)
        """
        self.llm = llm
        self.processing_mode = processing_mode
        self.system_prompt = self._load_prompt()

    def _load_prompt(self) -> str:
        """Load the system prompt from the prompts directory."""
        prompt_path = Path(__file__).parent.parent / "prompts" / "assignment_agent.md"
        with open(prompt_path, "r", encoding="utf-8") as f:
            return f.read()

    def run(self, pdf: str) -> str:
        """
        Process an assignment PDF using the configured processing mode.

        Args:
            pdf: Path to the assignment PDF file

        Returns:
            Processed assignment information as a string (typically JSON)
        """
        if self.processing_mode == ProcessingMode.PARSED:
            return self._run_parsed(pdf)
        elif self.processing_mode == ProcessingMode.IMAGES:
            return self._run_images(pdf)
        else:
            raise ValueError(f"Unknown processing mode: {self.processing_mode}")

    def _run_parsed(self, pdf: str) -> str:
        """
        Process PDF using text and image parsing (original method).

        Args:
            pdf: Path to the PDF file

        Returns:
            Processed assignment information
        """
        # Process the PDF to extract text and images
        parsed_content = parse_pdf(pdf)
        message_content = self._prepare_message(parsed_content)

        # Process chunks with accumulated context for long documents
        chunk_context_instruction = (
            "\n\n## Summary of Earlier Sections\n"
            "Based on the previous parts of the assignment document, "
            "the following tasks and information were already identified:\n"
            "{accumulated_output}\n\n"
            "Continue with the next section of the document, identifying additional tasks "
            "and extracting any new requirements not mentioned in earlier sections."
        )

        combine_instruction = (
            "\n\nYou have now reviewed the entire assignment document in sections. "
            "Provide the final, complete output that consolidates all tasks, "
            "requirements, and specifications from all sections. Ensure the output is "
            "well-organized with all tasks properly grouped and no duplicates."
        )

        response = process_chunks_with_accumulated_context(
            llm=self.llm,
            system_prompt=self.system_prompt,
            content_entries=message_content,
            max_chars=3000,
            chunk_context_instruction=chunk_context_instruction,
            combine_instruction=combine_instruction,
        )
        return response

    def _run_images(self, pdf: str) -> str:
        """
        Process PDF by loading pages as images and processing iteratively.

        This method loads each PDF page as an image and processes them sequentially
        with accumulated context from previous pages.

        Args:
            pdf: Path to the PDF file

        Returns:
            Processed assignment information
        """
        page_prompt = (
            "You are processing page {page_num} of an assignment specification document.\n\n"
            "Previous context from earlier pages:\n{context}\n\n"
            "Analyze this page and identify all tasks, requirements, and specifications. "
            "Focus on new information not covered in the previous sections. "
            "Extract key points in a structured format."
        )

        # Process all pages iteratively with accumulated context
        results = self.llm.process_pdf_pages_iteratively(
            pdf_path=pdf,
            system_prompt=self.system_prompt,
            page_prompt=page_prompt,
            accumulate_context=True,
            context_summary_interval=5,  # Summarize every 5 pages to keep context manageable
        )

        # Combine results from all pages
        combined_response = self._combine_page_results(results)
        return combined_response

    def _combine_page_results(self, results: list) -> str:
        """
        Combine results from iterative page processing into final output.

        Args:
            results: List of page processing results from process_pdf_pages_iteratively

        Returns:
            Combined final output
        """
        all_responses = "\n\n".join(
            [f"[Page {r['page']}]: {r['response']}" for r in results]
        )

        # Use LLM to consolidate all page results into final structured output
        consolidation_prompt = (
            f"You have reviewed an assignment specification document page by page. "
            f"Here are the findings from each page:\n\n{all_responses}\n\n"
            f"Now provide the final, consolidated output that combines all findings. "
            f"Organize by task/requirement, eliminate duplicates, and ensure completeness. "
            f"Maintain the same output structure as your analysis."
        )

        final_output = self.llm._call(prompt=consolidation_prompt)
        return final_output

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
