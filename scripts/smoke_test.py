from __future__ import annotations

from pathlib import Path
import sys
import tempfile

from PIL import Image, ImageDraw

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from png2vlsi.exporters.gds_exporter import GdsExporter
from png2vlsi.exporters.svg_exporter import SvgExporter
from png2vlsi.models import (
    CleanupSettings,
    ColorQuantizationSettings,
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
    multicolor_svg_output = PROJECT_ROOT / "sample_data" / "smoke_multicolor_output.svg"
    multicolor_gds_output = PROJECT_ROOT / "sample_data" / "smoke_multicolor_output.gds"
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
    SvgExporter.export_layers(
        layer_results=result.layer_results,
        width_um=result.final_width_um,
        height_um=result.final_height_um,
        output_path=svg_output,
    )
    try:
        GdsExporter.export_layers(result.layer_results, gds_output)
        print(gds_output)
    except RuntimeError as exc:
        print(f"gds_skipped={exc}")

    with tempfile.TemporaryDirectory() as temp_dir:
        multicolor_sample = Path(temp_dir) / "multicolor_sample.png"
        image = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        draw.rectangle((0, 0, 31, 31), fill=(255, 0, 0, 255))
        draw.rectangle((32, 0, 63, 31), fill=(0, 255, 0, 255))
        draw.rectangle((0, 32, 31, 63), fill=(0, 0, 255, 255))
        draw.rectangle((32, 32, 63, 63), fill=(255, 255, 0, 255))
        image.save(multicolor_sample)

        multicolor_settings = PipelineSettings(
            alpha_threshold=8,
            color_quantization=ColorQuantizationSettings(
                mode="solid_colors",
                selected_metals=["met1", "met2", "met3", "met4"],
            ),
            cleanup=CleanupSettings(trim_transparent_margins=True),
            pixelation=PixelationSettings(mode="rows_cols", rows=32, cols=32, activation_ratio=0.5, merge_rectangles=True),
            scaling=ScalingSettings(mode="pixel_size", pixel_size_um=0.5),
            drc=DrcSettings(enabled=False),
            layer=LayerSettings(logical_name="met1", gds_layer=gds_layer, gds_datatype=gds_datatype),
        )
        multicolor_result = ConversionPipeline().run(str(multicolor_sample), multicolor_settings)
        SvgExporter.export_layers(
            layer_results=multicolor_result.layer_results,
            width_um=multicolor_result.final_width_um,
            height_um=multicolor_result.final_height_um,
            output_path=multicolor_svg_output,
        )
        try:
            GdsExporter.export_layers(multicolor_result.layer_results, multicolor_gds_output)
            print(multicolor_gds_output)
        except RuntimeError as exc:
            print(f"multicolor_gds_skipped={exc}")
        print(f"multicolor_layers={len(multicolor_result.layer_results)}")

    print(f"active_pixels={result.active_pixels}")
    print(f"rectangles={result.exported_rectangles}")
    print(f"size_um={result.final_width_um:.3f}x{result.final_height_um:.3f}")
    print(svg_output)
    print(multicolor_svg_output)


if __name__ == "__main__":
    main()
