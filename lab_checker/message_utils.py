"""
Utility functions for preparing messages with visual content for LLM agents.
"""

import base64
import re
from io import BytesIO
from typing import Any, Dict, List


def prepare_message_with_visuals(
    text: str, visuals: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """
    Convert text with visual tokens into message format with images.

    Splits text by visual tokens (<<IMAGE_N>>, <<DIAGRAM_N>>) and inserts
    the corresponding images at those positions.

    Args:
        text: Text with visual tokens
        visuals: List of visual elements from parse_pdf()

    Returns:
        List of content entries for OpenAI API with alternating text and image_url entries
    """
    if not visuals:
        return [{"type": "input_text", "text": text}]

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
        elif part and not re.match(r"^\(IMAGE|DIAGRAM\)$", part) and not part.isdigit():
            # This is text content (not the captured groups from regex)
            text_content = part.strip()
            if text_content:
                content_entries.append({"type": "input_text", "text": text_content})

    return (
        content_entries if content_entries else [{"type": "input_text", "text": text}]
    )
