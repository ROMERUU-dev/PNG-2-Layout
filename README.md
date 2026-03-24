# PNG to VLSI Pixel Layout

Local Linux desktop application built with PySide6 to convert a transparent PNG logo into a strictly orthogonal pixel-art layout and export it as SVG, DXF, and GDS.

## Features

- Load transparent PNG files and detect visible content from the alpha channel.
- Preview the original image and the orthogonal pixelated result.
- Configure alpha threshold, cleanup rules, grid resolution, and physical scaling.
- Keep geometry strictly rectangle-based with no diagonals, curves, or splines.
- Merge adjacent active grid cells into larger rectangles for cleaner export.
- Export to SVG, DXF, and GDS with layer metadata.

## Project Structure

```text
png2vlsi_pixel/
├── README.md
├── requirements.txt
├── run_app.py
├── sample_data/
│   ├── ardilla.png
│   ├── generate_sample_logo.py
│   └── sample_logo.png
├── assets/
│   └── pxl.svg
├── scripts/
│   └── smoke_test.py
└── src/
    └── png2vlsi/
        ├── __init__.py
        ├── app.py
        ├── cleanup.py
        ├── geometry.py
        ├── image_loader.py
        ├── mask_generator.py
        ├── models.py
        ├── pipeline.py
        ├── pixelation.py
        ├── scaling.py
        ├── exporters/
        │   ├── __init__.py
        │   ├── dxf_exporter.py
        │   ├── gds_exporter.py
        │   └── svg_exporter.py
        └── gui/
            ├── __init__.py
            └── main_window.py
```

## Requirements

- Linux
- Python 3.10+
- Qt runtime compatible with PySide6

Python dependencies are listed in `requirements.txt`.

## Installation

1. Create a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Run the app:

```bash
python3 run_app.py
```

## Usage

1. Click `Load PNG` and select a transparent logo image.
2. Adjust the alpha threshold if needed to separate visible pixels from the background.
3. Choose the pixelation mode:
   - `Rows / Columns`
   - `Source Pixel Size`
4. Configure cleanup:
   - remove tiny islands
   - fill small holes
   - trim transparent margins
5. Configure physical scaling:
   - define pixel size in micrometers
   - or target width / target height in micrometers
6. Review the pixelated preview and the exported statistics.
7. Export as SVG, DXF, or GDS.

## Notes

- The first version is intentionally orthogonal-only.
- No diagonal reconstruction, smoothing, Bezier curves, or 45-degree geometry are generated.
- Geometry is handled internally as rectangles to stay robust and predictable for layout tools such as KLayout.
- The architecture leaves room for future DRC-like checks such as minimum width and spacing validation.

## Sample Data

A simple sample logo is included at [ardilla.png](/home/romeruu/png2vlsi_pixel/sample_data/ardilla.png). The launcher icon can be placed at `[assets/pxl.svg](/home/romeruu/png2vlsi_pixel/assets/pxl.svg)`. You can regenerate the older sample with:

```bash
python3 sample_data/generate_sample_logo.py
```

## Validation

Basic non-GUI validation script:

```bash
python3 scripts/smoke_test.py
```
