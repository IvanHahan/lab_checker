import base64
import os
from io import BytesIO
from typing import Any, Iterator, List, Optional

from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.language_models import LLM
from langchain_core.outputs import GenerationChunk
from openai import OpenAI, Timeout
from PIL import Image
from pydantic import Field

LLM_MAP = {
    "qwen3_4b_thinking": {
        "base_url": "https://stereologic-vllm-qwen3-4b-instruct-2507.hf.space/v1",
        "model": "Qwen/Qwen3-4B-Instruct-2507",
    },
}

MODEL_URLS = {
    "qwenvl25_32b": "https://stereologic-vllm-qwen25-32b.hf.space/v1",
    "qwenvl25_72b": "https://stereologic-vllm-qwen25-72b.hf.space/v1",
    "internvl_14b": "https://stereologic-vllm-ogvl-internvl35-14b.hf.space/v1",
    "internvl_30b": "https://stereologic-vllm-ogvl-internvl3-5-30b-a3b.hf.space/v1",
    "orsta": "https://stereologic-vllm.hf.space/v1",
    "qwen3vl_8b": "https://stereologic-vllm-qwen3-vl-8b-instruct.hf.space/v1",
    "qwen3vl_4b": "https://stereologic-vllm-qwen3-vl-4b-instruct.hf.space/v1",
    "qwen3_4b": "https://stereologic-vllm-qwen3-4b-instruct-2507.hf.space/v1",
}


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
    model: str = None
    api_key: Optional[str] = None
    verbosity: str = "medium"
    reasoning_effort: str = "minimal"
    base_url: Optional[str] = None
    timeout_seconds: int = 60
    read_timeout_seconds: int = 600
    default_temperature: float = 0.0
    max_tokens: int = 512

    def __init__(
        self,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        verbosity: str = "medium",
        reasoning_effort: str = "minimal",
        timeout_seconds: int = 60,
        read_timeout_seconds: int = 600,
        **kwargs: Any,
    ):
        super().__init__()
        self.model = model
        self.base_url = base_url
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError(
                "Missing OpenAI API key. Set OPENAI_API_KEY or pass api_key."
            )
        self.verbosity = verbosity
        self.timeout_seconds = timeout_seconds
        self.read_timeout_seconds = read_timeout_seconds
        self.reasoning_effort = reasoning_effort
        self.client = self._create_client()
        if not self.model:
            self.model = self.client.models.list().data[0].id

    def _create_client(self) -> OpenAI:
        """Create and configure the OpenAI client."""
        client_kwargs = {
            "base_url": self.base_url,
            "timeout": Timeout(
                self.timeout_seconds,
                connect=self.timeout_seconds,
                read=self.read_timeout_seconds,
                write=self.timeout_seconds,
            ),
        }

        if self.api_key is not None:
            client_kwargs["default_headers"] = {
                "Authorization": f"Bearer {self.api_key}"
            }

        return OpenAI(**client_kwargs)

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
        image: Optional[Image.Image] = None,
        messages: Optional[List[dict]] = None,
        tools: Optional[List[Any]] = [],
        stop: Optional[List[str]] = None,
        **kwargs: Any,
    ) -> str:
        """Send prompt to GPT-5 Nano via OpenAI Responses API."""
        if messages is None:
            messages = self._prepare_messages(prompt, image)

        # kwargs["max_tokens"] = kwargs.get("max_tokens", self.max_tokens)
        # kwargs["temperature"] = kwargs.get("temperature", self.default_temperature)

        response = self.client.responses.create(
            model=self.model,
            input=messages,
            tools=tools,
            **kwargs,
        )

        content = response.output_text
        return content

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


if __name__ == "__main__":
    import requests

    model = OpenAIModel(
        base_url=MODEL_URLS["qwen3vl_4b"], api_key=os.getenv("HF_TOKEN")
    )

    prompt = "Describe the image in detail."

    image_url = "https://images.unsplash.com/photo-1503023345310-bd7c1de61c7d"
    image_data = requests.get(image_url).content
    image = Image.open(BytesIO(image_data))

    response = model.call(
        prompt=prompt,
        image=image,
    )
    print("Response:", response)
