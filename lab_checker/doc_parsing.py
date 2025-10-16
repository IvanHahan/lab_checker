import os
from typing import Dict, List, Optional, Tuple

import pdfplumber

# ============================================================================
# Constants
# ============================================================================

DIAGRAM_DETECTION_THRESHOLD = 3  # Minimum shapes to consider as diagram
DIAGRAM_CLUSTERING_DISTANCE = 50  # Vertical distance for grouping shapes
DIAGRAM_PADDING = 10  # Padding around diagram bbox
DIAGRAM_RESOLUTION = 150  # Resolution for rendering diagrams


# ============================================================================
# Basic PDF Reading Functions
# ============================================================================


def read_pdf(file_path: str, password: Optional[str] = None) -> str:
    """
    Read a PDF file and extract all text content using pdfplumber.

    Args:
        file_path: Path to the PDF file
        password: Optional password if the PDF is encrypted

    Returns:
        Extracted text from all pages of the PDF

    Raises:
        FileNotFoundError: If the PDF file doesn't exist
    """
    text_content = []

    with pdfplumber.open(file_path, password=password) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                text_content.append(text)

    return "\n".join(text_content)


def read_pdf_page(file_path: str, page_num: int, password: Optional[str] = None) -> str:
    """
    Read a specific page from a PDF file using pdfplumber.

    Args:
        file_path: Path to the PDF file
        page_num: Page number to read (0-indexed)
        password: Optional password if the PDF is encrypted

    Returns:
        Extracted text from the specified page

    Raises:
        FileNotFoundError: If the PDF file doesn't exist
        IndexError: If the page number is out of range
    """
    with pdfplumber.open(file_path, password=password) as pdf:
        if page_num >= len(pdf.pages) or page_num < 0:
            raise IndexError(
                f"Page {page_num} is out of range. PDF has {len(pdf.pages)} pages."
            )

        page = pdf.pages[page_num]
        return page.extract_text() or ""


def extract_images_from_pdf(
    file_path: str, password: Optional[str] = None, output_folder: Optional[str] = None
) -> List[Dict]:
    """
    Extract all images from a PDF file and optionally save them.

    Args:
        file_path: Path to the PDF file
        password: Optional password if the PDF is encrypted
        output_folder: Optional folder to save extracted images

    Returns:
        List of dictionaries containing:
            - 'image': PIL Image object
            - 'page': Page number (1-indexed)
            - 'index': Image index on the page (1-indexed)
            - 'bbox': Bounding box coordinates (x0, top, x1, bottom)

    Raises:
        FileNotFoundError: If the PDF file doesn't exist
    """
    images = []

    with pdfplumber.open(file_path, password=password) as pdf:
        for page_num, page in enumerate(pdf.pages):
            for img_index, img in enumerate(page.images):
                # Extract image using pdfplumber
                image_bbox = (img["x0"], img["top"], img["x1"], img["bottom"])
                cropped_page = page.crop(image_bbox)
                pil_image = cropped_page.to_image().original

                image_info = {
                    "image": pil_image,
                    "page": page_num + 1,
                    "index": img_index + 1,
                    "bbox": image_bbox,
                }
                images.append(image_info)

                if output_folder:
                    os.makedirs(output_folder, exist_ok=True)
                    img_path = f"{output_folder}/page{page_num+1}_img{img_index+1}.png"
                    pil_image.save(img_path)

    return images


# ============================================================================
# Image Extraction Functions
# ============================================================================


def _extract_embedded_images(page, page_num: int) -> List[Tuple[float, Dict]]:
    """
    Extract embedded images from a PDF page.

    Args:
        page: pdfplumber page object
        page_num: Page number (0-indexed)

    Returns:
        List of tuples (y_position, visual_info)
    """
    images = []

    for img_index, img in enumerate(page.images):
        image_bbox = (img["x0"], img["top"], img["x1"], img["bottom"])
        cropped_page = page.crop(image_bbox)
        pil_image = cropped_page.to_image().original

        visual_info = {
            "type": "image",
            "image": pil_image,
            "page": page_num + 1,
            "index": img_index + 1,
            "bbox": image_bbox,
            "y_position": img["top"],
        }
        images.append((img["top"], visual_info))

    return images


