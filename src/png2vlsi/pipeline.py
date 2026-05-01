from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import replace
import numpy as np

from .cleanup import GeometryCleanup, GridDrcCleanup
from .image_loader import ImageLoader
from .mask_generator import MaskGenerator
from .models import (
    LayerResult,
    LayerSettings,
    PipelineResult,
    PipelineSettings,
    drc_rule_for_logical_layer,
    gds_mapping_for_logical_layer,
)
from .pixelation import Pixelator
from .scaling import PhysicalScaler


class ConversionPipeline:
    def run(
        self,
        image_path: str,
        settings: PipelineSettings,
        progress_callback: Callable[[str, int | None], None] | None = None,
    ) -> PipelineResult:
        self._report(progress_callback, "Loading image...", 5)
        loaded = ImageLoader.load_png(image_path)
        self._report(progress_callback, "Preparing masks...", 15)
        layer_inputs = self._build_layer_inputs(loaded.rgba, loaded.alpha, settings)
        if not layer_inputs:
            empty_mask = np.zeros_like(loaded.alpha, dtype=bool)
            layer_inputs = [(empty_mask, settings.layer)]

        prepared_layers: list[tuple[np.ndarray, np.ndarray, np.ndarray, LayerSettings]] = []
        required_pixel_size_um = 0.0
        layer_count = max(1, len(layer_inputs))
        cleanup_settings = replace(settings.cleanup, trim_transparent_margins=False)
        for source_mask, layer in layer_inputs:
            cleaned_mask = GeometryCleanup.apply(source_mask, cleanup_settings)
            prepared_layers.append((source_mask, cleaned_mask, None, layer))
            required_pixel_size_um = max(
                required_pixel_size_um,
                self._minimum_pixel_size_for_layer(settings, layer.logical_name),
            )

        if settings.cleanup.trim_transparent_margins:
            self._report(progress_callback, "Applying shared crop window...", 20)
            union_mask = np.zeros_like(prepared_layers[0][1], dtype=bool)
            for _, cleaned_mask, _, _ in prepared_layers:
                union_mask |= cleaned_mask
            bounds = GeometryCleanup.trim_bounds(union_mask)
            prepared_layers = [
                (
                    GeometryCleanup.crop_to_bounds(source_mask, bounds),
                    GeometryCleanup.crop_to_bounds(cleaned_mask, bounds),
                    None,
                    layer,
                )
                for source_mask, cleaned_mask, _, layer in prepared_layers
            ]

        prepared_layers = [
            (
                source_mask,
                cleaned_mask,
                Pixelator.pixelate(cleaned_mask, settings.pixelation),
                layer,
            )
            for source_mask, cleaned_mask, _, layer in prepared_layers
        ]

        first_pixel_mask = prepared_layers[0][2]
        pixel_size_um = max(
            required_pixel_size_um,
            PhysicalScaler.resolve_pixel_size_um(
                grid_width=first_pixel_mask.shape[1],
                grid_height=first_pixel_mask.shape[0],
                settings=settings.scaling,
            ),
        )

        layer_results: list[LayerResult] = []
        combined_source_mask = prepared_layers[0][0].copy()
        combined_cleaned_mask = prepared_layers[0][1].copy()
        combined_pixel_mask = np.zeros_like(first_pixel_mask, dtype=bool)
        combined_grid_rectangles = []
        combined_physical_rectangles = []

        for index, (source_mask, cleaned_mask, layer_pixel_mask, layer) in enumerate(prepared_layers, start=1):
            progress = 25 + int(45 * index / layer_count)
            self._report(progress_callback, f"Processing {layer.logical_name} ({index}/{layer_count})...", progress)
            effective_drc = self._resolve_effective_drc(settings, layer.logical_name, pixel_size_um)
            pixel_mask = GridDrcCleanup.apply(layer_pixel_mask, effective_drc)
            grid_rectangles = Pixelator.mask_to_rectangles(pixel_mask, settings.pixelation.merge_rectangles)
            physical_rectangles = PhysicalScaler.scale_rectangles(
                grid_rectangles,
                pixel_size_um,
                grid_height=pixel_mask.shape[0],
            )
            layer_results.append(
                LayerResult(
                    layer=layer,
                    source_rgb=layer.preview_rgb,
                    source_mask=source_mask,
                    cleaned_mask=cleaned_mask,
                    pixel_mask=pixel_mask,
                    grid_rectangles=grid_rectangles,
                    physical_rectangles=physical_rectangles,
                    active_pixels=int(pixel_mask.sum()),
                    exported_rectangles=len(grid_rectangles),
                )
            )
            combined_source_mask |= source_mask
            combined_cleaned_mask |= cleaned_mask
            combined_pixel_mask |= pixel_mask
            combined_grid_rectangles.extend(grid_rectangles)
            combined_physical_rectangles.extend(physical_rectangles)

        self._report(progress_callback, "Finalizing preview data...", 85)
        final_width_um = combined_pixel_mask.shape[1] * pixel_size_um
        final_height_um = combined_pixel_mask.shape[0] * pixel_size_um

        self._report(progress_callback, "Preview ready.", 100)
        return PipelineResult(
            original_rgba=loaded.rgba,
            source_mask=combined_source_mask,
            cleaned_mask=combined_cleaned_mask,
            pixel_mask=combined_pixel_mask,
            grid_rectangles=combined_grid_rectangles,
            physical_rectangles=combined_physical_rectangles,
            pixel_size_um=pixel_size_um,
            final_width_um=final_width_um,
            final_height_um=final_height_um,
            active_pixels=int(combined_pixel_mask.sum()),
            exported_rectangles=len(combined_grid_rectangles),
            layer_results=layer_results,
        )

    def _build_layer_inputs(
        self,
        rgba,
        alpha,
        settings: PipelineSettings,
    ) -> list[tuple[np.ndarray, LayerSettings]]:
        if settings.color_quantization.mode != "solid_colors":
            source_mask = MaskGenerator.alpha_to_mask(alpha, settings.alpha_threshold)
            return [(source_mask, replace(settings.layer, preview_rgb=(255, 255, 255)))]

        selected_metals = settings.color_quantization.selected_metals or ["met1"]
        color_masks = MaskGenerator.rgba_to_color_masks(
            rgba=rgba,
            alpha=alpha,
            alpha_threshold=settings.alpha_threshold,
            color_count=len(selected_metals),
        )
        return [
            (
                mask,
                self._layer_for_selected_metal(selected_metals[index], color),
            )
            for index, (mask, color) in enumerate(color_masks)
        ]

    def _layer_for_selected_metal(self, logical_name: str, color: tuple[int, int, int]) -> LayerSettings:
        gds_layer, gds_datatype = gds_mapping_for_logical_layer(logical_name)
        return LayerSettings(
            logical_name=logical_name,
            gds_layer=gds_layer,
            gds_datatype=gds_datatype,
            preview_rgb=color,
        )

    def _minimum_pixel_size_for_layer(self, settings: PipelineSettings, logical_name: str) -> float:
        if not settings.drc.enabled:
            return 0.0
        rule = drc_rule_for_logical_layer(logical_name)
        if rule is None:
            return 0.0
        return rule.min_width_um

    def _resolve_effective_drc(self, settings: PipelineSettings, logical_name: str, pixel_size_um: float):
        if not settings.drc.enabled:
            return settings.drc

        rule = drc_rule_for_logical_layer(logical_name)
        if rule is None:
            return settings.drc

        minimum_width_cells = max(
            settings.drc.minimum_width_cells,
            math.ceil(rule.min_width_um / pixel_size_um),
        )
        minimum_spacing_cells = max(
            settings.drc.minimum_spacing_cells,
            math.ceil(rule.recommended_spacing_um / pixel_size_um),
        )
        return replace(
            settings.drc,
            minimum_width_cells=minimum_width_cells,
            minimum_spacing_cells=minimum_spacing_cells,
        )

    def _report(
        self,
        progress_callback: Callable[[str, int | None], None] | None,
        message: str,
        percent: int | None,
    ) -> None:
        if progress_callback is not None:
            progress_callback(message, percent)
