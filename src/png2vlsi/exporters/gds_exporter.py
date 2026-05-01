from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from ..models import LayerResult, LayerSettings, PhysicalRectangle


class GdsExporter:
    @staticmethod
    def export(
        rectangles: list[PhysicalRectangle],
        layer: LayerSettings,
        output_path: str | Path,
        cell_name: str = "TOP",
    ) -> None:
        try:
            import gdstk
        except ImportError as exc:
            raise RuntimeError("gdstk is required for GDS export") from exc

        GdsExporter.export_layers(
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
            output_path=output_path,
            cell_name=cell_name,
        )

    @staticmethod
    def export_layers(
        layer_results: list[LayerResult],
        output_path: str | Path,
        cell_name: str = "TOP",
        progress_callback: Callable[[str, int | None], None] | None = None,
    ) -> None:
        try:
            import gdstk
        except ImportError as exc:
            raise RuntimeError("gdstk is required for GDS export") from exc

        library = gdstk.Library(unit=1e-6, precision=1e-9)
        cell = library.new_cell(cell_name)

        layer_count = max(1, len(layer_results))
        for index, layer_result in enumerate(layer_results, start=1):
            if progress_callback is not None:
                progress_callback(f"Writing GDS layer {layer_result.layer.logical_name}...", 90 + int(8 * index / layer_count))
            for rect in layer_result.physical_rectangles:
                cell.add(
                    gdstk.rectangle(
                        (rect.x_um, rect.y_um),
                        (rect.x_um + rect.width_um, rect.y_um + rect.height_um),
                        layer=layer_result.layer.gds_layer,
                        datatype=layer_result.layer.gds_datatype,
                    )
                )

        library.write_gds(Path(output_path))