def _extract_vector_shapes(page) -> List[Dict]:
    """
    Extract vector graphics elements (curves and rectangles) from a page.

    Args:
        page: pdfplumber page object

    Returns:
        List of shape dictionaries with type, bbox, and y position
    """
    curves = page.curves if hasattr(page, "curves") and page.curves else []
    rects = page.rects if hasattr(page, "rects") and page.rects else []

    all_shapes = []

    for curve in curves:
        all_shapes.append(
            {
                "type": "curve",
                "bbox": (
                    curve.get("x0", 0),
                    curve.get("top", 0),
                    curve.get("x1", 0),
                    curve.get("bottom", 0),
                ),
                "y": curve.get("top", 0),
            }
        )

    for rect in rects:
        all_shapes.append(
            {
                "type": "rect",
                "bbox": (
                    rect.get("x0", 0),
                    rect.get("top", 0),
                    rect.get("x1", 0),
                    rect.get("bottom", 0),
                ),
                "y": rect.get("top", 0),
            }
        )

    return all_shapes


def _cluster_shapes_by_proximity(shapes: List[Dict]) -> List[List[Dict]]:
    """
    Group shapes that are close together vertically to identify diagrams.

    Args:
        shapes: List of shape dictionaries

    Returns:
        List of shape clusters (each cluster is a list of shapes)
    """
    if not shapes:
        return []

    # Sort by vertical position
    sorted_shapes = sorted(shapes, key=lambda x: x["y"])

    clusters = []
    current_cluster = [sorted_shapes[0]]

    for shape in sorted_shapes[1:]:
        if abs(shape["y"] - current_cluster[-1]["y"]) < DIAGRAM_CLUSTERING_DISTANCE:
            current_cluster.append(shape)
        else:
            if len(current_cluster) >= DIAGRAM_DETECTION_THRESHOLD:
                clusters.append(current_cluster)
            current_cluster = [shape]

    # Don't forget the last cluster
    if len(current_cluster) >= DIAGRAM_DETECTION_THRESHOLD:
        clusters.append(current_cluster)

    return clusters


def _calculate_cluster_bbox(
    cluster: List[Dict], page_width: float, page_height: float
) -> Tuple[float, float, float, float]:
    """
    Calculate the bounding box for a cluster of shapes.

    Args:
        cluster: List of shape dictionaries
        page_width: Width of the page
        page_height: Height of the page

    Returns:
        Tuple of (x0, top, x1, bottom) with padding applied
    """
    min_x = min(s["bbox"][0] for s in cluster)
    min_y = min(s["bbox"][1] for s in cluster)
    max_x = max(s["bbox"][2] for s in cluster)
    max_y = max(s["bbox"][3] for s in cluster)

    # Add padding and ensure within page bounds
    bbox = (
        max(0, min_x - DIAGRAM_PADDING),
        max(0, min_y - DIAGRAM_PADDING),
        min(page_width, max_x + DIAGRAM_PADDING),
        min(page_height, max_y + DIAGRAM_PADDING),
    )

    return bbox


def _extract_diagram_from_cluster(
    page, cluster: List[Dict], cluster_idx: int, page_num: int
) -> Optional[Tuple[float, Dict]]:
    """
    Extract a diagram image from a cluster of shapes.

    Args:
        page: pdfplumber page object
        cluster: List of shape dictionaries
        cluster_idx: Index of this cluster (0-indexed)
        page_num: Page number (0-indexed)

    Returns:
        Tuple of (y_position, visual_info) or None if extraction fails
    """
    bbox = _calculate_cluster_bbox(cluster, page.width, page.height)
    min_y = bbox[1]

    try:
        cropped_page = page.crop(bbox)
        diagram_image = cropped_page.to_image(resolution=DIAGRAM_RESOLUTION).original

        visual_info = {
            "type": "diagram",
            "image": diagram_image,
            "page": page_num + 1,
            "index": cluster_idx + 1,
            "bbox": bbox,
            "y_position": min_y,
            "shape_count": len(cluster),
        }
        return (min_y, visual_info)
    except Exception:
        # Skip if cropping fails
        return None


