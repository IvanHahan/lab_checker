import os
from typing import Dict, List, Optional, Tuple

import pdfplumber


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


def extract_visual_elements(
    page, page_num: int, output_folder: Optional[str] = None
) -> List[Tuple[float, Dict]]:
    """
    Extract all visual elements from a page including images, figures, curves, and rects.

    Args:
        page: pdfplumber page object
        page_num: Page number (0-indexed)
        output_folder: Optional folder to save extracted visuals

    Returns:
        List of tuples (y_position, visual_info) sorted by vertical position
    """
    visuals = []

    # Extract embedded images
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
        visuals.append((img["top"], visual_info))

    # Extract figures (combinations of paths/curves that form diagrams)
    # Group curves and rects that are close together to identify diagrams
    curves = page.curves if hasattr(page, "curves") and page.curves else []
    rects = page.rects if hasattr(page, "rects") and page.rects else []

    # Combine all vector graphics elements
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

    # Group nearby shapes into diagram regions
    if all_shapes:
        # Sort by vertical position
        all_shapes.sort(key=lambda x: x["y"])

        # Cluster shapes that are close together (within 50 points vertically)
        clusters = []
        current_cluster = [all_shapes[0]] if all_shapes else []

        for shape in all_shapes[1:]:
            if current_cluster and abs(shape["y"] - current_cluster[-1]["y"]) < 50:
                current_cluster.append(shape)
            else:
                if (
                    len(current_cluster) >= 3
                ):  # Only consider groups of 3+ shapes as diagrams
                    clusters.append(current_cluster)
                current_cluster = [shape]

        if len(current_cluster) >= 3:
            clusters.append(current_cluster)

        # Extract each diagram cluster as an image
        for cluster_idx, cluster in enumerate(clusters):
            # Calculate bounding box for the entire cluster
            min_x = min(s["bbox"][0] for s in cluster)
            min_y = min(s["bbox"][1] for s in cluster)
            max_x = max(s["bbox"][2] for s in cluster)
            max_y = max(s["bbox"][3] for s in cluster)

            # Add some padding
            padding = 10
            diagram_bbox = (
                max(0, min_x - padding),
                max(0, min_y - padding),
                min(page.width, max_x + padding),
                min(page.height, max_y + padding),
            )

            # Extract the diagram region as an image
            try:
                cropped_page = page.crop(diagram_bbox)
                diagram_image = cropped_page.to_image(resolution=150).original

                visual_info = {
                    "type": "diagram",
                    "image": diagram_image,
                    "page": page_num + 1,
                    "index": cluster_idx + 1,
                    "bbox": diagram_bbox,
                    "y_position": min_y,
                    "shape_count": len(cluster),
                }
                visuals.append((min_y, visual_info))
            except Exception as e:
                # Skip if cropping fails
                pass

    # Save visuals if output folder is specified
    if output_folder and visuals:
        os.makedirs(output_folder, exist_ok=True)
        for y_pos, visual in visuals:
            visual_type = visual["type"]
            visual_idx = visual["index"]
            img_path = f"{output_folder}/page{page_num+1}_{visual_type}{visual_idx}.png"
            visual["image"].save(img_path)

    return visuals


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
            # Extract all visual elements (images, diagrams, figures)
            page_visuals_with_pos = extract_visual_elements(
                page, page_num, output_folder
            )

            # Sort visuals by vertical position
            page_visuals_with_pos.sort(key=lambda x: x[0])

            # Prepare visual references for text insertion
            page_visual_refs = []
            for y_pos, visual_info in page_visuals_with_pos:
                global_visual_counter += 1
                visual_info["global_index"] = global_visual_counter
                all_visuals.append(visual_info)
                page_visual_refs.append(
                    (y_pos, global_visual_counter, visual_info["type"])
                )

            # Sort visual references by vertical position
            page_visual_refs.sort(key=lambda x: x[0])

            # Extract text with layout information
            text = page.extract_text()

            if text or page_visual_refs:
                page_text = f"\n--- Page {page_num + 1} ---\n"

                # If we have text, try to insert visual placeholders at appropriate positions
                if text and page_visual_refs:
                    # Get text with layout to understand positioning
                    words = page.extract_words()

                    if words:
                        # Build text with visual tokens inserted at correct positions
                        lines = text.split("\n")
                        text_with_visuals = []

                        # Insert visual tokens between text sections based on vertical position
                        current_visual_idx = 0
                        for line in lines:
                            # Find words in this line to get approximate y position
                            line_words = [w for w in words if w["text"] in line]
                            if line_words:
                                line_y = sum(w["top"] for w in line_words) / len(
                                    line_words
                                )

                                # Insert any visuals that appear before this line
                                while (
                                    current_visual_idx < len(page_visual_refs)
                                    and page_visual_refs[current_visual_idx][0] < line_y
                                ):
                                    visual_y, visual_num, visual_type = (
                                        page_visual_refs[current_visual_idx]
                                    )
                                    text_with_visuals.append(
                                        f"<<{visual_type.upper()}_{visual_num}>>"
                                    )
                                    current_visual_idx += 1

                            text_with_visuals.append(line)

                        # Add any remaining visuals at the end
                        while current_visual_idx < len(page_visual_refs):
                            visual_y, visual_num, visual_type = page_visual_refs[
                                current_visual_idx
                            ]
                            text_with_visuals.append(
                                f"<<{visual_type.upper()}_{visual_num}>>"
                            )
                            current_visual_idx += 1

                        page_text += "\n".join(text_with_visuals)
                    else:
                        # Fallback: just add text and visuals
                        page_text += text
                        for visual_y, visual_num, visual_type in page_visual_refs:
                            page_text += f"\n<<{visual_type.upper()}_{visual_num}>>"
                elif text:
                    page_text += text
                else:
                    # Only visuals on this page
                    for visual_y, visual_num, visual_type in page_visual_refs:
                        page_text += f"<<{visual_type.upper()}_{visual_num}>>\n"

                text_content.append(page_text)

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
