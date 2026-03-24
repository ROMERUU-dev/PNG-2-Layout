from __future__ import annotations

from pathlib import Path

from ..models import LayerSettings, PhysicalRectangle


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

        library = gdstk.Library(unit=1e-6, precision=1e-9)
        cell = library.new_cell(cell_name)

        for rect in rectangles:
            cell.add(
                gdstk.rectangle(
                    (rect.x_um, rect.y_um),
                    (rect.x_um + rect.width_um, rect.y_um + rect.height_um),
                    layer=layer.gds_layer,
                    datatype=layer.gds_datatype,
                )
            )

        library.write_gds(Path(output_path))
