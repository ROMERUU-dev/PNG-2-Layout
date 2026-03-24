from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw


def main() -> None:
    output_path = Path(__file__).resolve().parent / "sample_logo.png"
    image = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)

    draw.rounded_rectangle((28, 28, 228, 228), radius=24, fill=(255, 255, 255, 255))
    draw.rectangle((84, 84, 172, 172), fill=(0, 0, 0, 0))
    draw.rectangle((52, 112, 204, 144), fill=(255, 255, 255, 255))
    draw.rectangle((112, 52, 144, 204), fill=(255, 255, 255, 255))

    image.save(output_path)
    print(output_path)


if __name__ == "__main__":
    main()
