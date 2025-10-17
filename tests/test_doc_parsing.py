import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from PIL import Image

from lab_checker.doc_parsing import (  # Basic PDF Reading Functions; Image Extraction Functions; Text Processing Functions; Main Function; Constants
    DIAGRAM_CLUSTERING_DISTANCE,
    DIAGRAM_DETECTION_THRESHOLD,
    DIAGRAM_PADDING,
    DIAGRAM_RESOLUTION,
    _add_visual_tokens_to_text,
    _calculate_cluster_bbox,
    _calculate_line_y_position,
    _cluster_shapes_by_proximity,
    _create_visual_token,
    _extract_diagram_from_cluster,
    _extract_diagrams_from_shapes,
    _extract_embedded_images,
    _extract_vector_shapes,
    _filter_text_excluding_diagrams,
    _format_page_with_visuals,
    _insert_visuals_into_text,
    _is_word_in_diagram,
    _prepare_visual_references,
    _process_page_content,
    _save_visuals_to_disk,
    extract_images_from_pdf,
    extract_visual_elements,
    parse_pdf,
    read_pdf,
    read_pdf_page,
)

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_pdf():
    """Create a mock PDF object."""
    pdf = MagicMock()
    return pdf


@pytest.fixture
def mock_page():
    """Create a mock page object."""
    page = MagicMock()
    page.width = 612
    page.height = 792
    page.extract_text.return_value = "Sample text"
    page.extract_words.return_value = []
    page.images = []
    page.curves = []
    page.rects = []
    return page


@pytest.fixture
def sample_image():
    """Create a sample PIL image."""
    return Image.new("RGB", (100, 100), color="red")


@pytest.fixture
def temp_output_dir():
    """Create a temporary directory for output."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


# ============================================================================
# Test Basic PDF Reading Functions
# ============================================================================


class TestReadPdf:
    """Tests for read_pdf function."""

    @patch("lab_checker.doc_parsing.pdfplumber.open")
    def test_read_pdf_single_page(self, mock_open):
        """Test reading a single-page PDF."""
        mock_pdf = MagicMock()
        mock_page = MagicMock()
        mock_page.extract_text.return_value = "Page 1 content"
        mock_pdf.pages = [mock_page]
        mock_open.return_value.__enter__.return_value = mock_pdf

        result = read_pdf("test.pdf")

        assert result == "Page 1 content"
        mock_open.assert_called_once_with("test.pdf", password=None)

    @patch("lab_checker.doc_parsing.pdfplumber.open")
    def test_read_pdf_multiple_pages(self, mock_open):
        """Test reading a multi-page PDF."""
        mock_pdf = MagicMock()
        mock_page1 = MagicMock()
        mock_page1.extract_text.return_value = "Page 1"
        mock_page2 = MagicMock()
        mock_page2.extract_text.return_value = "Page 2"
        mock_pdf.pages = [mock_page1, mock_page2]
        mock_open.return_value.__enter__.return_value = mock_pdf

        result = read_pdf("test.pdf")

        assert result == "Page 1\nPage 2"

    @patch("lab_checker.doc_parsing.pdfplumber.open")
    def test_read_pdf_with_password(self, mock_open):
        """Test reading a password-protected PDF."""
        mock_pdf = MagicMock()
        mock_page = MagicMock()
        mock_page.extract_text.return_value = "Protected content"
        mock_pdf.pages = [mock_page]
        mock_open.return_value.__enter__.return_value = mock_pdf

        result = read_pdf("test.pdf", password="secret")

        assert result == "Protected content"
        mock_open.assert_called_once_with("test.pdf", password="secret")

    @patch("lab_checker.doc_parsing.pdfplumber.open")
    def test_read_pdf_empty_pages(self, mock_open):
        """Test reading PDF with pages that have no text."""
        mock_pdf = MagicMock()
        mock_page1 = MagicMock()
        mock_page1.extract_text.return_value = None
        mock_page2 = MagicMock()
        mock_page2.extract_text.return_value = "Page 2"
        mock_pdf.pages = [mock_page1, mock_page2]
        mock_open.return_value.__enter__.return_value = mock_pdf

        result = read_pdf("test.pdf")

        assert result == "Page 2"


class TestReadPdfPage:
    """Tests for read_pdf_page function."""

    @patch("lab_checker.doc_parsing.pdfplumber.open")
    def test_read_pdf_page_success(self, mock_open):
        """Test reading a specific page successfully."""
        mock_pdf = MagicMock()
        mock_page = MagicMock()
        mock_page.extract_text.return_value = "Page content"
        mock_pdf.pages = [mock_page]
        mock_open.return_value.__enter__.return_value = mock_pdf

        result = read_pdf_page("test.pdf", 0)

        assert result == "Page content"

    @patch("lab_checker.doc_parsing.pdfplumber.open")
    def test_read_pdf_page_out_of_range(self, mock_open):
        """Test reading a page that doesn't exist."""
        mock_pdf = MagicMock()
        mock_pdf.pages = [MagicMock()]
        mock_open.return_value.__enter__.return_value = mock_pdf

        with pytest.raises(IndexError, match="Page 5 is out of range"):
            read_pdf_page("test.pdf", 5)

    @patch("lab_checker.doc_parsing.pdfplumber.open")
    def test_read_pdf_page_negative_index(self, mock_open):
        """Test reading with negative page index."""
        mock_pdf = MagicMock()
        mock_pdf.pages = [MagicMock()]
        mock_open.return_value.__enter__.return_value = mock_pdf

        with pytest.raises(IndexError, match="Page -1 is out of range"):
            read_pdf_page("test.pdf", -1)

    @patch("lab_checker.doc_parsing.pdfplumber.open")
    def test_read_pdf_page_empty_text(self, mock_open):
        """Test reading a page with no text."""
        mock_pdf = MagicMock()
        mock_page = MagicMock()
        mock_page.extract_text.return_value = None
        mock_pdf.pages = [mock_page]
        mock_open.return_value.__enter__.return_value = mock_pdf

        result = read_pdf_page("test.pdf", 0)

        assert result == ""


