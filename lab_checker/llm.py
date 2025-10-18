import base64
import os
from io import BytesIO
from typing import Any, Iterator, List, Optional, Type

from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.language_models import LLM
from langchain_core.outputs import GenerationChunk
from openai import OpenAI
from PIL import Image
from pydantic import Field


def image_to_base64(image):
    buffered = BytesIO()
    image.save(buffered, format="JPEG")
    img_str = base64.b64encode(buffered.getvalue())
    return img_str.decode()


def read_image_as_base64(image_path: str) -> str:
    """
    Read an image file and convert it to base64 string.

    Args:
        image_path: Path to the image file

    Returns:
        Base64 encoded string of the image
    """
    with Image.open(image_path) as image:
        return image_to_base64(image)


class OpenAIModel(LLM):
    """LangChain-compatible wrapper for OpenAI's gpt-5-nano model."""

    client: OpenAI = Field(default=None, exclude=True)
    model: str = "gpt-5-nano"
    api_key: Optional[str] = None
    verbosity: str = "medium"
    reasoning_effort: str = "minimal"

    def __init__(
        self,
        model: str = "gpt-5-nano",
        api_key: Optional[str] = None,
        verbosity: str = "medium",
        reasoning_effort: str = "minimal",
    ):
        super().__init__()
        self.model = model
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError(
                "Missing OpenAI API key. Set OPENAI_API_KEY or pass api_key."
            )
        self.client = OpenAI(api_key=self.api_key)
        self.verbosity = verbosity
        self.reasoning_effort = reasoning_effort

    @property
    def _llm_type(self) -> str:
        return self.model

    def _prepare_messages(
        self, prompt: str, image: Optional[Image.Image] = None
    ) -> List[dict]:
        if image is not None:
            if isinstance(image, str):
                image = read_image_as_base64(image)
            else:
                image = image_to_base64(image)
            messages = [
                {
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": prompt},
                        {
                            "type": "input_image",
                            "image_url": f"data:image/jpeg;base64,{image}",
                        },
                    ],
                },
            ]
        else:
            messages = [{"role": "user", "content": prompt}]
        return messages

    def _call(
        self,
        prompt: Optional[str] = None,
        stop: Optional[List[str]] = None,
        image: Optional[Image.Image] = None,
        text_format: Optional[Type] = None,
        messages: Optional[List[dict]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> str:
        """Send prompt to GPT-5 Nano via OpenAI Responses API."""
        if messages is None:
            messages = self._prepare_messages(prompt, image)
        if text_format is not None:
            response = self.client.responses.parse(
                model=self.model,
                input=messages,
                text={"verbosity": kwargs.pop("verbosity", self.verbosity)},
                reasoning={
                    "effort": kwargs.pop("reasoning_effort", self.reasoning_effort)
                },
                text_format=text_format,
                **kwargs,
            )
            output = response.output_parsed
        else:
            response = self.client.responses.create(
                model=self.model,
                input=messages,
                text={"verbosity": kwargs.pop("verbosity", self.verbosity)},
                reasoning={
                    "effort": kwargs.pop("reasoning_effort", self.reasoning_effort)
                },
                **kwargs,
            )
            output = response.output_text.strip()
            if stop:
                for s in stop:
                    output = output.split(s)[0]
        return output

    def _stream(
        self,
        prompt: str,
        stop: Optional[List[str]] = None,
        image: Optional[Image.Image] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        messages: Optional[List[dict]] = None,
        **kwargs: Any,
    ) -> Iterator[GenerationChunk]:
        """Stream responses from GPT-5 Nano via OpenAI Responses API."""
        if messages is None:
            messages = self._prepare_messages(prompt, image)
        stream = self.client.responses.create(
            model=self.model,
            input=messages,
            text={"verbosity": kwargs.pop("verbosity", self.verbosity)},
            reasoning={"effort": kwargs.pop("reasoning_effort", self.reasoning_effort)},
            stream=True,
            **kwargs,
        )

        for event in stream:
            if event.type == "response.created":
                pass
            elif event.type == "response.output_text.delta":
                text = event.delta
                yield GenerationChunk(text=text)

                if run_manager:
                    run_manager.on_llm_new_token(text)
            elif event.type == "response.completed":
                pass
            elif event.type == "error":
                pass

                # Check for stop sequences

    def process_pdf_pages_iteratively(
        self,
        pdf_path: str,
        system_prompt: str,
        page_prompt: str,
        start_page: int = 0,
        end_page: Optional[int] = None,
        accumulate_context: bool = True,
        context_summary_interval: Optional[int] = None,
        password: Optional[str] = None,
        dpi: int = 150,
    ) -> List[dict]:
        """
        Process a PDF iteratively, running LLM on each page image with accumulated context.

        Args:
            pdf_path: Path to the PDF file
            system_prompt: System prompt to set the LLM's behavior
            page_prompt: Template for processing each page. Use {page_num} and {context} placeholders
            start_page: Starting page number (0-indexed, default: 0)
            end_page: Ending page number (0-indexed, exclusive). None means all pages
            accumulate_context: Whether to accumulate context from previous pages (default: True)
            context_summary_interval: Optionally summarize context every N pages (default: None)
            password: Optional password for encrypted PDFs
            dpi: Resolution for page rendering (default: 150)

        Returns:
            List of dictionaries containing:
                - 'page': Page number (1-indexed)
                - 'response': LLM response for this page
                - 'accumulated_context': Context accumulated up to this page (if accumulate_context=True)

        Raises:
            FileNotFoundError: If the PDF file doesn't exist
            ValueError: If page range is invalid
        """
        from lab_checker.doc_parsing import load_pdf_pages_as_images

        # Load all pages as images
        page_images = load_pdf_pages_as_images(pdf_path, password=password, dpi=dpi)

        if not page_images:
            raise ValueError(f"No pages found in PDF: {pdf_path}")

        # Validate and adjust page range
        total_pages = len(page_images)
        if start_page < 0 or start_page >= total_pages:
            raise ValueError(
                f"Invalid start_page {start_page}. PDF has {total_pages} pages."
            )

        if end_page is None:
            end_page = total_pages
        elif end_page <= start_page or end_page > total_pages:
            raise ValueError(
                f"Invalid end_page {end_page}. Must be between {start_page + 1} and {total_pages}."
            )

        # Process pages
        results = []
        accumulated_context = ""

        for page_index in range(start_page, end_page):
            page_info = page_images[page_index]
            page_num = page_info["page"]
            page_image = page_info["image"]

            # Build the prompt for this page
            if "{page_num}" in page_prompt:
                current_prompt = page_prompt.replace("{page_num}", str(page_num))
            else:
                current_prompt = page_prompt

            if "{context}" in current_prompt:
                current_prompt = current_prompt.replace(
                    "{context}", accumulated_context or "No context yet."
                )

            # Add system prompt context if provided
            if system_prompt:
                current_prompt = f"{system_prompt}\n\n{current_prompt}"

            # Call LLM with page image
            response = self._call(
                prompt=current_prompt,
                image=page_image,
            )

            # Accumulate context from response
            if accumulate_context:
                accumulated_context += f"\n\n[Page {page_num}]: {response}"

            # Optionally summarize context periodically
            if (
                context_summary_interval
                and (page_index - start_page + 1) % context_summary_interval == 0
            ):
                summary_prompt = f"Summarize the following context in a concise manner:\n\n{accumulated_context}"
                accumulated_context = self._call(prompt=summary_prompt)

            result = {
                "page": page_num,
                "response": response,
                "accumulated_context": (
                    accumulated_context.copy() if accumulate_context else None
                ),
            }
            results.append(result)

        return results


if __name__ == "__main__":
    import requests

    model = OpenAIModel()

    prompt = "Describe the image in detail."

    image_url = "https://images.unsplash.com/photo-1503023345310-bd7c1de61c7d"
    image_data = requests.get(image_url).content
    image = Image.open(BytesIO(image_data))

    response = model.invoke(
        [{"role": "system", "content": "You are a helpful assistant."}]
        + [{"role": "user", "content": prompt}],
        image=image,
    )
    print("Response:", response)
