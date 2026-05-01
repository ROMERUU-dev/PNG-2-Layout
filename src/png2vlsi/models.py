from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

import numpy as np
from PIL import Image


PixelationMode = Literal["rows_cols", "source_pixel_size"]
ScalingMode = Literal["pixel_size", "target_width", "target_height", "fit_box"]
ColorMode = Literal["alpha_mask", "solid_colors"]

DEFAULT_GDS_LAYER_MAP: dict[str, tuple[int, int]] = {
    "met1": (68, 20),
    "met2": (69, 20),
    "met3": (70, 20),
    "met4": (71, 20),
    "met5": (72, 20),
}


@dataclass(frozen=True)
class LayerDrcRule:
    min_width_um: float
    min_spacing_um: float
    recommended_spacing_um: float


DEFAULT_LAYER_DRC_RULES: dict[str, LayerDrcRule] = {
    "met1": LayerDrcRule(min_width_um=0.14, min_spacing_um=0.14, recommended_spacing_um=0.28),
    "met2": LayerDrcRule(min_width_um=0.14, min_spacing_um=0.14, recommended_spacing_um=0.28),
    "met3": LayerDrcRule(min_width_um=0.3, min_spacing_um=0.3, recommended_spacing_um=0.4),
    "met4": LayerDrcRule(min_width_um=0.3, min_spacing_um=0.3, recommended_spacing_um=0.4),
}


@dataclass(frozen=True)
class Rectangle:
    x: int
    y: int
    width: int
    height: int


@dataclass(frozen=True)
class PhysicalRectangle:
    x_um: float
    y_um: float
    width_um: float
    height_um: float


@dataclass
class LoadedImage:
    path: Path
    pil_image: Image.Image
    rgba: np.ndarray
    alpha: np.ndarray


@dataclass
class CleanupSettings:
    remove_islands_min_pixels: int = 0
    fill_holes_max_pixels: int = 0
    trim_transparent_margins: bool = True


@dataclass
class PixelationSettings:
    mode: PixelationMode = "rows_cols"
    rows: int = 96
    cols: int = 96
    source_pixel_size: int = 4
    activation_ratio: float = 0.5
    preserve_aspect_ratio: bool = True
    merge_rectangles: bool = True


@dataclass
class ScalingSettings:
    mode: ScalingMode = "fit_box"
    pixel_size_um: float = 1.0
    target_width_um: float = 30.0
    target_height_um: float = 30.0


@dataclass
class DrcSettings:
    enabled: bool = False
    orthogonal_cleanup_iterations: int = 1
    minimum_width_cells: int = 1
    minimum_spacing_cells: int = 1


@dataclass
class LayerSettings:
    logical_name: str = "met1"
    gds_layer: int = 68
    gds_datatype: int = 20
    preview_rgb: tuple[int, int, int] | None = None


@dataclass
class ColorQuantizationSettings:
    mode: ColorMode = "alpha_mask"
    selected_metals: list[str] = field(default_factory=lambda: ["met1", "met2", "met3", "met4"])


@dataclass
class PipelineSettings:
    alpha_threshold: int = 1
    color_quantization: ColorQuantizationSettings = field(default_factory=ColorQuantizationSettings)
    cleanup: CleanupSettings = field(default_factory=CleanupSettings)
    pixelation: PixelationSettings = field(default_factory=PixelationSettings)
    scaling: ScalingSettings = field(default_factory=ScalingSettings)
    drc: DrcSettings = field(default_factory=DrcSettings)
    layer: LayerSettings = field(default_factory=LayerSettings)


def default_pipeline_settings() -> PipelineSettings:
    """Create a fresh copy of the application's default processing settings."""
    return PipelineSettings()


def gds_mapping_for_logical_layer(logical_name: str) -> tuple[int, int]:
    return DEFAULT_GDS_LAYER_MAP.get(logical_name, DEFAULT_GDS_LAYER_MAP["met1"])


def drc_rule_for_logical_layer(logical_name: str) -> LayerDrcRule | None:
    return DEFAULT_LAYER_DRC_RULES.get(logical_name)


@dataclass
class LayerResult:
    layer: LayerSettings
    source_rgb: tuple[int, int, int] | None
    source_mask: np.ndarray
    cleaned_mask: np.ndarray
    pixel_mask: np.ndarray
    grid_rectangles: list[Rectangle]
    physical_rectangles: list[PhysicalRectangle]
    active_pixels: int
    exported_rectangles: int


@dataclass
class PipelineResult:
    original_rgba: np.ndarray
    source_mask: np.ndarray
    cleaned_mask: np.ndarray
    pixel_mask: np.ndarray
    grid_rectangles: list[Rectangle]
    physical_rectangles: list[PhysicalRectangle]
    pixel_size_um: float
    final_width_um: float
    final_height_um: float
    active_pixels: int
    exported_rectangles: int
    layer_results: list[LayerResult]