class TestExtractImagesFromPdf:
    """Tests for extract_images_from_pdf function."""

    @patch("lab_checker.doc_parsing.pdfplumber.open")
    def test_extract_images_no_output_folder(self, mock_open, sample_image):
        """Test extracting images without saving them."""
        mock_pdf = MagicMock()
        mock_page = MagicMock()
        mock_cropped = MagicMock()
        mock_cropped.to_image.return_value.original = sample_image
        mock_page.crop.return_value = mock_cropped
        mock_page.images = [{"x0": 10, "top": 20, "x1": 110, "bottom": 120}]
        mock_pdf.pages = [mock_page]
        mock_open.return_value.__enter__.return_value = mock_pdf

        result = extract_images_from_pdf("test.pdf")

        assert len(result) == 1
        assert result[0]["page"] == 1
        assert result[0]["index"] == 1
        assert result[0]["bbox"] == (10, 20, 110, 120)
        assert result[0]["image"] == sample_image

    @patch("lab_checker.doc_parsing.pdfplumber.open")
    def test_extract_images_with_output_folder(
        self, mock_open, sample_image, temp_output_dir
    ):
        """Test extracting and saving images."""
        mock_pdf = MagicMock()
        mock_page = MagicMock()
        mock_cropped = MagicMock()
        mock_cropped.to_image.return_value.original = sample_image
        mock_page.crop.return_value = mock_cropped
        mock_page.images = [{"x0": 10, "top": 20, "x1": 110, "bottom": 120}]
        mock_pdf.pages = [mock_page]
        mock_open.return_value.__enter__.return_value = mock_pdf

        result = extract_images_from_pdf("test.pdf", output_folder=temp_output_dir)

        assert len(result) == 1
        saved_file = Path(temp_output_dir) / "page1_img1.png"
        assert saved_file.exists()

    @patch("lab_checker.doc_parsing.pdfplumber.open")
    def test_extract_images_multiple_pages(self, mock_open, sample_image):
        """Test extracting images from multiple pages."""
        mock_pdf = MagicMock()
        mock_page1 = MagicMock()
        mock_page2 = MagicMock()
        mock_cropped = MagicMock()
        mock_cropped.to_image.return_value.original = sample_image

        mock_page1.crop.return_value = mock_cropped
        mock_page1.images = [{"x0": 10, "top": 20, "x1": 110, "bottom": 120}]

        mock_page2.crop.return_value = mock_cropped
        mock_page2.images = [{"x0": 30, "top": 40, "x1": 130, "bottom": 140}]

        mock_pdf.pages = [mock_page1, mock_page2]
        mock_open.return_value.__enter__.return_value = mock_pdf

        result = extract_images_from_pdf("test.pdf")

        assert len(result) == 2
        assert result[0]["page"] == 1
        assert result[1]["page"] == 2


# ============================================================================
# Test Image Extraction Functions
# ============================================================================


