from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image
from PySide6.QtCore import QLocale, QSettings, Qt
from PySide6.QtCore import QSignalBlocker
from PySide6.QtGui import QAction, QImage, QPixmap
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from ..exporters.dxf_exporter import DxfExporter
from ..desktop_integration import install_launcher_entries
from ..exporters.gds_exporter import GdsExporter
from ..exporters.svg_exporter import SvgExporter
from ..geometry import GeometryUtils
from .preferences_dialog import PreferencesDialog
from .translations import translate
from ..models import (
    CleanupSettings,
    DrcSettings,
    LayerSettings,
    PipelineResult,
    PipelineSettings,
    PixelationSettings,
    ScalingSettings,
    default_pipeline_settings,
    gds_mapping_for_logical_layer,
)
from ..pipeline import ConversionPipeline


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.settings_store = QSettings()
        self.language = self._detect_default_language()
        self._load_preferences()

        self.setWindowTitle(self._text("app_title"))
        self.resize(1240, 760)

        self.pipeline = ConversionPipeline()
        self.default_settings = default_pipeline_settings()
        self.current_image_path: str | None = None
        self.current_image_size: tuple[int, int] | None = None
        self.current_result: PipelineResult | None = None
        self.preview_dirty = False

        self.original_preview = QLabel(self._text("text_original_preview"))
        self.pixel_preview = QLabel(self._text("text_pixelated_preview"))
        self.stats_label = QLabel(self._text("status_load_png"))

        self._setup_preview_label(self.original_preview)
        self._setup_preview_label(self.pixel_preview)

        central = QWidget()
        self.setCentralWidget(central)

        main_layout = QVBoxLayout(central)
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)

        controls_container = QWidget()
        controls_layout = QVBoxLayout(controls_container)
        controls_layout.setContentsMargins(12, 12, 12, 12)

        controls_scroll = QScrollArea()
        controls_scroll.setWidgetResizable(True)
        controls_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        controls_scroll.setWidget(controls_container)

        previews_container = QWidget()
        previews_layout = QVBoxLayout(previews_container)
        previews_layout.setContentsMargins(12, 12, 12, 12)

        splitter.addWidget(controls_scroll)
        splitter.addWidget(previews_container)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([360, 860])

        self.input_group = self._build_file_group()
        self.mask_group = self._build_mask_group()
        self.pixelation_group = self._build_pixelation_group()
        self.cleanup_group = self._build_cleanup_group()
        self.drc_group = self._build_drc_group()
        self.scaling_group = self._build_scaling_group()
        self.layer_group = self._build_layer_group()
        self.export_group = self._build_export_group()

        controls_layout.addWidget(self.input_group)
        controls_layout.addWidget(self.mask_group)
        controls_layout.addWidget(self.pixelation_group)
        controls_layout.addWidget(self.cleanup_group)
        controls_layout.addWidget(self.drc_group)
        controls_layout.addWidget(self.scaling_group)
        controls_layout.addWidget(self.layer_group)
        controls_layout.addWidget(self.export_group)
        controls_layout.addStretch(1)
        controls_layout.addWidget(self.stats_label)

        self.original_title_label = QLabel()
        self.pixel_title_label = QLabel()
        previews_layout.addWidget(self.original_title_label)
        previews_layout.addWidget(self.original_preview, stretch=1)
        previews_layout.addWidget(self.pixel_title_label)
        previews_layout.addWidget(self.pixel_preview, stretch=1)

        self._create_menu()
        self._retranslate_ui()
        self._set_controls_enabled(False)
        self._load_sample_if_available()

    def _text(self, key: str, **kwargs: str) -> str:
        return translate(self.language, key, **kwargs)

    def _detect_default_language(self) -> str:
        language = str(self.settings_store.value("ui/language", "")).strip()
        if language in {"en", "es"}:
            return language
        return "es" if QLocale.system().name().lower().startswith("es") else "en"

    def _load_preferences(self) -> None:
        return None

    def _save_preferences(self) -> None:
        self.settings_store.setValue("ui/language", self.language)

    def _create_menu(self) -> None:
        self.file_menu = self.menuBar().addMenu("")
        self.tools_menu = self.menuBar().addMenu("")
        self.help_menu = self.menuBar().addMenu("")

        self.load_action = QAction(self)
        self.load_action.triggered.connect(self.load_png)
        self.preferences_action = QAction(self)
        self.preferences_action.triggered.connect(self.open_preferences_dialog)
        self.install_launcher_action = QAction(self)
        self.install_launcher_action.triggered.connect(self.install_launcher)
        self.exit_action = QAction(self)
        self.exit_action.triggered.connect(self.close)
        self.about_action = QAction(self)
        self.about_action.triggered.connect(self.show_about_dialog)

        self.file_menu.addAction(self.load_action)
        self.file_menu.addSeparator()
        self.file_menu.addAction(self.exit_action)
        self.tools_menu.addAction(self.preferences_action)
        self.tools_menu.addAction(self.install_launcher_action)
        self.help_menu.addAction(self.about_action)

    def _retranslate_ui(self) -> None:
        self.setWindowTitle(self._text("app_title"))
        self.file_menu.setTitle(self._text("menu_file"))
        self.tools_menu.setTitle(self._text("menu_tools"))
        self.help_menu.setTitle(self._text("menu_help"))
        self.load_action.setText(self._text("action_load_png"))
        self.preferences_action.setText(self._text("action_preferences"))
        self.install_launcher_action.setText(self._text("action_install_launcher"))
        self.exit_action.setText(self._text("action_exit"))
        self.about_action.setText(self._text("action_about"))

        self.input_group.setTitle(self._text("group_input"))
        self.mask_group.setTitle(self._text("group_alpha_mask"))
        self.pixelation_group.setTitle(self._text("group_pixelation"))
        self.cleanup_group.setTitle(self._text("group_cleanup"))
        self.drc_group.setTitle(self._text("group_drc_cleanup"))
        self.scaling_group.setTitle(self._text("group_physical_scaling"))
        self.layer_group.setTitle(self._text("group_layer"))
        self.export_group.setTitle(self._text("group_export"))

        self.original_title_label.setText(self._text("label_original_image"))
        self.pixel_title_label.setText(self._text("label_orthogonal_pixel_layout"))
        self.original_preview.setText(self._text("text_original_preview"))
        self.pixel_preview.setText(self._text("text_pixelated_preview"))

        self.load_button.setText(self._text("button_load_png"))
        self.apply_button.setText(self._text("button_update_preview"))
        self.reset_button.setText(self._text("button_reset_defaults"))
        self.export_svg_button.setText(self._text("button_export_svg"))
        self.export_dxf_button.setText(self._text("button_export_dxf"))
        self.export_gds_button.setText(self._text("button_export_gds"))
        if not self.current_image_path:
            self.loaded_path_label.setText(self._text("text_no_file_selected"))
        if not self.current_image_path and self.current_result is None:
            self.stats_label.setText(self._text("status_load_png"))

        self._retranslate_form_labels()
        self._retranslate_combo_items()

    def _retranslate_form_labels(self) -> None:
        self.mask_layout.labelForField(self.alpha_threshold).setText(self._text("field_alpha_threshold"))
        self.pixelation_layout.labelForField(self.pixel_mode).setText(self._text("field_mode"))
        self.pixelation_layout.labelForField(self.rows_spin).setText(self._text("field_rows"))
        self.pixelation_layout.labelForField(self.cols_spin).setText(self._text("field_columns"))
        self.pixelation_layout.labelForField(self.source_pixel_size).setText(self._text("field_source_pixel_size"))
        self.pixelation_layout.labelForField(self.activation_ratio).setText(self._text("field_activation_ratio"))
        self.cleanup_layout.labelForField(self.remove_islands).setText(self._text("field_remove_islands"))
        self.cleanup_layout.labelForField(self.fill_holes).setText(self._text("field_fill_holes"))
        self.drc_layout.labelForField(self.drc_iterations).setText(self._text("field_cleanup_passes"))
        self.drc_layout.labelForField(self.min_width_cells).setText(self._text("field_minimum_width"))
        self.drc_layout.labelForField(self.min_spacing_cells).setText(self._text("field_minimum_spacing"))
        self.scaling_layout.labelForField(self.scaling_mode).setText(self._text("field_scaling_mode"))
        self.scaling_layout.labelForField(self.pixel_size_um).setText(self._text("field_pixel_size"))
        self.scaling_layout.labelForField(self.target_width_um).setText(self._text("field_target_width"))
        self.scaling_layout.labelForField(self.target_height_um).setText(self._text("field_target_height"))
        self.layer_layout.labelForField(self.layer_name).setText(self._text("field_logical_layer"))
        self.layer_layout.labelForField(self.gds_layer).setText(self._text("field_gds_layer"))
        self.layer_layout.labelForField(self.gds_datatype).setText(self._text("field_gds_datatype"))

    def _retranslate_combo_items(self) -> None:
        self.pixel_mode.setItemText(0, self._text("option_rows_columns"))
        self.pixel_mode.setItemText(1, self._text("option_source_pixel_size"))
        self.scaling_mode.setItemText(0, self._text("option_pixel_size"))
        self.scaling_mode.setItemText(1, self._text("option_target_width"))
        self.scaling_mode.setItemText(2, self._text("option_target_height"))
        self.scaling_mode.setItemText(3, self._text("option_fit_inside_box"))
        self.preserve_aspect_ratio.setText(self._text("checkbox_lock_aspect_ratio"))
        self.merge_rectangles.setText(self._text("checkbox_merge_adjacent_cells"))
        self.trim_margins.setText(self._text("checkbox_trim_transparent_margins"))
        self.drc_enabled.setText(self._text("checkbox_enable_manhattan_cleanup"))

    def _build_file_group(self) -> QGroupBox:
        group = QGroupBox(self._text("group_input"))
        layout = QVBoxLayout(group)
        self.load_button = QPushButton(self._text("button_load_png"))
        self.load_button.clicked.connect(self.load_png)
        self.apply_button = QPushButton(self._text("button_update_preview"))
        self.apply_button.clicked.connect(self.refresh_pipeline)
        self.reset_button = QPushButton(self._text("button_reset_defaults"))
        self.reset_button.clicked.connect(self.reset_to_defaults)
        self.loaded_path_label = QLabel(self._text("text_no_file_selected"))
        self.loaded_path_label.setWordWrap(True)
        layout.addWidget(self.load_button)
        layout.addWidget(self.apply_button)
        layout.addWidget(self.reset_button)
        layout.addWidget(self.loaded_path_label)
        return group

    def _build_mask_group(self) -> QGroupBox:
        group = QGroupBox(self._text("group_alpha_mask"))
        layout = QFormLayout(group)
        self.mask_layout = layout
        self.alpha_threshold = QSpinBox()
        self.alpha_threshold.setRange(0, 255)
        self.alpha_threshold.setValue(self.default_settings.alpha_threshold)
        self.alpha_threshold.setSuffix(" alpha")
        self.alpha_threshold.valueChanged.connect(self.mark_preview_dirty)
        layout.addRow(self._text("field_alpha_threshold"), self.alpha_threshold)
        return group

    def _build_pixelation_group(self) -> QGroupBox:
        group = QGroupBox(self._text("group_pixelation"))
        layout = QFormLayout(group)
        self.pixelation_layout = layout

        self.pixel_mode = QComboBox()
        self.pixel_mode.addItem(self._text("option_rows_columns"), "rows_cols")
        self.pixel_mode.addItem(self._text("option_source_pixel_size"), "source_pixel_size")
        self.pixel_mode.currentIndexChanged.connect(self._on_mode_changed)

        self.rows_spin = QSpinBox()
        self.rows_spin.setRange(1, 2048)
        self.rows_spin.setValue(self.default_settings.pixelation.rows)
        self.rows_spin.setSuffix(" rows")
        self.rows_spin.valueChanged.connect(self._on_rows_changed)

        self.cols_spin = QSpinBox()
        self.cols_spin.setRange(1, 2048)
        self.cols_spin.setValue(self.default_settings.pixelation.cols)
        self.cols_spin.setSuffix(" cols")
        self.cols_spin.valueChanged.connect(self.mark_preview_dirty)

        self.preserve_aspect_ratio = QCheckBox(self._text("checkbox_lock_aspect_ratio"))
        self.preserve_aspect_ratio.setChecked(self.default_settings.pixelation.preserve_aspect_ratio)
        self.preserve_aspect_ratio.stateChanged.connect(self._on_aspect_ratio_toggled)

        self.source_pixel_size = QSpinBox()
        self.source_pixel_size.setRange(1, 1024)
        self.source_pixel_size.setValue(self.default_settings.pixelation.source_pixel_size)
        self.source_pixel_size.setSuffix(" px")
        self.source_pixel_size.valueChanged.connect(self.mark_preview_dirty)

        self.activation_ratio = QDoubleSpinBox()
        self.activation_ratio.setRange(0.01, 1.0)
        self.activation_ratio.setSingleStep(0.05)
        self.activation_ratio.setValue(self.default_settings.pixelation.activation_ratio)
        self.activation_ratio.setDecimals(2)
        self.activation_ratio.valueChanged.connect(self.mark_preview_dirty)

        self.merge_rectangles = QCheckBox(self._text("checkbox_merge_adjacent_cells"))
        self.merge_rectangles.setChecked(self.default_settings.pixelation.merge_rectangles)
        self.merge_rectangles.stateChanged.connect(self.mark_preview_dirty)

        layout.addRow(self._text("field_mode"), self.pixel_mode)
        layout.addRow(self._text("field_rows"), self.rows_spin)
        layout.addRow(self._text("field_columns"), self.cols_spin)
        layout.addRow("", self.preserve_aspect_ratio)
        layout.addRow(self._text("field_source_pixel_size"), self.source_pixel_size)
        layout.addRow(self._text("field_activation_ratio"), self.activation_ratio)
        layout.addRow("", self.merge_rectangles)
        self._on_mode_changed()
        return group

    def _build_cleanup_group(self) -> QGroupBox:
        group = QGroupBox(self._text("group_cleanup"))
        layout = QFormLayout(group)
        self.cleanup_layout = layout

        self.remove_islands = QSpinBox()
        self.remove_islands.setRange(0, 100000)
        self.remove_islands.setValue(self.default_settings.cleanup.remove_islands_min_pixels)
        self.remove_islands.setSuffix(" px")
        self.remove_islands.valueChanged.connect(self.mark_preview_dirty)

        self.fill_holes = QSpinBox()
        self.fill_holes.setRange(0, 100000)
        self.fill_holes.setValue(self.default_settings.cleanup.fill_holes_max_pixels)
        self.fill_holes.setSuffix(" px")
        self.fill_holes.valueChanged.connect(self.mark_preview_dirty)

        self.trim_margins = QCheckBox(self._text("checkbox_trim_transparent_margins"))
        self.trim_margins.setChecked(self.default_settings.cleanup.trim_transparent_margins)
        self.trim_margins.stateChanged.connect(self.mark_preview_dirty)

        layout.addRow(self._text("field_remove_islands"), self.remove_islands)
        layout.addRow(self._text("field_fill_holes"), self.fill_holes)
        layout.addRow("", self.trim_margins)
        return group

    def _build_drc_group(self) -> QGroupBox:
        group = QGroupBox(self._text("group_drc_cleanup"))
        layout = QFormLayout(group)
        self.drc_layout = layout

        self.drc_enabled = QCheckBox(self._text("checkbox_enable_manhattan_cleanup"))
        self.drc_enabled.setChecked(self.default_settings.drc.enabled)
        self.drc_enabled.stateChanged.connect(self._on_drc_toggled)

        self.drc_iterations = QSpinBox()
        self.drc_iterations.setRange(0, 8)
        self.drc_iterations.setValue(self.default_settings.drc.orthogonal_cleanup_iterations)
        self.drc_iterations.setSuffix(" passes")
        self.drc_iterations.valueChanged.connect(self.mark_preview_dirty)

        self.min_width_cells = QSpinBox()
        self.min_width_cells.setRange(1, 128)
        self.min_width_cells.setValue(self.default_settings.drc.minimum_width_cells)
        self.min_width_cells.setSuffix(" cells")
        self.min_width_cells.valueChanged.connect(self.mark_preview_dirty)

        self.min_spacing_cells = QSpinBox()
        self.min_spacing_cells.setRange(1, 128)
        self.min_spacing_cells.setValue(self.default_settings.drc.minimum_spacing_cells)
        self.min_spacing_cells.setSuffix(" cells")
        self.min_spacing_cells.valueChanged.connect(self.mark_preview_dirty)

        layout.addRow("", self.drc_enabled)
        layout.addRow(self._text("field_cleanup_passes"), self.drc_iterations)
        layout.addRow(self._text("field_minimum_width"), self.min_width_cells)
        layout.addRow(self._text("field_minimum_spacing"), self.min_spacing_cells)

        self._on_drc_toggled()
        return group

    def _build_scaling_group(self) -> QGroupBox:
        group = QGroupBox(self._text("group_physical_scaling"))
        layout = QFormLayout(group)
        self.scaling_layout = layout

        self.scaling_mode = QComboBox()
        self.scaling_mode.addItem(self._text("option_pixel_size"), "pixel_size")
        self.scaling_mode.addItem(self._text("option_target_width"), "target_width")
        self.scaling_mode.addItem(self._text("option_target_height"), "target_height")
        self.scaling_mode.addItem(self._text("option_fit_inside_box"), "fit_box")
        self.scaling_mode.currentIndexChanged.connect(self._on_scaling_mode_changed)

        self.pixel_size_um = QDoubleSpinBox()
        self.pixel_size_um.setRange(0.001, 1_000_000.0)
        self.pixel_size_um.setDecimals(6)
        self.pixel_size_um.setValue(self.default_settings.scaling.pixel_size_um)
        self.pixel_size_um.setSuffix(" um")
        self.pixel_size_um.valueChanged.connect(self.mark_preview_dirty)

        self.target_width_um = QDoubleSpinBox()
        self.target_width_um.setRange(0.001, 1_000_000.0)
        self.target_width_um.setDecimals(6)
        self.target_width_um.setValue(self.default_settings.scaling.target_width_um)
        self.target_width_um.setSuffix(" um")
        self.target_width_um.valueChanged.connect(self.mark_preview_dirty)

        self.target_height_um = QDoubleSpinBox()
        self.target_height_um.setRange(0.001, 1_000_000.0)
        self.target_height_um.setDecimals(6)
        self.target_height_um.setValue(self.default_settings.scaling.target_height_um)
        self.target_height_um.setSuffix(" um")
        self.target_height_um.valueChanged.connect(self.mark_preview_dirty)

        layout.addRow(self._text("field_scaling_mode"), self.scaling_mode)
        layout.addRow(self._text("field_pixel_size"), self.pixel_size_um)
        layout.addRow(self._text("field_target_width"), self.target_width_um)
        layout.addRow(self._text("field_target_height"), self.target_height_um)
        self._on_scaling_mode_changed()
        return group

    def _build_layer_group(self) -> QGroupBox:
        group = QGroupBox(self._text("group_layer"))
        layout = QFormLayout(group)
        self.layer_layout = layout

        self.layer_name = QComboBox()
        self.layer_name.addItems(["met1", "met2", "met3", "met4"])
        self.layer_name.setCurrentText(self.default_settings.layer.logical_name)
        self.layer_name.currentIndexChanged.connect(self._on_layer_name_changed)

        self.gds_layer = QSpinBox()
        self.gds_layer.setRange(0, 65535)
        self.gds_layer.setValue(self.default_settings.layer.gds_layer)
        self.gds_layer.setPrefix("L")
        self.gds_layer.valueChanged.connect(self.mark_preview_dirty)

        self.gds_datatype = QSpinBox()
        self.gds_datatype.setRange(0, 65535)
        self.gds_datatype.setValue(self.default_settings.layer.gds_datatype)
        self.gds_datatype.setPrefix("D")
        self.gds_datatype.valueChanged.connect(self.mark_preview_dirty)

        layout.addRow(self._text("field_logical_layer"), self.layer_name)
        layout.addRow(self._text("field_gds_layer"), self.gds_layer)
        layout.addRow(self._text("field_gds_datatype"), self.gds_datatype)
        self._sync_gds_mapping_for_layer(mark_dirty=False)
        return group

    def _build_export_group(self) -> QGroupBox:
        group = QGroupBox(self._text("group_export"))
        layout = QGridLayout(group)

        self.export_svg_button = QPushButton(self._text("button_export_svg"))
        self.export_dxf_button = QPushButton(self._text("button_export_dxf"))
        self.export_gds_button = QPushButton(self._text("button_export_gds"))

        self.export_svg_button.clicked.connect(lambda: self.export_file("svg"))
        self.export_dxf_button.clicked.connect(lambda: self.export_file("dxf"))
        self.export_gds_button.clicked.connect(lambda: self.export_file("gds"))

        layout.addWidget(self.export_svg_button, 0, 0)
        layout.addWidget(self.export_dxf_button, 0, 1)
        layout.addWidget(self.export_gds_button, 1, 0, 1, 2)
        return group

    def _set_controls_enabled(self, enabled: bool) -> None:
        for widget in (
            self.alpha_threshold,
            self.pixel_mode,
            self.rows_spin,
            self.cols_spin,
            self.preserve_aspect_ratio,
            self.source_pixel_size,
            self.activation_ratio,
            self.merge_rectangles,
            self.remove_islands,
            self.fill_holes,
            self.trim_margins,
            self.drc_enabled,
            self.drc_iterations,
            self.min_width_cells,
            self.min_spacing_cells,
            self.scaling_mode,
            self.pixel_size_um,
            self.target_width_um,
            self.target_height_um,
            self.layer_name,
            self.gds_layer,
            self.gds_datatype,
            self.apply_button,
            self.export_svg_button,
            self.export_dxf_button,
            self.export_gds_button,
        ):
            widget.setEnabled(enabled)

    def _setup_preview_label(self, label: QLabel) -> None:
        label.setAlignment(Qt.AlignCenter)
        label.setMinimumSize(420, 320)
        label.setStyleSheet("background-color: #1e1e1e; color: #dcdcdc; border: 1px solid #555;")

    def _load_sample_if_available(self) -> None:
        sample = Path(__file__).resolve().parents[3] / "sample_data" / "ardilla.png"
        if sample.exists():
            self.current_image_path = str(sample)
            self._update_current_image_size()
            self.loaded_path_label.setText(str(sample))
            self._set_controls_enabled(True)
            self._on_mode_changed()
            self._on_scaling_mode_changed()
            self.refresh_pipeline()

    def _on_mode_changed(self) -> None:
        mode = self.pixel_mode.currentData()
        by_grid = mode == "rows_cols"
        self.rows_spin.setEnabled(by_grid and self.current_image_path is not None)
        self.preserve_aspect_ratio.setEnabled(by_grid and self.current_image_path is not None)
        self.cols_spin.setEnabled(
            by_grid
            and not self.preserve_aspect_ratio.isChecked()
            and self.current_image_path is not None
        )
        self.source_pixel_size.setEnabled((not by_grid) and self.current_image_path is not None)
        self._sync_cols_for_aspect_ratio()
        self.mark_preview_dirty()

    def _on_rows_changed(self) -> None:
        self._sync_cols_for_aspect_ratio()
        self.mark_preview_dirty()

    def _on_aspect_ratio_toggled(self) -> None:
        self._on_mode_changed()

    def _on_layer_name_changed(self) -> None:
        self._sync_gds_mapping_for_layer(mark_dirty=True)

    def _on_scaling_mode_changed(self) -> None:
        mode = self.scaling_mode.currentData()
        self.pixel_size_um.setEnabled(mode == "pixel_size" and self.current_image_path is not None)
        self.target_width_um.setEnabled(mode in {"target_width", "fit_box"} and self.current_image_path is not None)
        self.target_height_um.setEnabled(mode in {"target_height", "fit_box"} and self.current_image_path is not None)
        self.mark_preview_dirty()

    def _on_drc_toggled(self) -> None:
        enabled = self.drc_enabled.isChecked() and self.current_image_path is not None
        self.drc_iterations.setEnabled(enabled)
        self.min_width_cells.setEnabled(enabled)
        self.min_spacing_cells.setEnabled(enabled)
        self.mark_preview_dirty()

    def load_png(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, self._text("action_load_png"), "", "PNG Images (*.png)")
        if not path:
            return
        self.current_image_path = path
        self._update_current_image_size()
        self.loaded_path_label.setText(path)
        self._set_controls_enabled(True)
        self._on_mode_changed()
        self._on_scaling_mode_changed()
        self.refresh_pipeline()

    def mark_preview_dirty(self) -> None:
        self.preview_dirty = True
        if self.current_image_path:
            self.stats_label.setText(self._text("status_settings_changed"))
        else:
            self.stats_label.setText(self._text("status_defaults_updated"))

    def build_settings(self) -> PipelineSettings:
        return PipelineSettings(
            alpha_threshold=self.alpha_threshold.value(),
            cleanup=CleanupSettings(
                remove_islands_min_pixels=self.remove_islands.value(),
                fill_holes_max_pixels=self.fill_holes.value(),
                trim_transparent_margins=self.trim_margins.isChecked(),
            ),
            pixelation=PixelationSettings(
                mode=self.pixel_mode.currentData(),
                rows=self.rows_spin.value(),
                cols=self.cols_spin.value(),
                source_pixel_size=self.source_pixel_size.value(),
                activation_ratio=self.activation_ratio.value(),
                preserve_aspect_ratio=self.preserve_aspect_ratio.isChecked(),
                merge_rectangles=self.merge_rectangles.isChecked(),
            ),
            scaling=ScalingSettings(
                mode=self.scaling_mode.currentData(),
                pixel_size_um=self.pixel_size_um.value(),
                target_width_um=self.target_width_um.value(),
                target_height_um=self.target_height_um.value(),
            ),
            drc=DrcSettings(
                enabled=self.drc_enabled.isChecked(),
                orthogonal_cleanup_iterations=self.drc_iterations.value(),
                minimum_width_cells=self.min_width_cells.value(),
                minimum_spacing_cells=self.min_spacing_cells.value(),
            ),
            layer=LayerSettings(
                logical_name=self.layer_name.currentText(),
                gds_layer=self.gds_layer.value(),
                gds_datatype=self.gds_datatype.value(),
            ),
        )

    def reset_to_defaults(self) -> None:
        defaults = default_pipeline_settings()
        widgets = [
            self.alpha_threshold,
            self.pixel_mode,
            self.rows_spin,
            self.cols_spin,
            self.preserve_aspect_ratio,
            self.source_pixel_size,
            self.activation_ratio,
            self.merge_rectangles,
            self.remove_islands,
            self.fill_holes,
            self.trim_margins,
            self.drc_enabled,
            self.drc_iterations,
            self.min_width_cells,
            self.min_spacing_cells,
            self.scaling_mode,
            self.pixel_size_um,
            self.target_width_um,
            self.target_height_um,
            self.layer_name,
            self.gds_layer,
            self.gds_datatype,
        ]
        blockers = [QSignalBlocker(widget) for widget in widgets]

        self.alpha_threshold.setValue(defaults.alpha_threshold)

        self.pixel_mode.setCurrentIndex(self.pixel_mode.findData(defaults.pixelation.mode))
        self.rows_spin.setValue(defaults.pixelation.rows)
        self.cols_spin.setValue(defaults.pixelation.cols)
        self.source_pixel_size.setValue(defaults.pixelation.source_pixel_size)
        self.activation_ratio.setValue(defaults.pixelation.activation_ratio)
        self.preserve_aspect_ratio.setChecked(defaults.pixelation.preserve_aspect_ratio)
        self.merge_rectangles.setChecked(defaults.pixelation.merge_rectangles)

        self.remove_islands.setValue(defaults.cleanup.remove_islands_min_pixels)
        self.fill_holes.setValue(defaults.cleanup.fill_holes_max_pixels)
        self.trim_margins.setChecked(defaults.cleanup.trim_transparent_margins)

        self.drc_enabled.setChecked(defaults.drc.enabled)
        self.drc_iterations.setValue(defaults.drc.orthogonal_cleanup_iterations)
        self.min_width_cells.setValue(defaults.drc.minimum_width_cells)
        self.min_spacing_cells.setValue(defaults.drc.minimum_spacing_cells)

        self.scaling_mode.setCurrentIndex(self.scaling_mode.findData(defaults.scaling.mode))
        self.pixel_size_um.setValue(defaults.scaling.pixel_size_um)
        self.target_width_um.setValue(defaults.scaling.target_width_um)
        self.target_height_um.setValue(defaults.scaling.target_height_um)

        self.layer_name.setCurrentText(defaults.layer.logical_name)
        self.gds_layer.setValue(defaults.layer.gds_layer)
        self.gds_datatype.setValue(defaults.layer.gds_datatype)

        del blockers
        self._sync_gds_mapping_for_layer(mark_dirty=False)
        self._on_mode_changed()
        self._on_drc_toggled()
        self._on_scaling_mode_changed()
        if self.current_image_path:
            self.refresh_pipeline()
        else:
            self.current_result = None
            self.preview_dirty = False
            self.stats_label.setText(self._text("status_defaults_restored"))

    def refresh_pipeline(self) -> None:
        if not self.current_image_path:
            return
        try:
            settings = self.build_settings()
            result = self.pipeline.run(self.current_image_path, settings)
        except Exception as exc:
            self.current_result = None
            self.stats_label.setText(f"Error: {exc}")
            return

        self.current_result = result
        self.preview_dirty = False
        self._set_pixmap(self.original_preview, result.original_rgba)
        self._set_pixmap(self.pixel_preview, GeometryUtils.mask_to_preview(result.pixel_mask))
        self.stats_label.setText(
            "\n".join(
                [
                    f"Final width: {result.final_width_um:.6f} um",
                    f"Final height: {result.final_height_um:.6f} um",
                    f"Pixel size: {result.pixel_size_um:.6f} um",
                    f"Active pixels: {result.active_pixels}",
                    f"Exported rectangles: {result.exported_rectangles}",
                    f"DRC cleanup: {'on' if settings.drc.enabled else 'off'}",
                    f"Grid: {result.pixel_mask.shape[1]} cols x {result.pixel_mask.shape[0]} rows",
                ]
            )
        )

    def export_file(self, export_type: str) -> None:
        if self.preview_dirty and self.current_image_path:
            self.refresh_pipeline()
        if not self.current_result:
            return

        suffix = export_type
        path, _ = QFileDialog.getSaveFileName(
            self,
            f"Export {export_type.upper()}",
            f"layout.{suffix}",
            f"{export_type.upper()} Files (*.{suffix})",
        )
        if not path:
            return

        layer = self.build_settings().layer
        try:
            if export_type == "svg":
                SvgExporter.export(
                    rectangles=self.current_result.physical_rectangles,
                    width_um=self.current_result.final_width_um,
                    height_um=self.current_result.final_height_um,
                    layer=layer,
                    output_path=path,
                )
            elif export_type == "dxf":
                DxfExporter.export(self.current_result.physical_rectangles, layer, path)
            elif export_type == "gds":
                GdsExporter.export(self.current_result.physical_rectangles, layer, path)
            else:
                raise ValueError(f"Unsupported export type: {export_type}")
        except Exception as exc:
            QMessageBox.critical(self, self._text("dialog_export_failed"), str(exc))
            return

        QMessageBox.information(
            self,
            self._text("dialog_export_complete"),
            self._text("dialog_saved", name=Path(path).name),
        )

    def _set_pixmap(self, label: QLabel, rgba: np.ndarray) -> None:
        rgba = np.ascontiguousarray(rgba)
        height, width, _ = rgba.shape
        image = QImage(rgba.data, width, height, rgba.strides[0], QImage.Format_RGBA8888)
        pixmap = QPixmap.fromImage(image.copy())
        label.setPixmap(
            pixmap.scaled(
                label.size(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation,
            )
        )

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        if self.current_result is None:
            return
        self._set_pixmap(self.original_preview, self.current_result.original_rgba)
        self._set_pixmap(self.pixel_preview, GeometryUtils.mask_to_preview(self.current_result.pixel_mask))

    def _update_current_image_size(self) -> None:
        if not self.current_image_path:
            self.current_image_size = None
            return
        with Image.open(self.current_image_path) as image:
            self.current_image_size = image.size

    def _sync_cols_for_aspect_ratio(self) -> None:
        if (
            self.pixel_mode.currentData() != "rows_cols"
            or not self.preserve_aspect_ratio.isChecked()
            or self.current_image_size is None
        ):
            return
        width, height = self.current_image_size
        cols = max(1, int(round(self.rows_spin.value() * width / max(1, height))))
        blocker = QSignalBlocker(self.cols_spin)
        self.cols_spin.setValue(cols)
        del blocker

    def _sync_gds_mapping_for_layer(self, mark_dirty: bool) -> None:
        gds_layer, gds_datatype = gds_mapping_for_logical_layer(self.layer_name.currentText())
        layer_blocker = QSignalBlocker(self.gds_layer)
        datatype_blocker = QSignalBlocker(self.gds_datatype)
        self.gds_layer.setValue(gds_layer)
        self.gds_datatype.setValue(gds_datatype)
        del layer_blocker
        del datatype_blocker
        if mark_dirty:
            self.mark_preview_dirty()

    def open_preferences_dialog(self) -> None:
        dialog = PreferencesDialog(self.language, self)
        dialog.install_button.clicked.connect(self.install_launcher)
        if dialog.exec():
            self.language = dialog.selected_language()
            self._save_preferences()
            self._retranslate_ui()
            if self.current_image_path:
                self.mark_preview_dirty()

    def install_launcher(self) -> None:
        try:
            installed_paths = install_launcher_entries()
        except Exception as exc:
            QMessageBox.critical(self, self._text("dialog_install_launcher_failure"), str(exc))
            return
        message = "\n".join(str(path) for path in installed_paths)
        QMessageBox.information(
            self,
            self._text("action_install_launcher"),
            f"{self._text('dialog_install_launcher_success')}\n\n{message}",
        )

    def show_about_dialog(self) -> None:
        QMessageBox.about(self, self._text("dialog_about"), self._text("about_body"))
