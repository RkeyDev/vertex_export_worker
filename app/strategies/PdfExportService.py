import logging
import os
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Image, PageBreak, Spacer
from PIL import Image as PILImage
from typing import Tuple, List

from app.dataTypes.ExportRequest import ExportRequest
from app.dataTypes.OperationResult import OperationResult
from app.strategies.ExportProcessor import ExportProcessor

logger = logging.getLogger(__name__)

SUPPORTED_IMAGE_EXTENSIONS = ('.png', '.jpg', '.jpeg', '.bmp', '.gif')

PAGE_SIZE = letter
MARGIN_LEFT = 36
MARGIN_RIGHT = 36
MARGIN_TOP = 36
MARGIN_BOTTOM = 36
MAX_PRINTABLE_WIDTH = PAGE_SIZE[0] - (MARGIN_LEFT + MARGIN_RIGHT)
MAX_PRINTABLE_HEIGHT = PAGE_SIZE[1] - (MARGIN_TOP + MARGIN_BOTTOM)


class PdfExportService(ExportProcessor):

    @staticmethod
    def requiresScreenshots() -> bool:
        return True

    @staticmethod
    def exportBoard(export_request: ExportRequest) -> OperationResult:
        board_id        = export_request.board_id
        screenshots_dir = export_request.output_dir

        logger.info(
            "Starting PDF export for board '%s'. Scanning directory: %s",
            board_id,
            screenshots_dir,
        )

        try:
            screenshots = PdfExportService._get_images(screenshots_dir)
        except FileNotFoundError as e:
            logger.error("Screenshots directory not found for board '%s': %s", board_id, e)
            return OperationResult.FAILED

        if not screenshots:
            logger.warning(
                "No screenshots found in '%s' for board '%s'. Aborting PDF export.",
                screenshots_dir,
                board_id,
            )
            return OperationResult.FAILED

        logger.info("Found %d screenshot(s) for board '%s'.", len(screenshots), board_id)

        try:
            pdf_filename = f"{board_id}.pdf"
            output_path  = os.path.join(export_request.output_dir, pdf_filename)

            logger.debug("Writing PDF to: %s", output_path)

            doc = SimpleDocTemplate(
                output_path,
                pagesize=PAGE_SIZE,
                leftMargin=MARGIN_LEFT,
                rightMargin=MARGIN_RIGHT,
                topMargin=MARGIN_TOP,
                bottomMargin=MARGIN_BOTTOM,
            )

            styles = getSampleStyleSheet()
            cover_title_style = ParagraphStyle(
                "CoverTitle",
                parent=styles["Heading1"],
                fontName="Helvetica-Bold",
                fontSize=32,
                leading=38,
                textColor=colors.HexColor("#1A202C"),
                alignment=1,
                spaceAfter=0,
            )

            story = []

            # Title matches the PDF filename (without extension)
            title = board_id.replace("_", " ").replace("-", " ").title()
            logger.debug("Adding cover page with title: '%s'", title)
            story.append(Spacer(1, MAX_PRINTABLE_HEIGHT / 3))
            story.append(Paragraph(title, cover_title_style))
            story.append(PageBreak())

            total = len(screenshots)
            for index, path in enumerate(screenshots):
                logger.debug("Processing screenshot %d/%d: %s", index + 1, total, path)
                try:
                    w, h = PdfExportService._fit_image(path)
                    img_flowable = Image(path, width=w, height=h)
                    img_flowable.hAlign = "CENTER"

                    vertical_padding = max(0, (MAX_PRINTABLE_HEIGHT - h) / 2)
                    if vertical_padding > 0:
                        story.append(Spacer(1, vertical_padding))

                    story.append(img_flowable)

                    if index < total - 1:
                        story.append(PageBreak())

                except Exception as e:
                    logger.error("Skipping unreadable screenshot at '%s': %s", path, e)

            doc.build(story)
            logger.info(
                "PDF export complete for board '%s'. Output: %s", board_id, output_path
            )
            return OperationResult.SUCCEED

        except Exception as e:
            logger.exception(
                "Unexpected error during PDF export for board '%s': %s", board_id, e
            )
            return OperationResult.FAILED

    @staticmethod
    def _get_images(directory: str) -> List[str]:
        """Returns sorted list of supported image paths from the given directory."""
        if not os.path.isdir(directory):
            raise FileNotFoundError(f"Screenshots directory not found: {directory}")

        files = [
            os.path.join(directory, f)
            for f in os.listdir(directory)
            if f.lower().endswith(SUPPORTED_IMAGE_EXTENSIONS)
        ]
        return sorted(files)

    @staticmethod
    def _fit_image(image_path: str) -> Tuple[float, float]:
        """Scale image to fit within printable page bounds, preserving aspect ratio."""
        with PILImage.open(image_path) as img:
            img_width, img_height = img.size

        aspect = img_width / img_height
        width = MAX_PRINTABLE_WIDTH
        height = width / aspect

        if height > MAX_PRINTABLE_HEIGHT:
            height = MAX_PRINTABLE_HEIGHT
            width = height * aspect

        return width, height