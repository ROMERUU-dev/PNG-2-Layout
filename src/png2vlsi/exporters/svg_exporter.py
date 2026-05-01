from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from ..models import LayerResult, LayerSettings, PhysicalRectangle


class SvgExporter:
    @staticmethod
    def export(
        rectangles: list[PhysicalRectangle],
        width_um: float,
        height_um: float,
        layer: LayerSettings,
        output_path: str | Path,
    ) -> None:
        SvgExporter.export_layers(
            layer_results=[
                LayerResult(
                    layer=layer,
                    source_rgb=layer.preview_rgb,
                    source_mask=None,
                    cleaned_mask=None,
                    pixel_mask=None,
                    grid_rectangles=[],
                    physical_rectangles=rectangles,
                    active_pixels=0,
                    exported_rectangles=len(rectangles),
                )
            ],
            width_um=width_um,
            height_um=height_um,
            output_path=output_path,
        )

    @staticmethod
    def export_layers(
        layer_results: list[LayerResult],
        width_um: float,
        height_um: float,
        output_path: str | Path,
        progress_callback: Callable[[str, int | None], None] | None = None,
    ) -> None:
        path = Path(output_path)
        if progress_callback is not None:
            progress_callback("Building SVG groups...", 90)
        lines = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            (
                f'<svg xmlns="http://www.w3.org/2000/svg" width="{width_um}um" '
                f'height="{height_um}um" viewBox="0 0 {width_um} {height_um}">'
            ),
        ]
        layer_count = max(1, len(layer_results))
        for index, layer_result in enumerate(layer_results, start=1):
            if progress_callback is not None:
                progress_callback(f"Writing SVG layer {layer_result.layer.logical_name}...", 90 + int(8 * index / layer_count))
            fill = layer_result.source_rgb or layer_result.layer.preview_rgb or (0, 0, 0)
            lines.append(
                f'  <g id="{layer_result.layer.logical_name}" '
                f'fill="rgb({fill[0]},{fill[1]},{fill[2]})" stroke="none">'
            )
            for rect in layer_result.physical_rectangles:
                lines.append(
                    "    "
                    f'<rect x="{rect.x_um:.6f}" y="{rect.y_um:.6f}" '
                    f'width="{rect.width_um:.6f}" height="{rect.height_um:.6f}" />'
                )
            lines.append("  </g>")
        lines.append("</svg>")
        path.write_text("\n".join(lines), encoding="utf-8")
