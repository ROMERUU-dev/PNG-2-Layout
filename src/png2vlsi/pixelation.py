from __future__ import annotations

import numpy as np

from .models import PixelationSettings, Rectangle


class Pixelator:
    @staticmethod
    def resolve_grid(mask: np.ndarray, settings: PixelationSettings) -> tuple[int, int]:
        if settings.mode == "source_pixel_size":
            cell = max(1, int(settings.source_pixel_size))
            rows = max(1, int(np.ceil(mask.shape[0] / cell)))
            cols = max(1, int(np.ceil(mask.shape[1] / cell)))
        else:
            rows = max(1, settings.rows)
            if settings.preserve_aspect_ratio:
                aspect_ratio = mask.shape[1] / max(1, mask.shape[0])
                cols = max(1, int(round(rows * aspect_ratio)))
            else:
                cols = max(1, settings.cols)
        return rows, cols

    @staticmethod
    def pixelate(mask: np.ndarray, settings: PixelationSettings) -> np.ndarray:
        rows, cols = Pixelator.resolve_grid(mask, settings)

        y_edges = np.linspace(0, mask.shape[0], rows + 1, dtype=int)
        x_edges = np.linspace(0, mask.shape[1], cols + 1, dtype=int)

        pixel_mask = np.zeros((rows, cols), dtype=bool)
        for row in range(rows):
            for col in range(cols):
                y0, y1 = y_edges[row], y_edges[row + 1]
                x0, x1 = x_edges[col], x_edges[col + 1]
                tile = mask[y0:y1, x0:x1]
                if tile.size == 0:
                    continue
                pixel_mask[row, col] = float(tile.mean()) >= settings.activation_ratio
        return pixel_mask

    @staticmethod
    def mask_to_rectangles(mask: np.ndarray, merge_rectangles: bool) -> list[Rectangle]:
        if not merge_rectangles:
            ys, xs = np.nonzero(mask)
            return [Rectangle(int(x), int(y), 1, 1) for y, x in zip(ys, xs)]

        rows, cols = mask.shape
        used = np.zeros_like(mask, dtype=bool)
        rectangles: list[Rectangle] = []

        for y in range(rows):
            for x in range(cols):
                if not mask[y, x] or used[y, x]:
                    continue

                width = 1
                while x + width < cols and mask[y, x + width] and not used[y, x + width]:
                    width += 1

                height = 1
                grow = True
                while y + height < rows and grow:
                    for test_x in range(x, x + width):
                        if not mask[y + height, test_x] or used[y + height, test_x]:
                            grow = False
                            break
                    if grow:
                        height += 1

                used[y : y + height, x : x + width] = True
                rectangles.append(Rectangle(x=x, y=y, width=width, height=height))

        return rectangles
