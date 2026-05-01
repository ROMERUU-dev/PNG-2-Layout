# PNG to VLSI Pixel Layout

Desktop application for Ubuntu/Linux that converts PNG images into orthogonal VLSI-style pixel geometry and exports `SVG`, `DXF`, and `GDS`.

## Current Features

- Two workflows in the GUI:
  - `Alpha Monochrome` for transparent or single-layer images
  - `Solid Multicolor` for segmented color images mapped to selected metals
- Manual metal selection for multicolor flow: `met1` to `met5`
- Built-in DRC-oriented Manhattan cleanup
- Background remover tool in `Tools -> Background Remover...`
- Activity panel with step-by-step processing log
- Default physical size starts in `Fit Inside Box` at `30um x 30um` to avoid huge accidental outputs

## Important Notes

- `met5` is available in the GUI, but Tiny Tapeout does not allow `metal5`.
- Geometry stays orthogonal on purpose: no curves, splines, or diagonal reconstruction are generated.
- The DRC cleanup is defensive, but final signoff still belongs to your layout tool flow, for example Magic or KLayout checks.

## Project Structure

```text
PNG-2-Layout/
├── README.md
├── VERSION
├── requirements.txt
├── run_app.py
├── assets/
├── sample_data/
├── scripts/
│   ├── build_deb.sh
│   └── smoke_test.py
└── src/
    └── png2vlsi/
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
        └── gui/
            ├── background_remover_dialog.py
            ├── main_window.py
            └── preferences_dialog.py
```

## Local Run

1. Create the environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Launch the GUI:

```bash
python3 run_app.py
```

## GUI Workflow

### 1. Alpha Monochrome

Use this tab when the image is already transparent or should become a single metal layer.

- Load the image
- Pick the logical metal
- Adjust alpha threshold
- Set pixelation and scaling
- Export

### 2. Solid Multicolor

Use this tab when the image has solid regions and you want to split it across multiple metals.

- Load the image
- Select which metals are allowed
- Adjust alpha threshold for visible pixels
- Preview the segmented result
- Export

The detected color regions are assigned in order to the checked metals.

## Background Remover Tool

Open `Tools -> Background Remover...`

This tool is meant for PNGs that still have a colored background.

- Click directly on the unwanted background color
- Increase or decrease `Color Tolerance`
- Use the alpha threshold gate to avoid touching already transparent pixels
- Repeat as many times as needed
- Click `Use In App` to load the edited PNG back into the main application
- Or save the edited PNG manually

## Validation

Run the basic pipeline validation:

```bash
python3 scripts/smoke_test.py
```

## Debian Package Build

This repository includes a Debian packaging script that vendors the Python dependencies into the package, so installation on another Ubuntu machine is straightforward.

Build the package:

```bash
./scripts/build_deb.sh
```

Or build an explicit version:

```bash
./scripts/build_deb.sh 0.2.0
```

The output lands in `dist/` as:

```text
png-2-layout_<version>_<arch>.deb
```

## Install The `.deb` On Ubuntu

On the target machine:

```bash
sudo apt install ./png-2-layout_<version>_<arch>.deb
```

If `apt` asks to resolve dependencies, let it do so. The package already includes the Python-side dependencies; Ubuntu only needs the system libraries listed in the package control file.

After install, launch from:

- Applications menu: `PNG 2 Layout`
- Terminal:

```bash
png-2-layout
```

## Portable Ubuntu Notes

The `.deb` is intended to be installable on other Ubuntu systems as long as they have:

- `python3`
- standard X11/Qt runtime libraries required by PySide6

The package script already declares these runtime dependencies in `DEBIAN/control`.

## Repository

GitHub:

`https://github.com/ROMERUU-dev/PNG-2-Layout`
