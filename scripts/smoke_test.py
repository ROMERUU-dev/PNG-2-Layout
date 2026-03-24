from __future__ import annotations

from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from png2vlsi.exporters.gds_exporter import GdsExporter
from png2vlsi.exporters.svg_exporter import SvgExporter
from png2vlsi.models import (
    CleanupSettings,
    DrcSettings,
    LayerSettings,
    PipelineSettings,
    PixelationSettings,
    ScalingSettings,
    gds_mapping_for_logical_layer,
)
from png2vlsi.pipeline import ConversionPipeline


def main() -> None:
    sample = PROJECT_ROOT / "sample_data" / "sample_logo.png"
    svg_output = PROJECT_ROOT / "sample_data" / "smoke_output.svg"
    gds_output = PROJECT_ROOT / "sample_data" / "smoke_output.gds"
    gds_layer, gds_datatype = gds_mapping_for_logical_layer("met1")

    settings = PipelineSettings(
        alpha_threshold=8,
        cleanup=CleanupSettings(remove_islands_min_pixels=4, fill_holes_max_pixels=4, trim_transparent_margins=True),
        pixelation=PixelationSettings(mode="rows_cols", rows=48, cols=48, activation_ratio=0.5, merge_rectangles=True),
        scaling=ScalingSettings(mode="pixel_size", pixel_size_um=0.5),
        drc=DrcSettings(enabled=True, orthogonal_cleanup_iterations=1, minimum_width_cells=2, minimum_spacing_cells=2),
        layer=LayerSettings(logical_name="met1", gds_layer=gds_layer, gds_datatype=gds_datatype),
    )

    result = ConversionPipeline().run(str(sample), settings)
    SvgExporter.export(
        rectangles=result.physical_rectangles,
        width_um=result.final_width_um,
        height_um=result.final_height_um,
        layer=settings.layer,
        output_path=svg_output,
    )
    GdsExporter.export(result.physical_rectangles, settings.layer, gds_output)

    print(f"active_pixels={result.active_pixels}")
    print(f"rectangles={result.exported_rectangles}")
    print(f"size_um={result.final_width_um:.3f}x{result.final_height_um:.3f}")
    print(svg_output)
    print(gds_output)


if __name__ == "__main__":
    main()
