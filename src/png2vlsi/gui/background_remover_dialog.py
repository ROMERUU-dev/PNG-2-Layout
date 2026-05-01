from __future__ import annotations

from pathlib import Path
import tempfile

import numpy as np
from PIL import Image
from PySide6.QtCore import QPoint, Qt, Signal
from PySide6.QtGui import QImage, QMouseEvent, QPixmap
from PySide6.QtWidgets import (
    QDialog,
    QDoubleSpinBox,
    QFileDialog,
    QLabel,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
    QHBoxLayout,
)

from .translations import translate


class ClickableImageLabel(QLabel):
    image_clicked = Signal(int, int)

    def __init__(self) -> None:
        super().__init__()
        self._source_size: tuple[int, int] | None = None
        self._last_pixmap_size: tuple[int, int] | None = None
        self.setAlignment(Qt.AlignCenter)
        self.setMinimumSize(420, 320)
        self.setStyleSheet("background: #f8fbff; border: 1px solid #d0dceb; border-radius: 16px;")

    def set_preview(self, rgba: np.ndarray) -> None:
        rgba = np.ascontiguousarray(rgba)
        height, width, _ = rgba.shape
        image = QImage(rgba.data, width, height, rgba.strides[0], QImage.Format_RGBA8888)
        pixmap = QPixmap.fromImage(image.copy())
        scaled = pixmap.scaled(self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self._source_size = (width, height)
        self._last_pixmap_size = (scaled.width(), scaled.height())
        self.setPixmap(scaled)

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802
        if event.button() != Qt.LeftButton or self._source_size is None or self._last_pixmap_size is None:
            return
        width, height = self._source_size
        pixmap_width, pixmap_height = self._last_pixmap_size
        x_offset = (self.width() - pixmap_width) / 2
        y_offset = (self.height() - pixmap_height) / 2
        pos: QPoint = event.position().toPoint()
        x = pos.x() - x_offset
        y = pos.y() - y_offset
        if x < 0 or y < 0 or x > pixmap_width or y > pixmap_height:
            return
        source_x = min(width - 1, max(0, int(x * width / max(1, pixmap_width))))
        source_y = min(height - 1, max(0, int(y * height / max(1, pixmap_height))))
        self.image_clicked.emit(source_x, source_y)

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        if self.pixmap() is not None and self._source_size is not None:
            pass


class BackgroundRemoverDialog(QDialog):
    def __init__(self, image_path: str, language: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.language = language
        self.image_path = image_path
        self.original_rgba = np.array(Image.open(image_path).convert("RGBA"), dtype=np.uint8)
        self.working_rgba = self.original_rgba.copy()
        self.app_output_path: str | None = None

        self.setWindowTitle(translate(language, "dialog_background_tool"))
        self.resize(760, 720)

        layout = QVBoxLayout(self)
        self.hint_label = QLabel(translate(language, "background_hint"))
        self.hint_label.setWordWrap(True)
        layout.addWidget(self.hint_label)

        controls = QHBoxLayout()
        self.tolerance_label = QLabel(translate(language, "background_tolerance"))
        self.tolerance_spin = QDoubleSpinBox()
        self.tolerance_spin.setRange(0.0, 255.0)
        self.tolerance_spin.setDecimals(0)
        self.tolerance_spin.setSingleStep(5.0)
        self.tolerance_spin.setValue(28.0)
        self.alpha_gate_label = QLabel(translate(language, "field_background_alpha_threshold"))
        self.alpha_gate_spin = QSpinBox()
        self.alpha_gate_spin.setRange(0, 255)
        self.alpha_gate_spin.setValue(1)
        self.reset_button = QPushButton(translate(language, "background_reset"))
        self.save_button = QPushButton(translate(language, "background_save"))
        self.use_in_app_button = QPushButton(translate(language, "background_use_in_app"))
        self.reset_button.clicked.connect(self.reset_image)
        self.save_button.clicked.connect(self.save_image)
        self.use_in_app_button.clicked.connect(self.use_in_app)
        controls.addWidget(self.tolerance_label)
        controls.addWidget(self.tolerance_spin)
        controls.addWidget(self.alpha_gate_label)
        controls.addWidget(self.alpha_gate_spin)
        controls.addStretch(1)
        controls.addWidget(self.reset_button)
        controls.addWidget(self.save_button)
        controls.addWidget(self.use_in_app_button)
        layout.addLayout(controls)

        self.preview_label = ClickableImageLabel()
        self.preview_label.image_clicked.connect(self.erase_by_sample)
        layout.addWidget(self.preview_label, stretch=1)
        self._refresh_preview()

    def _refresh_preview(self) -> None:
        self.preview_label.set_preview(self.working_rgba)

    def reset_image(self) -> None:
        self.working_rgba = self.original_rgba.copy()
        self._refresh_preview()

    def erase_by_sample(self, x: int, y: int) -> None:
        sample = self.working_rgba[y, x]
        rgb = self.working_rgba[:, :, :3].astype(np.int16)
        target = sample[:3].astype(np.int16)
        tolerance = int(self.tolerance_spin.value())
        distance = np.max(np.abs(rgb - target), axis=2)
        mask = distance <= tolerance
        mask &= self.working_rgba[:, :, 3] >= int(self.alpha_gate_spin.value())
        self.working_rgba[mask, 3] = 0
        self._refresh_preview()

    def save_image(self) -> None:
        output_path, _ = QFileDialog.getSaveFileName(
            self,
            translate(self.language, "background_save"),
            f"{Path(self.image_path).stem}_background_removed.png",
            "PNG Files (*.png)",
        )
        if not output_path:
            return
        Image.fromarray(self.working_rgba, mode="RGBA").save(output_path)
        QMessageBox.information(
            self,
            translate(self.language, "dialog_background_tool"),
            translate(self.language, "dialog_saved", name=Path(output_path).name),
        )

    def use_in_app(self) -> None:
        temp_dir = Path(tempfile.gettempdir())
        output_path = temp_dir / f"{Path(self.image_path).stem}_background_removed_for_app.png"
        Image.fromarray(self.working_rgba, mode="RGBA").save(output_path)
        self.app_output_path = str(output_path)
        self.accept()