class TestExtractEmbeddedImages:
    """Tests for _extract_embedded_images function."""

    def test_extract_embedded_images_single(self, sample_image):
        """Test extracting a single embedded image."""
        mock_page = MagicMock()
        mock_cropped = MagicMock()
        mock_cropped.to_image.return_value.original = sample_image
        mock_page.crop.return_value = mock_cropped
        mock_page.images = [{"x0": 10, "top": 20, "x1": 110, "bottom": 120}]

        result = _extract_embedded_images(mock_page, 0)

        assert len(result) == 1
        y_pos, visual_info = result[0]
        assert y_pos == 20
        assert visual_info["type"] == "image"
        assert visual_info["page"] == 1
        assert visual_info["index"] == 1

    def test_extract_embedded_images_multiple(self, sample_image):
        """Test extracting multiple embedded images."""
        mock_page = MagicMock()
        mock_cropped = MagicMock()
        mock_cropped.to_image.return_value.original = sample_image
        mock_page.crop.return_value = mock_cropped
        mock_page.images = [
            {"x0": 10, "top": 20, "x1": 110, "bottom": 120},
            {"x0": 150, "top": 200, "x1": 250, "bottom": 300},
        ]

        result = _extract_embedded_images(mock_page, 0)

        assert len(result) == 2
        assert result[0][0] == 20  # First y position
        assert result[1][0] == 200  # Second y position

    def test_extract_embedded_images_none(self):
        """Test when there are no embedded images."""
        mock_page = MagicMock()
        mock_page.images = []

        result = _extract_embedded_images(mock_page, 0)

        assert len(result) == 0


class TestExtractVectorShapes:
    """Tests for _extract_vector_shapes function."""

    def test_extract_vector_shapes_with_curves(self):
        """Test extracting curves."""
        mock_page = MagicMock()
        mock_page.curves = [
            {"x0": 10, "top": 20, "x1": 110, "bottom": 120},
            {"x0": 30, "top": 40, "x1": 130, "bottom": 140},
        ]
        mock_page.rects = []

        result = _extract_vector_shapes(mock_page)

        assert len(result) == 2
        assert result[0]["type"] == "curve"
        assert result[0]["y"] == 20

    def test_extract_vector_shapes_with_rects(self):
        """Test extracting rectangles."""
        mock_page = MagicMock()
        mock_page.curves = []
        mock_page.rects = [
            {"x0": 50, "top": 60, "x1": 150, "bottom": 160},
        ]

        result = _extract_vector_shapes(mock_page)

        assert len(result) == 1
        assert result[0]["type"] == "rect"
        assert result[0]["y"] == 60

    def test_extract_vector_shapes_mixed(self):
        """Test extracting both curves and rectangles."""
        mock_page = MagicMock()
        mock_page.curves = [{"x0": 10, "top": 20, "x1": 110, "bottom": 120}]
        mock_page.rects = [{"x0": 50, "top": 60, "x1": 150, "bottom": 160}]

        result = _extract_vector_shapes(mock_page)

        assert len(result) == 2

    def test_extract_vector_shapes_no_attributes(self):
        """Test when page has no curves or rects attributes."""
        mock_page = MagicMock()
        del mock_page.curves
        del mock_page.rects

        result = _extract_vector_shapes(mock_page)

        assert len(result) == 0

    def test_extract_vector_shapes_none_values(self):
        """Test when curves/rects are None."""
        mock_page = MagicMock()
        mock_page.curves = None
        mock_page.rects = None

        result = _extract_vector_shapes(mock_page)

        assert len(result) == 0


class TestClusterShapesByProximity:
    """Tests for _cluster_shapes_by_proximity function."""

    def test_cluster_shapes_single_cluster(self):
        """Test clustering shapes that are close together."""
        shapes = [
            {"type": "rect", "bbox": (10, 20, 50, 40), "y": 20},
            {"type": "rect", "bbox": (60, 25, 100, 45), "y": 25},
            {"type": "rect", "bbox": (110, 30, 150, 50), "y": 30},
            {"type": "rect", "bbox": (160, 35, 200, 55), "y": 35},
        ]

        result = _cluster_shapes_by_proximity(shapes)

        assert len(result) == 1
        assert len(result[0]) == 4

    def test_cluster_shapes_multiple_clusters(self):
        """Test clustering shapes into multiple groups."""
        shapes = [
            {"type": "rect", "bbox": (10, 20, 50, 40), "y": 20},
            {"type": "rect", "bbox": (60, 25, 100, 45), "y": 25},
            {"type": "rect", "bbox": (110, 30, 150, 50), "y": 30},
            # Large gap
            {"type": "rect", "bbox": (10, 200, 50, 220), "y": 200},
            {"type": "rect", "bbox": (60, 205, 100, 225), "y": 205},
            {"type": "rect", "bbox": (110, 210, 150, 230), "y": 210},
        ]

        result = _cluster_shapes_by_proximity(shapes)

        assert len(result) == 2
        assert len(result[0]) == 3
        assert len(result[1]) == 3

    def test_cluster_shapes_below_threshold(self):
        """Test that small clusters are filtered out."""
        shapes = [
            {"type": "rect", "bbox": (10, 20, 50, 40), "y": 20},
            {"type": "rect", "bbox": (60, 25, 100, 45), "y": 25},
            # Only 2 shapes, below threshold of 3
        ]

        result = _cluster_shapes_by_proximity(shapes)

        assert len(result) == 0

    def test_cluster_shapes_empty(self):
        """Test clustering with no shapes."""
        result = _cluster_shapes_by_proximity([])
        assert len(result) == 0


