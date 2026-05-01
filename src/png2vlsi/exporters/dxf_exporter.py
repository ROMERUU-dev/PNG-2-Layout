from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from ..models import LayerResult, LayerSettings, PhysicalRectangle


class DxfExporter:
    @staticmethod
    def export(rectangles: list[PhysicalRectangle], layer: LayerSettings, output_path: str | Path) -> None:
        DxfExporter.export_layers(
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
        )

    @staticmethod
    def export_layers(
        layer_results: list[LayerResult],
        output_path: str | Path,
        progress_callback: Callable[[str, int | None], None] | None = None,
    ) -> None:
        try:
            import ezdxf
        except ImportError as exc:
            raise RuntimeError("ezdxf is required for DXF export") from exc

        doc = ezdxf.new(setup=True)
        msp = doc.modelspace()

        layer_count = max(1, len(layer_results))
        for index, layer_result in enumerate(layer_results, start=1):
            if progress_callback is not None:
                progress_callback(f"Writing DXF layer {layer_result.layer.logical_name}...", 90 + int(8 * index / layer_count))
            if layer_result.layer.logical_name not in doc.layers:
                doc.layers.add(name=layer_result.layer.logical_name)
            for rect in layer_result.physical_rectangles:
                points = [
                    (rect.x_um, rect.y_um),
                    (rect.x_um + rect.width_um, rect.y_um),
                    (rect.x_um + rect.width_um, rect.y_um + rect.height_um),
                    (rect.x_um, rect.y_um + rect.height_um),
                ]
                msp.add_lwpolyline(points, close=True, dxfattribs={"layer": layer_result.layer.logical_name})

        doc.header["$INSUNITS"] = 13
        doc.saveas(Path(output_path))
