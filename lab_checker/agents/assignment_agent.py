from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING

from loguru import logger
from tqdm import tqdm

from ..doc_parsing import load_pdf_pages_as_images, parse_pdf
from ..image_utils import crop_image_to_content
from ..llm import OpenAIModel
from ..message_utils import (
    prepare_message_with_visuals,
    process_chunks_with_accumulated_context,
)

if TYPE_CHECKING:
    from PIL import Image


class ProcessingMode(Enum):
    """Enum for PDF processing modes."""

    PARSED = "parsed"  # Extract text and images, then process with accumulated context
    IMAGES = "images"  # Load PDF as page images and process iteratively


class AssignmentAgent:
    def __init__(
        self,
        llm: OpenAIModel,
        processing_mode: ProcessingMode = ProcessingMode.IMAGES,
        output_dir: str | None = None,
    ):
        """
        Initialize the AssignmentAgent.

        Args:
            llm: OpenAI language model instance
            processing_mode: How to process PDFs (PARSED or IMAGES)
            output_dir: Optional directory to save parsed pages and markdown files
        """
        self.llm = llm
        self.processing_mode = processing_mode
        self.system_prompt = self._load_prompt()
        self.image_parse_prompt = self._load_image_parse_prompt()
        self.output_dir = Path(output_dir) if output_dir else None

    def _load_prompt(self) -> str:
        """Load the system prompt from the prompts directory."""
        prompt_path = Path(__file__).parent.parent / "prompts" / "assignment_agent.md"
        with open(prompt_path, "r", encoding="utf-8") as f:
            return f.read()

    def _load_image_parse_prompt(self) -> str:
        """Load the image parsing prompt from the prompts directory."""
        prompt_path = (
            Path(__file__).parent.parent / "prompts" / "pdf_image_to_markdown.md"
        )
        with open(prompt_path, "r", encoding="utf-8") as f:
            return f.read()

    def _setup_output_directory(self, pdf_path: str) -> Path:
        """
        Create output directory structure for saving parsed pages.

        Args:
            pdf_path: Path to the input PDF file

        Returns:
            Path to the output directory
        """
        if not self.output_dir:
            return None

        # Create directory structure: output_dir/pdf_name/pages/
        pdf_name = Path(pdf_path).stem
        pages_dir = self.output_dir / pdf_name / "pages"
        pages_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"Created output directory: {pages_dir}")
        return pages_dir

    def _save_page(
        self,
        page_num: int,
        cropped_image: "Image.Image",
        markdown_content: str,
        output_dir: Path,
    ) -> None:
        """
        Save a parsed page with its image and markdown content.

        Args:
            page_num: Page number (1-indexed)
            cropped_image: Cropped PIL Image object
            markdown_content: Parsed markdown content
            output_dir: Directory to save files to
        """
        if not output_dir:
            return

        # Save image
        image_filename = f"page_{page_num:03d}.png"
        image_path = output_dir / image_filename
        cropped_image.save(image_path)

        # Save markdown
        md_filename = f"page_{page_num:03d}.md"
        md_path = output_dir / md_filename
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(markdown_content)

        logger.debug(f"Saved page {page_num}: {image_path} and {md_path}")

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
        # Setup output directory if specified
        output_dir = self._setup_output_directory(pdf)

        pdf_images = load_pdf_pages_as_images(pdf)[10:]
        parsed_images = []
        for i, page in enumerate(tqdm(pdf_images, desc="Processing PDF pages"), 1):
            # Crop image to content
            cropped_image = crop_image_to_content(page["image"])

            response = self.llm.invoke(
                self.image_parse_prompt,
                image=cropped_image,
            )
            parsed_images.append(response)

            # Save page if output directory is set
            if output_dir:
                self._save_page(i, cropped_image, response, output_dir)

        doc_content = "\n\n".join(
            [f"[Page {i+1}]: {r}" for i, r in enumerate(parsed_images)]
        )
        logger.info("Processed all PDF pages into content.")
        response = self.llm.invoke(
            self.system_prompt + "\n\nPDF Content:\n" + doc_content,
        )
        return response

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