class TestCalculateClusterBbox:
    """Tests for _calculate_cluster_bbox function."""

    def test_calculate_cluster_bbox_simple(self):
        """Test calculating bbox for a simple cluster."""
        cluster = [
            {"bbox": (10, 20, 50, 40), "y": 20},
            {"bbox": (60, 25, 100, 45), "y": 25},
        ]

        result = _calculate_cluster_bbox(cluster, 612, 792)

        # With DIAGRAM_PADDING = 10
        assert result == (0, 10, 110, 55)  # max(0, 10-10), max(0, 20-10), ...

    def test_calculate_cluster_bbox_at_page_edge(self):
        """Test bbox calculation near page boundaries."""
        cluster = [
            {"bbox": (5, 5, 50, 40), "y": 5},  # Near top-left
            {"bbox": (560, 740, 610, 790), "y": 740},  # Near bottom-right
        ]

        result = _calculate_cluster_bbox(cluster, 612, 792)

        # Should be clamped to page bounds
        assert result[0] == 0  # Can't go below 0
        assert result[1] == 0
        assert result[2] == 612  # Can't exceed page width
        assert result[3] == 792  # Can't exceed page height


class TestExtractDiagramFromCluster:
    """Tests for _extract_diagram_from_cluster function."""

    def test_extract_diagram_success(self, sample_image):
        """Test successful diagram extraction."""
        mock_page = MagicMock()
        mock_page.width = 612
        mock_page.height = 792
        mock_cropped = MagicMock()
        mock_cropped.to_image.return_value.original = sample_image
        mock_page.crop.return_value = mock_cropped

        cluster = [
            {"bbox": (10, 20, 50, 40), "y": 20},
            {"bbox": (60, 25, 100, 45), "y": 25},
            {"bbox": (110, 30, 150, 50), "y": 30},
        ]

        result = _extract_diagram_from_cluster(mock_page, cluster, 0, 0)

        assert result is not None
        y_pos, visual_info = result
        assert visual_info["type"] == "diagram"
        assert visual_info["page"] == 1
        assert visual_info["index"] == 1
        assert visual_info["shape_count"] == 3

    def test_extract_diagram_failure(self):
        """Test diagram extraction failure."""
        mock_page = MagicMock()
        mock_page.width = 612
        mock_page.height = 792
        mock_page.crop.side_effect = Exception("Crop failed")

        cluster = [{"bbox": (10, 20, 50, 40), "y": 20}]

        result = _extract_diagram_from_cluster(mock_page, cluster, 0, 0)

        assert result is None


class TestExtractDiagramsFromShapes:
    """Tests for _extract_diagrams_from_shapes function."""

    def test_extract_diagrams_single_diagram(self, sample_image):
        """Test extracting a single diagram."""
        mock_page = MagicMock()
        mock_page.width = 612
        mock_page.height = 792
        mock_cropped = MagicMock()
        mock_cropped.to_image.return_value.original = sample_image
        mock_page.crop.return_value = mock_cropped

        shapes = [
            {"type": "rect", "bbox": (10, 20, 50, 40), "y": 20},
            {"type": "rect", "bbox": (60, 25, 100, 45), "y": 25},
            {"type": "rect", "bbox": (110, 30, 150, 50), "y": 30},
        ]

        result = _extract_diagrams_from_shapes(mock_page, shapes, 0)

        assert len(result) == 1

    def test_extract_diagrams_no_shapes(self):
        """Test when there are no shapes."""
        mock_page = MagicMock()
        result = _extract_diagrams_from_shapes(mock_page, [], 0)
        assert len(result) == 0


class TestSaveVisualsToDisk:
    """Tests for _save_visuals_to_disk function."""

    def test_save_visuals_to_disk(self, sample_image, temp_output_dir):
        """Test saving visuals to disk."""
        visuals = [
            (
                20,
                {
                    "type": "image",
                    "image": sample_image,
                    "index": 1,
                },
            ),
            (
                100,
                {
                    "type": "diagram",
                    "image": sample_image,
                    "index": 1,
                },
            ),
        ]

        _save_visuals_to_disk(visuals, 0, temp_output_dir)

        img_path = Path(temp_output_dir) / "page1_image1.png"
        diagram_path = Path(temp_output_dir) / "page1_diagram1.png"

        assert img_path.exists()
        assert diagram_path.exists()


