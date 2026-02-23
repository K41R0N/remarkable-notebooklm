"""fpdf2-based PDF generator for reMarkable 2 display.

Page size: 157.8 × 210.4mm (447.3 × 596.4 PDF points)
Left margin: 25.4mm (72pt) — accounts for reMarkable toolbar
Min font: 12pt, line spacing: 1.4×

Do NOT use standard paper sizes — reMarkable 2 is not A5.
"""

from __future__ import annotations

from pathlib import Path


class RemarkablePDFGenerator:
    """Generate AI response PDFs formatted for reMarkable 2 display."""

    def generate(self, text: str, output_path: Path, title: str = "AI Response") -> Path:
        """Convert AI response text to a reMarkable-formatted PDF.

        Args:
            text: Plain text or Markdown content from the AI response.
            output_path: Where to write the PDF file.
            title: Document title shown in the header.

        Returns:
            Path to the generated PDF file.

        Raises:
            ValueError: If output would exceed 100MB.
        """
        raise NotImplementedError("Milestone 5: implement PDF generation")