def _extract_diagrams_from_shapes(
    page, shapes: List[Dict], page_num: int
) -> List[Tuple[float, Dict]]:
    """
    Extract diagrams from vector shapes by clustering and rendering.

    Args:
        page: pdfplumber page object
        shapes: List of shape dictionaries
        page_num: Page number (0-indexed)

    Returns:
        List of tuples (y_position, visual_info)
    """
    diagrams = []

    clusters = _cluster_shapes_by_proximity(shapes)

    for cluster_idx, cluster in enumerate(clusters):
        diagram = _extract_diagram_from_cluster(page, cluster, cluster_idx, page_num)
        if diagram:
            diagrams.append(diagram)

    return diagrams


def _save_visuals_to_disk(
    visuals: List[Tuple[float, Dict]], page_num: int, output_folder: str
) -> None:
    """
    Save extracted visual elements to disk.

    Args:
        visuals: List of tuples (y_position, visual_info)
        page_num: Page number (0-indexed)
        output_folder: Folder to save images to
    """
    os.makedirs(output_folder, exist_ok=True)

    for y_pos, visual in visuals:
        visual_type = visual["type"]
        visual_idx = visual["index"]
        img_path = f"{output_folder}/page{page_num+1}_{visual_type}{visual_idx}.png"
        visual["image"].save(img_path)


def extract_visual_elements(
    page, page_num: int, output_folder: Optional[str] = None
) -> List[Tuple[float, Dict]]:
    """
    Extract all visual elements from a page including images and diagrams.

    Args:
        page: pdfplumber page object
        page_num: Page number (0-indexed)
        output_folder: Optional folder to save extracted visuals

    Returns:
        List of tuples (y_position, visual_info) sorted by vertical position
    """
    visuals = []

    # Extract embedded images
    images = _extract_embedded_images(page, page_num)
    visuals.extend(images)

    # Extract diagrams from vector graphics
    shapes = _extract_vector_shapes(page)
    diagrams = _extract_diagrams_from_shapes(page, shapes, page_num)
    visuals.extend(diagrams)

    # Save visuals if output folder is specified
    if output_folder and visuals:
        _save_visuals_to_disk(visuals, page_num, output_folder)

    return visuals


# ============================================================================
# Text Processing Functions
# ============================================================================


def _calculate_line_y_position(line: str, words: List[Dict]) -> Optional[float]:
    """
    Calculate the average vertical position of a text line.

    Uses a more robust matching algorithm that checks word sequences
    rather than just individual word presence to avoid false matches.

    Args:
        line: Text line to analyze
        words: List of word dictionaries from page.extract_words()

    Returns:
        Average y position or None if no words found
    """
    if not line.strip() or not words:
        return None

    # Split line into words for matching
    line_tokens = line.split()
    if not line_tokens:
        return None

    # Try to find a sequence of words that match the line tokens
    # This avoids false matches from repeated words elsewhere on the page
    best_match = []
    best_match_score = 0

    for i in range(len(words)):
        # Try to match starting from position i
        matched_words = []
        token_idx = 0

        for j in range(i, len(words)):
            if token_idx >= len(line_tokens):
                break

            # Check if current word matches current token
            word_text = words[j]["text"].strip()
            target_token = line_tokens[token_idx].strip()

            if (
                word_text == target_token
                or target_token in word_text
                or word_text in target_token
            ):
                matched_words.append(words[j])
                token_idx += 1

                # If words are too far apart vertically, this is probably not the right match
                if len(matched_words) > 1:
                    y_diff = abs(matched_words[-1]["top"] - matched_words[-2]["top"])
                    if (
                        y_diff > 5
                    ):  # Words on same line should be within ~5 points vertically
                        break
            elif len(matched_words) > 0:
                # Non-matching word after we started matching - this sequence is done
                break

        # Keep track of best match (most words matched)
        if len(matched_words) > best_match_score:
            best_match_score = len(matched_words)
            best_match = matched_words

    if not best_match:
        return None

    return sum(w["top"] for w in best_match) / len(best_match)


