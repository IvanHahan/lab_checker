import os
from typing import Dict, List, Optional

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


def parse_pdf(
    file_path: str, password: Optional[str] = None, output_folder: Optional[str] = None
) -> Dict[str, any]:
    """
    Extract both text and images from a PDF file with image placeholder tokens.

    Args:
        file_path: Path to the PDF file
        password: Optional password if the PDF is encrypted
        output_folder: Optional folder to save extracted images

    Returns:
        Dictionary containing:
            - 'text': Extracted text with image placeholder tokens inserted
            - 'images': List of dictionaries with image info (image, page, index, bbox)
            - 'page_count': Number of pages in the PDF

    Raises:
        FileNotFoundError: If the PDF file doesn't exist
    """
    text_content = []
    images = []
    global_img_counter = 0

    with pdfplumber.open(file_path, password=password) as pdf:
        page_count = len(pdf.pages)

        for page_num, page in enumerate(pdf.pages):
            # Get all images on this page with their positions
            page_images = []
            for img_index, img in enumerate(page.images):
                image_bbox = (img["x0"], img["top"], img["x1"], img["bottom"])
                cropped_page = page.crop(image_bbox)
                pil_image = cropped_page.to_image().original

                global_img_counter += 1
                image_info = {
                    "image": pil_image,
                    "page": page_num + 1,
                    "index": img_index + 1,
                    "bbox": image_bbox,
                    "y_position": img["top"],  # Vertical position on page
                }
                images.append(image_info)
                page_images.append((img["top"], global_img_counter, img_index + 1))

                if output_folder:
                    os.makedirs(output_folder, exist_ok=True)
                    img_path = f"{output_folder}/page{page_num+1}_img{img_index+1}.png"
                    pil_image.save(img_path)

            # Sort images by vertical position
            page_images.sort(key=lambda x: x[0])

            # Extract text with layout information
            text = page.extract_text()

            if text or page_images:
                page_text = f"\n--- Page {page_num + 1} ---\n"

                # If we have text, try to insert image placeholders at appropriate positions
                if text and page_images:
                    # Get text with layout to understand positioning
                    words = page.extract_words()

                    if words:
                        # Build text with image tokens inserted at correct positions
                        lines = text.split("\n")
                        text_with_images = []

                        # Simple approach: insert image tokens between text sections
                        # based on vertical position
                        current_img_idx = 0
                        for line in lines:
                            # Find words in this line to get approximate y position
                            line_words = [w for w in words if w["text"] in line]
                            if line_words:
                                line_y = sum(w["top"] for w in line_words) / len(
                                    line_words
                                )

                                # Insert any images that appear before this line
                                while (
                                    current_img_idx < len(page_images)
                                    and page_images[current_img_idx][0] < line_y
                                ):
                                    img_y, img_num, img_idx = page_images[
                                        current_img_idx
                                    ]
                                    text_with_images.append(f"<<IMAGE_{img_num}>>")
                                    current_img_idx += 1

                            text_with_images.append(line)

                        # Add any remaining images at the end
                        while current_img_idx < len(page_images):
                            img_y, img_num, img_idx = page_images[current_img_idx]
                            text_with_images.append(f"<<IMAGE_{img_num}>>")
                            current_img_idx += 1

                        page_text += "\n".join(text_with_images)
                    else:
                        # Fallback: just add text and images
                        page_text += text
                        for img_y, img_num, img_idx in page_images:
                            page_text += f"\n<<IMAGE_{img_num}>>"
                elif text:
                    page_text += text
                else:
                    # Only images on this page
                    for img_y, img_num, img_idx in page_images:
                        page_text += f"<<IMAGE_{img_num}>>\n"

                text_content.append(page_text)

    return {
        "text": "\n".join(text_content),
        "images": images,
        "page_count": page_count,
    }


if __name__ == "__main__":
    # Example usage
    import sys

    if len(sys.argv) > 1:
        pdf_path = sys.argv[1]
        try:
            # Parse PDF to get both text and images
            result = parse_pdf(pdf_path)
            print(f"Successfully parsed PDF: {pdf_path}")
            print(f"Pages: {result['page_count']}")
            print(f"Text length: {len(result['text'])} characters")
            print(f"Images found: {len(result['images'])}")
            print("\nFirst 500 characters of text:")
            print(result["text"][:500])
        except Exception as e:
            print(f"Error parsing PDF: {e}")
    else:
        print("Usage: python doc_parsing.py <path_to_pdf>")