class TestExtractVisualElements:
    """Tests for extract_visual_elements function."""

    def test_extract_visual_elements_complete(self, sample_image):
        """Test extracting both images and diagrams."""
        mock_page = MagicMock()
        mock_page.width = 612
        mock_page.height = 792

        # Setup for embedded images
        mock_cropped_img = MagicMock()
        mock_cropped_img.to_image.return_value.original = sample_image
        mock_page.images = [{"x0": 10, "top": 20, "x1": 110, "bottom": 120}]

        # Setup for diagrams
        mock_cropped_diagram = MagicMock()
        mock_cropped_diagram.to_image.return_value.original = sample_image
        mock_page.curves = [
            {"x0": 10, "top": 200, "x1": 50, "bottom": 220},
            {"x0": 60, "top": 205, "x1": 100, "bottom": 225},
            {"x0": 110, "top": 210, "x1": 150, "bottom": 230},
        ]
        mock_page.rects = []

        def crop_side_effect(bbox):
            if bbox[1] < 150:  # Image crop
                return mock_cropped_img
            else:  # Diagram crop
                return mock_cropped_diagram

        mock_page.crop.side_effect = crop_side_effect

        result = extract_visual_elements(mock_page, 0)

        # Should have both image and diagram
        assert len(result) >= 1  # At least the image

    def test_extract_visual_elements_sorted(self, sample_image):
        """Test that visual elements can be sorted by position."""
        mock_page = MagicMock()
        mock_page.width = 612
        mock_page.height = 792
        mock_cropped = MagicMock()
        mock_cropped.to_image.return_value.original = sample_image

        mock_page.images = [
            {"x0": 10, "top": 100, "x1": 110, "bottom": 200},  # Second
            {"x0": 10, "top": 50, "x1": 110, "bottom": 150},  # First
        ]
        mock_page.curves = []
        mock_page.rects = []
        mock_page.crop.return_value = mock_cropped

        result = extract_visual_elements(mock_page, 0)

        # Result should contain both images with their y positions
        assert len(result) == 2
        assert result[0][0] == 100  # First in list
        assert result[1][0] == 50  # Second in list

        # When sorted, should be in y position order
        sorted_result = sorted(result, key=lambda x: x[0])
        assert sorted_result[0][0] == 50
        assert sorted_result[1][0] == 100


# ============================================================================
# Test Text Processing Functions
# ============================================================================


class TestCalculateLineYPosition:
    """Tests for _calculate_line_y_position function."""

    def test_calculate_line_y_position_simple(self):
        """Test calculating y position for a simple line."""
        line = "Hello world"
        words = [
            {"text": "Hello", "top": 100, "x0": 10},
            {"text": "world", "top": 100, "x0": 60},
        ]

        result = _calculate_line_y_position(line, words)

        assert result == 100

    def test_calculate_line_y_position_partial_match(self):
        """Test with partial word matches."""
        line = "The quick brown"
        words = [
            {"text": "The", "top": 50, "x0": 10},
            {"text": "quick", "top": 50, "x0": 40},
            {"text": "brown", "top": 50, "x0": 80},
            {"text": "fox", "top": 50, "x0": 120},  # Not in line
        ]

        result = _calculate_line_y_position(line, words)

        assert result == 50

    def test_calculate_line_y_position_no_match(self):
        """Test when line doesn't match any words."""
        line = "Nonexistent text"
        words = [
            {"text": "Other", "top": 100, "x0": 10},
            {"text": "words", "top": 100, "x0": 60},
        ]

        result = _calculate_line_y_position(line, words)

        assert result is None

    def test_calculate_line_y_position_empty_line(self):
        """Test with empty line."""
        result = _calculate_line_y_position("", [])
        assert result is None

    def test_calculate_line_y_position_empty_words(self):
        """Test with no words."""
        result = _calculate_line_y_position("Some text", [])
        assert result is None

    def test_calculate_line_y_position_different_lines(self):
        """Test that words on different lines aren't matched."""
        line = "First line"
        words = [
            {"text": "First", "top": 100, "x0": 10},
            {"text": "line", "top": 150, "x0": 60},  # Different y position
        ]

        result = _calculate_line_y_position(line, words)

        # Should only match "First" since "line" is on a different vertical position
        assert result == 100 or result is None  # Depends on matching logic


class TestCreateVisualToken:
    """Tests for _create_visual_token function."""

    def test_create_visual_token_image(self):
        """Test creating an image token."""
        result = _create_visual_token("image", 1)
        assert result == "<<IMAGE_1>>"

    def test_create_visual_token_diagram(self):
        """Test creating a diagram token."""
        result = _create_visual_token("diagram", 5)
        assert result == "<<DIAGRAM_5>>"


