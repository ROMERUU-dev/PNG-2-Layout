from __future__ import annotations

import math
from dataclasses import replace

from .cleanup import GeometryCleanup, GridDrcCleanup
from .image_loader import ImageLoader
from .mask_generator import MaskGenerator
from .models import PipelineResult, PipelineSettings, drc_rule_for_logical_layer
from .pixelation import Pixelator
from .scaling import PhysicalScaler


class ConversionPipeline:
    def run(self, image_path: str, settings: PipelineSettings) -> PipelineResult:
        loaded = ImageLoader.load_png(image_path)
        source_mask = MaskGenerator.alpha_to_mask(loaded.alpha, settings.alpha_threshold)
        cleaned_mask = GeometryCleanup.apply(source_mask, settings.cleanup)
        pixel_mask = Pixelator.pixelate(cleaned_mask, settings.pixelation)

        pixel_size_um = PhysicalScaler.resolve_pixel_size_um(
            grid_width=pixel_mask.shape[1],
            grid_height=pixel_mask.shape[0],
            settings=settings.scaling,
        )
        effective_drc, pixel_size_um = self._resolve_effective_drc(settings, pixel_size_um)
        pixel_mask = GridDrcCleanup.apply(pixel_mask, effective_drc)
        grid_rectangles = Pixelator.mask_to_rectangles(pixel_mask, settings.pixelation.merge_rectangles)
        physical_rectangles = PhysicalScaler.scale_rectangles(
            grid_rectangles,
            pixel_size_um,
            grid_height=pixel_mask.shape[0],
        )
        final_width_um = pixel_mask.shape[1] * pixel_size_um
        final_height_um = pixel_mask.shape[0] * pixel_size_um

        return PipelineResult(
            original_rgba=loaded.rgba,
            source_mask=source_mask,
            cleaned_mask=cleaned_mask,
            pixel_mask=pixel_mask,
            grid_rectangles=grid_rectangles,
            physical_rectangles=physical_rectangles,
            pixel_size_um=pixel_size_um,
            final_width_um=final_width_um,
            final_height_um=final_height_um,
            active_pixels=int(pixel_mask.sum()),
            exported_rectangles=len(grid_rectangles),
        )

    def _resolve_effective_drc(self, settings: PipelineSettings, pixel_size_um: float):
        if not settings.drc.enabled:
            return settings.drc, pixel_size_um

        rule = drc_rule_for_logical_layer(settings.layer.logical_name)
        if rule is None:
            return settings.drc, pixel_size_um

        enforced_pixel_size_um = max(pixel_size_um, rule.min_width_um)
        minimum_width_cells = max(
            settings.drc.minimum_width_cells,
            math.ceil(rule.min_width_um / enforced_pixel_size_um),
        )
        minimum_spacing_cells = max(
            settings.drc.minimum_spacing_cells,
            math.ceil(rule.recommended_spacing_um / enforced_pixel_size_um),
        )
        return (
            replace(
                settings.drc,
                minimum_width_cells=minimum_width_cells,
                minimum_spacing_cells=minimum_spacing_cells,
            ),
            enforced_pixel_size_um,
        )