def _create_visual_token(visual_type: str, visual_num: int) -> str:
    """
    Create a placeholder token for a visual element.

    Args:
        visual_type: Type of visual (e.g., 'image', 'diagram')
        visual_num: Global visual number

    Returns:
        Formatted token string
    """
    return f"<<{visual_type.upper()}_{visual_num}>>"


def _insert_visuals_into_text(
    text: str, words: List[Dict], visual_refs: List[Tuple[float, int, str]]
) -> str:
    """
    Insert visual placeholder tokens into text at appropriate positions.

    Args:
        text: Extracted text from page
        words: List of word dictionaries for position information
        visual_refs: List of (y_position, visual_num, visual_type) tuples

    Returns:
        Text with visual tokens inserted
    """
    lines = text.split("\n")
    text_with_visuals = []
    current_visual_idx = 0

    for line in lines:
        line_y = _calculate_line_y_position(line, words)

        if line_y is not None:
            # Insert any visuals that appear before this line
            while (
                current_visual_idx < len(visual_refs)
                and visual_refs[current_visual_idx][0] < line_y
            ):
                visual_y, visual_num, visual_type = visual_refs[current_visual_idx]
                token = _create_visual_token(visual_type, visual_num)
                text_with_visuals.append(token)
                current_visual_idx += 1

        text_with_visuals.append(line)

    # Add any remaining visuals at the end
    while current_visual_idx < len(visual_refs):
        visual_y, visual_num, visual_type = visual_refs[current_visual_idx]
        token = _create_visual_token(visual_type, visual_num)
        text_with_visuals.append(token)
        current_visual_idx += 1

    return "\n".join(text_with_visuals)


def _add_visual_tokens_to_text(
    text: str, visual_refs: List[Tuple[float, int, str]]
) -> str:
    """
    Add visual tokens to text without position awareness (fallback method).

    Args:
        text: Extracted text
        visual_refs: List of (y_position, visual_num, visual_type) tuples

    Returns:
        Text with visual tokens appended
    """
    result = text
    for visual_y, visual_num, visual_type in visual_refs:
        token = _create_visual_token(visual_type, visual_num)
        result += f"\n{token}"
    return result


def _format_page_with_visuals(
    text: Optional[str], words: List[Dict], visual_refs: List[Tuple[float, int, str]]
) -> str:
    """
    Format page content with visual tokens inserted appropriately.

    Args:
        text: Extracted text from page (or None)
        words: List of word dictionaries for position information
        visual_refs: List of (y_position, visual_num, visual_type) tuples

    Returns:
        Formatted page text with visual tokens
    """
    if text and visual_refs:
        if words:
            # Smart insertion based on position
            return _insert_visuals_into_text(text, words, visual_refs)
        else:
            # Fallback: append visuals
            return _add_visual_tokens_to_text(text, visual_refs)
    elif text:
        return text
    else:
        # Only visuals on this page
        tokens = [_create_visual_token(vtype, vnum) for _, vnum, vtype in visual_refs]
        return "\n".join(tokens)