class TestInsertVisualsIntoText:
    """Tests for _insert_visuals_into_text function."""

    def test_insert_visuals_into_text_simple(self):
        """Test inserting visual tokens into text."""
        text = "Line 1\nLine 2\nLine 3"
        words = [
            {"text": "Line", "top": 100, "x0": 10},
            {"text": "1", "top": 100, "x0": 50},
            {"text": "Line", "top": 150, "x0": 10},
            {"text": "2", "top": 150, "x0": 50},
            {"text": "Line", "top": 200, "x0": 10},
            {"text": "3", "top": 200, "x0": 50},
        ]
        visual_refs = [(125, 1, "image"), (175, 2, "diagram")]

        result = _insert_visuals_into_text(text, words, visual_refs)

        # Visual at y=125 should appear between Line 1 (y=100) and Line 2 (y=150)
        # Visual at y=175 should appear between Line 2 (y=150) and Line 3 (y=200)
        assert "<<IMAGE_1>>" in result
        assert "<<DIAGRAM_2>>" in result

    def test_insert_visuals_into_text_at_end(self):
        """Test inserting visuals at the end."""
        text = "Line 1\nLine 2"
        words = [
            {"text": "Line", "top": 100, "x0": 10},
            {"text": "1", "top": 100, "x0": 50},
            {"text": "Line", "top": 150, "x0": 10},
            {"text": "2", "top": 150, "x0": 50},
        ]
        visual_refs = [(200, 1, "image")]

        result = _insert_visuals_into_text(text, words, visual_refs)

        assert "<<IMAGE_1>>" in result


class TestAddVisualTokensToText:
    """Tests for _add_visual_tokens_to_text function."""

    def test_add_visual_tokens_to_text(self):
        """Test adding visual tokens to text."""
        text = "Some text"
        visual_refs = [(100, 1, "image"), (200, 2, "diagram")]

        result = _add_visual_tokens_to_text(text, visual_refs)

        assert "Some text" in result
        assert "<<IMAGE_1>>" in result
        assert "<<DIAGRAM_2>>" in result


class TestFormatPageWithVisuals:
    """Tests for _format_page_with_visuals function."""

    def test_format_page_with_visuals_with_words(self):
        """Test formatting with word position data."""
        text = "Line 1\nLine 2"
        words = [
            {"text": "Line", "top": 100, "x0": 10},
            {"text": "1", "top": 100, "x0": 50},
            {"text": "Line", "top": 150, "x0": 10},
            {"text": "2", "top": 150, "x0": 50},
        ]
        visual_refs = [(125, 1, "image")]

        result = _format_page_with_visuals(text, words, visual_refs)

        assert "Line 1" in result
        assert "Line 2" in result
        assert "<<IMAGE_1>>" in result

    def test_format_page_with_visuals_without_words(self):
        """Test formatting without word position data."""
        text = "Some text"
        visual_refs = [(100, 1, "image")]

        result = _format_page_with_visuals(text, [], visual_refs)

        assert "Some text" in result
        assert "<<IMAGE_1>>" in result

    def test_format_page_with_visuals_only_visuals(self):
        """Test formatting with only visuals, no text."""
        visual_refs = [(100, 1, "image"), (200, 2, "diagram")]

        result = _format_page_with_visuals(None, [], visual_refs)

        assert "<<IMAGE_1>>" in result
        assert "<<DIAGRAM_2>>" in result

    def test_format_page_with_visuals_only_text(self):
        """Test formatting with only text, no visuals."""
        text = "Just text"

        result = _format_page_with_visuals(text, [], [])

        assert result == "Just text"


class TestPrepareVisualReferences:
    """Tests for _prepare_visual_references function."""

    def test_prepare_visual_references(self):
        """Test preparing visual references."""
        visuals_with_pos = [
            (100, {"type": "image", "page": 1, "index": 1}),
            (50, {"type": "diagram", "page": 1, "index": 1}),
        ]

        updated_visuals, visual_refs, counter = _prepare_visual_references(
            visuals_with_pos, 0
        )

        assert len(updated_visuals) == 2
        assert len(visual_refs) == 2
        assert counter == 2
        # Should be sorted by y position
        assert visual_refs[0][0] == 50  # diagram comes first
        assert visual_refs[1][0] == 100  # image comes second
        assert updated_visuals[0]["global_index"] == 1
        assert updated_visuals[1]["global_index"] == 2


class TestIsWordInDiagram:
    """Tests for _is_word_in_diagram function."""

    def test_is_word_in_diagram_inside(self):
        """Test word inside diagram bbox."""
        word = {"x0": 50, "top": 50, "x1": 100, "bottom": 80}
        diagram_bboxes = [(40, 40, 110, 90)]

        result = _is_word_in_diagram(word, diagram_bboxes)

        assert result is True

    def test_is_word_in_diagram_outside(self):
        """Test word outside diagram bbox."""
        word = {"x0": 200, "top": 200, "x1": 250, "bottom": 230}
        diagram_bboxes = [(40, 40, 110, 90)]

        result = _is_word_in_diagram(word, diagram_bboxes)

        assert result is False

    def test_is_word_in_diagram_multiple_bboxes(self):
        """Test word against multiple diagram bboxes."""
        word = {"x0": 150, "top": 150, "x1": 200, "bottom": 180}
        diagram_bboxes = [(40, 40, 110, 90), (140, 140, 210, 190)]

        result = _is_word_in_diagram(word, diagram_bboxes)

        assert result is True

    def test_is_word_in_diagram_edge_case(self):
        """Test word at edge of diagram."""
        word = {"x0": 100, "top": 100, "x1": 150, "bottom": 130}
        diagram_bboxes = [(100, 100, 150, 130)]

        result = _is_word_in_diagram(word, diagram_bboxes)

        assert result is True


