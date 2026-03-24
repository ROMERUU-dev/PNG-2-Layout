from __future__ import annotations

from pathlib import Path

from ..models import LayerSettings, PhysicalRectangle


class DxfExporter:
    @staticmethod
    def export(rectangles: list[PhysicalRectangle], layer: LayerSettings, output_path: str | Path) -> None:
        try:
            import ezdxf
        except ImportError as exc:
            raise RuntimeError("ezdxf is required for DXF export") from exc

        doc = ezdxf.new(setup=True)
        if layer.logical_name not in doc.layers:
            doc.layers.add(name=layer.logical_name)
        msp = doc.modelspace()

        for rect in rectangles:
            points = [
                (rect.x_um, rect.y_um),
                (rect.x_um + rect.width_um, rect.y_um),
                (rect.x_um + rect.width_um, rect.y_um + rect.height_um),
                (rect.x_um, rect.y_um + rect.height_um),
            ]
            msp.add_lwpolyline(points, close=True, dxfattribs={"layer": layer.logical_name})

        doc.header["$INSUNITS"] = 13
        doc.saveas(Path(output_path))