def _prepare_visual_references(
    visuals_with_pos: List[Tuple[float, Dict]], global_counter: int
) -> Tuple[List[Dict], List[Tuple[float, int, str]], int]:
    """
    Prepare visual references for text insertion and tracking.

    Args:
        visuals_with_pos: List of (y_position, visual_info) tuples
        global_counter: Current global visual counter

    Returns:
        Tuple of (updated_visuals, visual_refs, new_counter)
    """
    updated_visuals = []
    visual_refs = []

    for y_pos, visual_info in visuals_with_pos:
        global_counter += 1
        visual_info["global_index"] = global_counter
        updated_visuals.append(visual_info)
        visual_refs.append((y_pos, global_counter, visual_info["type"]))

    # Sort by vertical position
    visual_refs.sort(key=lambda x: x[0])

    return updated_visuals, visual_refs, global_counter


def _process_page_content(
    page, page_num: int, output_folder: Optional[str], global_counter: int
) -> Tuple[str, List[Dict], int]:
    """
    Process a single page to extract text and visuals.

    Args:
        page: pdfplumber page object
        page_num: Page number (0-indexed)
        output_folder: Optional folder to save visuals
        global_counter: Current global visual counter

    Returns:
        Tuple of (page_text, visuals, new_counter)
    """
    # Extract all visual elements
    visuals_with_pos = extract_visual_elements(page, page_num, output_folder)
    visuals_with_pos.sort(key=lambda x: x[0])

    # Prepare visual references
    updated_visuals, visual_refs, global_counter = _prepare_visual_references(
        visuals_with_pos, global_counter
    )

    # Extract text
    text = page.extract_text()
    words = page.extract_words() if text else []

    # Format page with visuals
    if text or visual_refs:
        page_header = f"\n--- Page {page_num + 1} ---\n"
        page_content = _format_page_with_visuals(text, words, visual_refs)
        page_text = page_header + page_content
    else:
        page_text = ""

    return page_text, updated_visuals, global_counter


# ============================================================================
# Main PDF Parsing Function
# ============================================================================


def parse_pdf(
    file_path: str, password: Optional[str] = None, output_folder: Optional[str] = None
) -> Dict[str, any]:
    """
    Extract text and all visual elements (images, diagrams, figures) from a PDF file.

    Args:
        file_path: Path to the PDF file
        password: Optional password if the PDF is encrypted
        output_folder: Optional folder to save extracted visuals

    Returns:
        Dictionary containing:
            - 'text': Extracted text with visual placeholder tokens inserted
            - 'visuals': List of dictionaries with visual info (type, image, page, index, bbox)
            - 'page_count': Number of pages in the PDF

    Raises:
        FileNotFoundError: If the PDF file doesn't exist
    """
    text_content = []
    all_visuals = []
    global_visual_counter = 0

    with pdfplumber.open(file_path, password=password) as pdf:
        page_count = len(pdf.pages)

        for page_num, page in enumerate(pdf.pages):
            page_text, page_visuals, global_visual_counter = _process_page_content(
                page, page_num, output_folder, global_visual_counter
            )

            if page_text:
                text_content.append(page_text)

            all_visuals.extend(page_visuals)

    return {
        "text": "\n".join(text_content),
        "visuals": all_visuals,
        "page_count": page_count,
    }


if __name__ == "__main__":
    # Example usage
    import sys

    if len(sys.argv) > 1:
        pdf_path = sys.argv[1]
        try:
            # Parse PDF to get text and all visual elements
            result = parse_pdf(pdf_path, output_folder="extracted_visuals")
            print(f"Successfully parsed PDF: {pdf_path}")
            print(f"Pages: {result['page_count']}")
            print(f"Text length: {len(result['text'])} characters")
            print(f"Visual elements found: {len(result['visuals'])}")

            # Count by type
            visual_types = {}
            for visual in result["visuals"]:
                vtype = visual["type"]
                visual_types[vtype] = visual_types.get(vtype, 0) + 1

            print("\nVisual elements by type:")
            for vtype, count in visual_types.items():
                print(f"  {vtype}: {count}")

            print("\nFirst 500 characters of text:")
            print(result["text"][:500])
        except Exception as e:
            print(f"Error parsing PDF: {e}")
            import traceback

            traceback.print_exc()
    else:
        print("Usage: python doc_parsing.py <path_to_pdf>")
