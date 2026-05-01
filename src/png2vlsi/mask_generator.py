from __future__ import annotations

import numpy as np
from PIL import Image


class MaskGenerator:
    @staticmethod
    def alpha_to_mask(alpha: np.ndarray, threshold: int) -> np.ndarray:
        threshold = int(max(0, min(255, threshold)))
        return alpha >= threshold

    @staticmethod
    def rgba_to_color_masks(
        rgba: np.ndarray,
        alpha: np.ndarray,
        alpha_threshold: int,
        color_count: int,
    ) -> list[tuple[np.ndarray, tuple[int, int, int]]]:
        visible = MaskGenerator.alpha_to_mask(alpha, alpha_threshold)
        if not np.any(visible):
            return []

        palette_size = max(1, min(4, int(color_count)))
        rgb = rgba[:, :, :3]
        visible_pixels = rgb[visible]
        unique_colors = np.unique(visible_pixels, axis=0)
        if unique_colors.shape[0] <= palette_size:
            entries: list[tuple[np.ndarray, tuple[int, int, int], int]] = []
            for color in unique_colors:
                color_tuple = (int(color[0]), int(color[1]), int(color[2]))
                mask = visible & np.all(rgb == color, axis=2)
                entries.append((mask, color_tuple, int(mask.sum())))
            entries.sort(key=lambda entry: entry[2], reverse=True)
            return [(mask, color) for mask, color, _ in entries]

        strip = Image.fromarray(visible_pixels.reshape((-1, 1, 3)), mode="RGB")
        quantized = strip.quantize(colors=palette_size)
        palette = quantized.getpalette()[: palette_size * 3]
        labels = np.array(quantized, dtype=np.uint8).reshape(-1)

        indexed = np.full(alpha.shape, -1, dtype=np.int16)
        indexed[visible] = labels

        entries = []
        for palette_index in range(palette_size):
            mask = indexed == palette_index
            if not np.any(mask):
                continue
            base = palette_index * 3
            color = (
                int(palette[base]),
                int(palette[base + 1]),
                int(palette[base + 2]),
            )
            entries.append((mask, color, int(mask.sum())))

        entries.sort(key=lambda entry: entry[2], reverse=True)
        return [(mask, color) for mask, color, _ in entries]