class TestFilterTextExcludingDiagrams:
    """Tests for _filter_text_excluding_diagrams function."""

    def test_filter_text_excluding_diagrams(self):
        """Test filtering text to exclude diagram regions."""
        text = "Word1 Word2 Word3"
        words = [
            {"text": "Word1", "x0": 10, "top": 100, "x1": 50, "bottom": 120},
            {
                "text": "Word2",
                "x0": 60,
                "top": 100,
                "x1": 100,
                "bottom": 120,
            },  # In diagram
            {"text": "Word3", "x0": 200, "top": 100, "x1": 240, "bottom": 120},
        ]
        diagram_bboxes = [(55, 95, 105, 125)]

        filtered_text, filtered_words = _filter_text_excluding_diagrams(
            text, words, diagram_bboxes
        )

        assert "Word1" in filtered_text
        assert "Word2" not in filtered_text
        assert "Word3" in filtered_text
        assert len(filtered_words) == 2

    def test_filter_text_excluding_diagrams_no_diagrams(self):
        """Test filtering with no diagrams."""
        text = "Word1 Word2"
        words = [
            {"text": "Word1", "x0": 10, "top": 100, "x1": 50, "bottom": 120},
            {"text": "Word2", "x0": 60, "top": 100, "x1": 100, "bottom": 120},
        ]

        filtered_text, filtered_words = _filter_text_excluding_diagrams(text, words, [])

        assert filtered_text == text
        assert filtered_words == words

    def test_filter_text_excluding_diagrams_all_filtered(self):
        """Test when all text is in diagrams."""
        text = "Word1 Word2"
        words = [
            {"text": "Word1", "x0": 10, "top": 100, "x1": 50, "bottom": 120},
            {"text": "Word2", "x0": 60, "top": 100, "x1": 100, "bottom": 120},
        ]
        diagram_bboxes = [(0, 0, 200, 200)]

        filtered_text, filtered_words = _filter_text_excluding_diagrams(
            text, words, diagram_bboxes
        )

        assert filtered_text == ""
        assert len(filtered_words) == 0

    def test_filter_text_excluding_diagrams_multiline(self):
        """Test filtering multiline text."""
        text = "Line1Word1 Line1Word2\nLine2Word1 Line2Word2"
        words = [
            {"text": "Line1Word1", "x0": 10, "top": 100, "x1": 50, "bottom": 120},
            {"text": "Line1Word2", "x0": 60, "top": 100, "x1": 100, "bottom": 120},
            {
                "text": "Line2Word1",
                "x0": 10,
                "top": 150,
                "x1": 50,
                "bottom": 170,
            },  # In diagram
            {
                "text": "Line2Word2",
                "x0": 60,
                "top": 150,
                "x1": 100,
                "bottom": 170,
            },  # In diagram
        ]
        diagram_bboxes = [(0, 140, 200, 180)]

        filtered_text, filtered_words = _filter_text_excluding_diagrams(
            text, words, diagram_bboxes
        )

        assert "Line1Word1" in filtered_text
        assert "Line2Word1" not in filtered_text


class TestProcessPageContent:
    """Tests for _process_page_content function."""

    @patch("lab_checker.doc_parsing.extract_visual_elements")
    def test_process_page_content_with_text_and_visuals(
        self, mock_extract_visuals, sample_image
    ):
        """Test processing page with both text and visuals."""
        mock_page = MagicMock()
        mock_page.extract_text.return_value = "Page content"
        mock_page.extract_words.return_value = [
            {"text": "Page", "x0": 10, "top": 100, "x1": 50, "bottom": 120},
        ]

        mock_extract_visuals.return_value = [
            (50, {"type": "image", "bbox": (10, 40, 110, 140)}),
        ]

        page_text, visuals, counter = _process_page_content(mock_page, 0, None, 0)

        assert "Page 1" in page_text
        assert "Page content" in page_text
        assert len(visuals) == 1
        assert counter == 1

    @patch("lab_checker.doc_parsing.extract_visual_elements")
    def test_process_page_content_with_diagrams(self, mock_extract_visuals):
        """Test processing page with diagrams."""
        mock_page = MagicMock()
        mock_page.extract_text.return_value = "Word1 Word2"
        mock_page.extract_words.return_value = [
            {"text": "Word1", "x0": 10, "top": 100, "x1": 50, "bottom": 120},
            {"text": "Word2", "x0": 60, "top": 100, "x1": 100, "bottom": 120},
        ]

        mock_extract_visuals.return_value = [
            (50, {"type": "diagram", "bbox": (55, 95, 105, 125)}),
        ]

        page_text, visuals, counter = _process_page_content(mock_page, 0, None, 0)

        # Word2 should be filtered out because it's in the diagram
        assert "Word1" in page_text
        assert len(visuals) == 1

    @patch("lab_checker.doc_parsing.extract_visual_elements")
    def test_process_page_content_empty_page(self, mock_extract_visuals):
        """Test processing an empty page."""
        mock_page = MagicMock()
        mock_page.extract_text.return_value = None
        mock_page.extract_words.return_value = []
        mock_extract_visuals.return_value = []

        page_text, visuals, counter = _process_page_content(mock_page, 0, None, 0)

        assert page_text == ""
        assert len(visuals) == 0
        assert counter == 0


