from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image

from .models import LoadedImage


class ImageLoader:
    """Load RGBA PNG images and expose the alpha channel for mask generation."""

    @staticmethod
    def load_png(path: str | Path) -> LoadedImage:
        image_path = Path(path)
        pil_image = Image.open(image_path).convert("RGBA")
        rgba = np.array(pil_image, dtype=np.uint8)
        alpha = rgba[:, :, 3]
        return LoadedImage(path=image_path, pil_image=pil_image, rgba=rgba, alpha=alpha)
