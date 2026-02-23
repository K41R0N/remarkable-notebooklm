"""reMarkable 2 page dimension constants for PDF generation.

reMarkable 2 display: 1404 × 1872 pixels at 226 DPI
Physical: 6.212 × 8.283 inches = 447.3 × 596.4 PDF points

This is close to A5 but NOT a standard paper size. Do not use A5.
"""

# PDF points (1 point = 1/72 inch)
RM2_WIDTH_PT: float = 447.3  # 6.212 inches × 72 pt/inch
RM2_HEIGHT_PT: float = 596.4  # 8.283 inches × 72 pt/inch

# Millimeters (for fpdf2 which uses mm by default)
RM2_WIDTH_MM: float = 157.8
RM2_HEIGHT_MM: float = 210.4

# Margins (PDF points)
LEFT_MARGIN_PT: float = 72  # 1 inch — accounts for reMarkable left toolbar
RIGHT_MARGIN_PT: float = 18  # 0.25 inch
TOP_MARGIN_PT: float = 28
BOTTOM_MARGIN_PT: float = 28

# Margins (mm, for fpdf2)
LEFT_MARGIN_MM: float = 25.4  # ~72pt
RIGHT_MARGIN_MM: float = 6.4
TOP_MARGIN_MM: float = 9.9
BOTTOM_MARGIN_MM: float = 9.9

# Typography
MIN_FONT_SIZE_PT: int = 12
BODY_LINE_SPACING: float = 1.4  # 1.3–1.5× recommended for e-ink
HEADER_FONT_SIZE_PT: int = 16
CODE_FONT_SIZE_PT: int = 11  # Monospace, slightly smaller

# Display properties
DISPLAY_WIDTH_PX: int = 1404
DISPLAY_HEIGHT_PX: int = 1872
DISPLAY_DPI: int = 226

# File limits
MAX_FILE_SIZE_MB: int = 100
MAX_FILE_SIZE_BYTES: int = MAX_FILE_SIZE_MB * 1024 * 1024