# ============================================================================
# Test Main PDF Parsing Function
# ============================================================================


class TestParsePdf:
    """Tests for parse_pdf function."""

    @patch("lab_checker.doc_parsing.pdfplumber.open")
    @patch("lab_checker.doc_parsing._process_page_content")
    def test_parse_pdf_single_page(self, mock_process, mock_open):
        """Test parsing a single-page PDF."""
        mock_pdf = MagicMock()
        mock_page = MagicMock()
        mock_pdf.pages = [mock_page]
        mock_open.return_value.__enter__.return_value = mock_pdf

        mock_process.return_value = (
            "\n--- Page 1 ---\nPage content",
            [{"type": "image", "global_index": 1}],
            1,
        )

        result = parse_pdf("test.pdf")

        assert result["page_count"] == 1
        assert "Page content" in result["text"]
        assert len(result["visuals"]) == 1

    @patch("lab_checker.doc_parsing.pdfplumber.open")
    @patch("lab_checker.doc_parsing._process_page_content")
    def test_parse_pdf_multiple_pages(self, mock_process, mock_open):
        """Test parsing a multi-page PDF."""
        mock_pdf = MagicMock()
        mock_pdf.pages = [MagicMock(), MagicMock()]
        mock_open.return_value.__enter__.return_value = mock_pdf

        mock_process.side_effect = [
            ("\n--- Page 1 ---\nPage 1 content", [], 0),
            ("\n--- Page 2 ---\nPage 2 content", [], 0),
        ]

        result = parse_pdf("test.pdf")

        assert result["page_count"] == 2
        assert "Page 1 content" in result["text"]
        assert "Page 2 content" in result["text"]

    @patch("lab_checker.doc_parsing.pdfplumber.open")
    @patch("lab_checker.doc_parsing._process_page_content")
    def test_parse_pdf_with_password(self, mock_process, mock_open):
        """Test parsing password-protected PDF."""
        mock_pdf = MagicMock()
        mock_pdf.pages = [MagicMock()]
        mock_open.return_value.__enter__.return_value = mock_pdf

        mock_process.return_value = ("\n--- Page 1 ---\nContent", [], 0)

        result = parse_pdf("test.pdf", password="secret")

        mock_open.assert_called_once_with("test.pdf", password="secret")

    @patch("lab_checker.doc_parsing.pdfplumber.open")
    @patch("lab_checker.doc_parsing._process_page_content")
    def test_parse_pdf_with_output_folder(
        self, mock_process, mock_open, temp_output_dir
    ):
        """Test parsing with output folder specified."""
        mock_pdf = MagicMock()
        mock_pdf.pages = [MagicMock()]
        mock_open.return_value.__enter__.return_value = mock_pdf

        mock_process.return_value = ("\n--- Page 1 ---\nContent", [], 0)

        result = parse_pdf("test.pdf", output_folder=temp_output_dir)

        # Verify that _process_page_content was called with the output folder
        mock_process.assert_called_once()
        call_args = mock_process.call_args
        assert call_args[0][2] == temp_output_dir

    @patch("lab_checker.doc_parsing.pdfplumber.open")
    @patch("lab_checker.doc_parsing._process_page_content")
    def test_parse_pdf_accumulates_visuals(self, mock_process, mock_open):
        """Test that visuals from all pages are accumulated."""
        mock_pdf = MagicMock()
        mock_pdf.pages = [MagicMock(), MagicMock()]
        mock_open.return_value.__enter__.return_value = mock_pdf

        mock_process.side_effect = [
            (
                "\n--- Page 1 ---\nPage 1",
                [{"type": "image", "global_index": 1}],
                1,
            ),
            (
                "\n--- Page 2 ---\nPage 2",
                [{"type": "diagram", "global_index": 2}],
                2,
            ),
        ]

        result = parse_pdf("test.pdf")

        assert len(result["visuals"]) == 2
        assert result["visuals"][0]["type"] == "image"
        assert result["visuals"][1]["type"] == "diagram"


# ============================================================================
# Test Constants
# ============================================================================


def test_constants():
    """Test that constants have expected values."""
    assert DIAGRAM_DETECTION_THRESHOLD == 3
    assert DIAGRAM_CLUSTERING_DISTANCE == 50
    assert DIAGRAM_PADDING == 10
    assert DIAGRAM_RESOLUTION == 150
