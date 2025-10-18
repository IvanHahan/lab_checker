"""
Utility functions for preparing messages with visual content for LLM agents.
"""

import base64
import re
from io import BytesIO
from typing import Any, Dict, List

from loguru import logger


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
    logger.debug(
        f"Preparing message with visuals. Text length: {len(text)}, visuals count: {len(visuals)}"
    )

    if not visuals:
        logger.debug("No visuals provided, returning text-only content entry")
        return [{"type": "input_text", "text": text}]

    # Create a mapping from visual tokens to visual data
    visual_map = {}
    for visual in visuals:
        global_idx = visual.get("global_index")
        visual_type = visual.get("type", "image").upper()
        if global_idx:
            token = f"<<{visual_type}_{global_idx}>>"
            visual_map[token] = visual
            logger.debug(f"Mapped visual token: {token}")

    # Pattern to match visual tokens: <<IMAGE_N>> or <<DIAGRAM_N>>
    token_pattern = r"<<(IMAGE|DIAGRAM)_(\d+)>>"

    # Split text by visual tokens while keeping the tokens
    parts = re.split(f"({token_pattern})", text)
    logger.debug(f"Split text into {len(parts)} parts")

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
                logger.debug(
                    f"Processed visual token {part}, base64 length: {len(img_base64)}"
                )

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
                logger.debug(f"Added text content, length: {len(text_content)}")
                content_entries.append({"type": "input_text", "text": text_content})

    logger.info(f"Message preparation complete. Total entries: {len(content_entries)}")
    return (
        content_entries if content_entries else [{"type": "input_text", "text": text}]
    )


def chunkify_message(
    content_entries: List[Dict[str, Any]], max_chars: int = 4000
) -> List[List[Dict[str, Any]]]:
    """
    Split message content entries into chunks by character count.

    Groups content entries into chunks without breaking words. Images are kept
    together with surrounding text. Text entries are split at word boundaries
    when they would exceed max_chars.

    Args:
        content_entries: List of content entries from prepare_message_with_visuals()
        max_chars: Maximum characters per chunk (default: 4000)

    Returns:
        List of chunks, where each chunk is a list of content entries
    """
    logger.debug(
        f"Starting message chunking. Entries: {len(content_entries)}, max_chars: {max_chars}"
    )

    if not content_entries:
        logger.warning("No content entries provided for chunking")
        return []

    chunks = []
    current_chunk = []
    current_char_count = 0

    for entry in content_entries:
        entry_type = entry.get("type")

        if entry_type == "input_image":
            # Images don't count toward char limit, just add them
            logger.debug("Adding image entry to current chunk")
            current_chunk.append(entry)
        elif entry_type == "input_text":
            text = entry.get("text", "")
            text_length = len(text)

            # If adding this text would exceed limit, finalize current chunk
            if current_char_count > 0 and current_char_count + text_length > max_chars:
                logger.debug(
                    f"Finalizing chunk with {len(current_chunk)} entries and {current_char_count} chars"
                )
                chunks.append(current_chunk)
                current_chunk = []
                current_char_count = 0

            # If single text entry exceeds limit, split it at word boundaries
            if text_length > max_chars:
                logger.debug(
                    f"Text entry exceeds max_chars ({text_length} > {max_chars}), splitting at word boundaries"
                )
                words = text.split()
                chunk_text = ""

                for word in words:
                    word_with_space = word if not chunk_text else " " + word
                    if len(chunk_text) + len(word_with_space) <= max_chars:
                        chunk_text += word_with_space
                    else:
                        # Save current chunk if it has content
                        if chunk_text:
                            if current_chunk:
                                logger.debug(
                                    f"Saving partial chunk with {len(current_chunk)} entries"
                                )
                                chunks.append(current_chunk)
                            logger.debug(
                                f"Creating new chunk from split text ({len(chunk_text)} chars)"
                            )
                            chunks.append([{"type": "input_text", "text": chunk_text}])
                        chunk_text = word
                        current_chunk = []
                        current_char_count = 0

                # Add remaining text
                if chunk_text:
                    logger.debug(
                        f"Adding remaining text chunk ({len(chunk_text)} chars)"
                    )
                    current_chunk.append({"type": "input_text", "text": chunk_text})
                    current_char_count = len(chunk_text)
            else:
                # Text fits, add to current chunk
                logger.debug(
                    f"Adding text entry to current chunk ({text_length} chars)"
                )
                current_chunk.append(entry)
                current_char_count += text_length

    # Add any remaining entries
    if current_chunk:
        logger.debug(
            f"Finalizing last chunk with {len(current_chunk)} entries and {current_char_count} chars"
        )
        chunks.append(current_chunk)

    logger.info(f"Chunking complete. Total chunks: {len(chunks)}")
    return chunks


