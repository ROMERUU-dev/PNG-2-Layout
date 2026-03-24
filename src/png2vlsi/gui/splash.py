"""Professional startup splash screen for PNG2VLSI Pixel."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPainterPath, QPen, QPixmap
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QSplashScreen


SPLASH_PRIMARY = QColor("#3584E4")
SPLASH_SECONDARY = QColor("#62A0EA")
SPLASH_DARK = QColor("#102746")
SPLASH_ACCENT = QColor("#D7E8FF")
SPLASH_TEXT = QColor("#F8FBFF")
SPLASH_MUTED = QColor("#DCE9FA")
SPLASH_PROGRESS = QColor("#EEF5FF")
LOGO_PATH = Path("/home/romeruu/Descargas/ardilla_silueta_blanca_suave.svg")


def _draw_fallback_logo(painter: QPainter, rect: QRectF) -> None:
    """Fallback logo used only if the SVG cannot be loaded."""
    painter.save()
    painter.setPen(Qt.NoPen)
    painter.setBrush(QColor("#3584E4"))
    painter.drawRoundedRect(rect, 26, 26)

    painter.setPen(SPLASH_TEXT)
    painter.setFont(QFont("DejaVu Sans", max(14, int(rect.width() * 0.22)), QFont.Black))
    painter.drawText(rect, Qt.AlignCenter, "PXL")
    painter.restore()


def _draw_logo(painter: QPainter, rect: QRectF) -> None:
    """Draw the app SVG logo, falling back to a simple vector mark."""
    clip_path = QPainterPath()
    clip_path.addRoundedRect(rect, 26, 26)
    painter.save()
    painter.setClipPath(clip_path)

    renderer = QSvgRenderer(str(LOGO_PATH))
    if renderer.isValid():
        renderer.render(painter, rect)
        painter.restore()
        return

    _draw_fallback_logo(painter, rect)
    painter.restore()


def build_splash_pixmap(width: int = 1020, height: int = 520) -> QPixmap:
    """Create a polished startup splash image using Qt painting."""
    pixmap = QPixmap(width, height)
    pixmap.fill(Qt.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)

    bg = QLinearGradient(0, 0, width, height)
    bg.setColorAt(0.0, SPLASH_DARK)
    bg.setColorAt(0.45, SPLASH_PRIMARY)
    bg.setColorAt(1.0, QColor("#0A1830"))
    painter.fillRect(0, 0, width, height, bg)

    accent = QLinearGradient(0, height * 0.65, width, height)
    accent.setColorAt(0.0, QColor(183, 214, 255, 55))
    accent.setColorAt(1.0, QColor(255, 255, 255, 22))
    painter.fillRect(0, int(height * 0.65), width, int(height * 0.35), accent)

    painter.setPen(QPen(SPLASH_ACCENT, 2))
    painter.drawRoundedRect(20, 20, width - 40, height - 40, 22, 22)

    _draw_logo(painter, QRectF(728, 114, 195, 235))

    painter.setPen(SPLASH_ACCENT)
    painter.setFont(QFont("DejaVu Sans", 18, QFont.Bold))
    painter.drawText(55, 95, "PNG2VLSI PIXEL")

    painter.setPen(SPLASH_TEXT)
    painter.setFont(QFont("DejaVu Sans", 45, QFont.Black))
    painter.drawText(55, 170, "Raster to Layout")
    painter.drawText(55, 235, "Conversion Studio")

    painter.setPen(SPLASH_MUTED)
    painter.setFont(QFont("DejaVu Sans", 15))
    painter.drawText(58, 300, "pixelation · cleanup · scaling · gds/svg/dxf export")

    painter.setPen(QColor("#EEF5FF"))
    painter.setFont(QFont("DejaVu Sans", 11))
    painter.drawText(width - 310, height - 70, "PySide6 · Linux Desktop")
    painter.drawText(width - 310, height - 45, "Layout-oriented image tooling")

    painter.end()
    return pixmap


class StartupSplash(QSplashScreen):
    """Splash with bottom-right progress messages."""

    def __init__(self) -> None:
        super().__init__(build_splash_pixmap())
        self.setWindowFlag(Qt.WindowStaysOnTopHint)

    def update_step(self, message: str) -> None:
        self.showMessage(
            message,
            alignment=Qt.AlignBottom | Qt.AlignRight,
            color=SPLASH_PROGRESS,
        )
