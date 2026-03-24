from __future__ import annotations

from pathlib import Path

from ..models import LayerSettings, PhysicalRectangle


class SvgExporter:
    @staticmethod
    def export(
        rectangles: list[PhysicalRectangle],
        width_um: float,
        height_um: float,
        layer: LayerSettings,
        output_path: str | Path,
    ) -> None:
        path = Path(output_path)
        lines = [
            '<?xml version="1.0" encoding="UTF-8"?>',
            (
                f'<svg xmlns="http://www.w3.org/2000/svg" width="{width_um}um" '
                f'height="{height_um}um" viewBox="0 0 {width_um} {height_um}">'
            ),
            f'  <g id="{layer.logical_name}" fill="black" stroke="none">',
        ]
        for rect in rectangles:
            lines.append(
                "    "
                f'<rect x="{rect.x_um:.6f}" y="{rect.y_um:.6f}" '
                f'width="{rect.width_um:.6f}" height="{rect.height_um:.6f}" />'
            )
        lines.extend(["  </g>", "</svg>"])
        path.write_text("\n".join(lines), encoding="utf-8")