def process_chunks_with_accumulated_context(
    llm,
    system_prompt: str,
    content_entries: List[Dict[str, Any]],
    max_chars: int = 4000,
    chunk_context_instruction: str = None,
    combine_instruction: str = None,
) -> str:
    """
    Process content chunks sequentially, accumulating outputs for context.

    For long contexts, split content into chunks and process each chunk with
    the LLM, passing previous results as context to the next chunk. This allows
    the LLM to build understanding incrementally without hitting token limits.

    Args:
        llm: OpenAIModel instance
        system_prompt: System prompt for the LLM
        content_entries: List of content entries from prepare_message_with_visuals()
        max_chars: Maximum characters per chunk (default: 4000)
        chunk_context_instruction: Template for including previous results as context.
                                  Should contain {accumulated_output} placeholder.
                                  If None, uses default instruction.
        combine_instruction: Instruction for combining final results.
                            If None, uses default instruction.

    Returns:
        Final aggregated output from all chunks
    """
    logger.info(
        f"Starting chunk processing with accumulated context. Content entries: {len(content_entries)}"
    )

    chunks = chunkify_message(content_entries, max_chars)

    # If only one chunk, process normally
    if len(chunks) <= 1:
        logger.info("Single chunk detected, processing normally without accumulation")
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": content_entries},
        ]
        result = llm._call(messages=messages, reasoning_effort="medium")
        logger.info("Single chunk processing complete")
        return result

    # Default instructions
    if chunk_context_instruction is None:
        chunk_context_instruction = (
            "\n\n## Previous Context from Earlier Chunks\n"
            "Based on analysis of earlier parts of the document:\n"
            "{accumulated_output}\n\n"
            "Now continue analyzing the next section of the document, "
            "building upon the findings above."
        )

    if combine_instruction is None:
        combine_instruction = (
            "\n\nYou have now reviewed the entire document in sections. "
            "Provide a final, comprehensive output that consolidates all "
            "findings from all sections into a single, cohesive result. "
            "Ensure no information is duplicated and all sections are properly integrated."
        )

    logger.info(f"Processing {len(chunks)} chunks with accumulated context")
    accumulated_output = None

    # Process each chunk
    for i, chunk in enumerate(chunks):
        logger.info(f"Processing chunk {i + 1}/{len(chunks)}")
        is_first_chunk = i == 0
        is_last_chunk = i == len(chunks) - 1

        # Build the user message for this chunk
        if accumulated_output is None:
            # First chunk - no accumulated context
            logger.debug("First chunk: no accumulated context to include")
            user_message = chunk
            current_system_prompt = system_prompt
        else:
            # Subsequent chunks - include previous output as context
            logger.debug(
                f"Adding accumulated context from previous chunk (length: {len(accumulated_output)})"
            )
            context_text = chunk_context_instruction.format(
                accumulated_output=accumulated_output
            )

            user_message = [
                {"type": "input_text", "text": context_text},
            ] + chunk

            # Update system prompt to indicate we're processing multiple chunks
            current_system_prompt = (
                system_prompt
                + "\n\n## Processing Instructions\n"
                + "You are processing a long document in multiple chunks. "
                + "For each chunk, build upon the previous analysis."
            )

        # Add final consolidation instruction for the last chunk
        if is_last_chunk:
            logger.debug("Last chunk: adding consolidation instruction")
            if isinstance(user_message, list):
                # Extract text content if it exists
                text_contents = [
                    entry.get("text", "")
                    for entry in user_message
                    if entry.get("type") == "input_text"
                ]
                combined_text = " ".join(text_contents) + combine_instruction
                # Replace the text in user_message
                user_message_list = [
                    entry for entry in user_message if entry.get("type") != "input_text"
                ]
                user_message_list.append({"type": "input_text", "text": combined_text})
                user_message = user_message_list
            else:
                user_message = [
                    {"type": "input_text", "text": user_message + combine_instruction}
                ]

        # Call the LLM
        logger.debug(
            f"Calling LLM for chunk {i + 1}, user message entries: {len(user_message) if isinstance(user_message, list) else 1}"
        )
        messages = [
            {"role": "system", "content": current_system_prompt},
            {"role": "user", "content": user_message},
        ]

        accumulated_output = llm._call(
            messages=messages,
            reasoning_effort="medium",
        )
        logger.debug(f"Chunk {i + 1} LLM response length: {len(accumulated_output)}")

    logger.info(
        f"Chunk processing complete. Final output length: {len(accumulated_output)}"
    )
    return accumulated_output
