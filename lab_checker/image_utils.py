"""Utilities for image processing operations."""

import numpy as np
from PIL import Image


def crop_image_to_content(image: Image.Image, padding: int = 10) -> Image.Image:
    """
    Crop an image to remove white/empty space around the content.

    Args:
        image: PIL Image object to crop
        padding: Padding in pixels to keep around the content (default: 10)

    Returns:
        Cropped PIL Image object
    """
    # Convert image to numpy array
    img_array = np.array(image)

    # Handle different image formats
    if len(img_array.shape) == 3:
        # RGB or RGBA image - check if pixel is "white" (close to 255)
        # For RGBA, check first 3 channels
        channels = (
            img_array[:, :, :3] if img_array.shape[2] >= 3 else img_array[:, :, :]
        )
        # A pixel is considered white if all channels are > 240
        white_mask = np.all(channels > 240, axis=2)
    else:
        # Grayscale image
        white_mask = img_array > 240

    # Find rows and columns that are not all white
    rows_with_content = ~np.all(white_mask, axis=1)
    cols_with_content = ~np.all(white_mask, axis=0)

    # Find the bounding box
    rows = np.where(rows_with_content)[0]
    cols = np.where(cols_with_content)[0]

    if len(rows) == 0 or len(cols) == 0:
        # No content found, return original image
        return image

    # Get bounding coordinates
    top = max(0, rows[0] - padding)
    bottom = min(img_array.shape[0], rows[-1] + padding + 1)
    left = max(0, cols[0] - padding)
    right = min(img_array.shape[1], cols[-1] + padding + 1)

    # Crop the image
    cropped_image = image.crop((left, top, right, bottom))
    return cropped_image
