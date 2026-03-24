from __future__ import annotations

import numpy as np

from .models import PhysicalRectangle, Rectangle


class GeometryUtils:
    @staticmethod
    def mask_to_preview(mask: np.ndarray, scale: int = 8) -> np.ndarray:
        binary = mask.astype(np.uint8) * 255
        expanded = np.repeat(np.repeat(binary, scale, axis=0), scale, axis=1)
        rgba = np.zeros((expanded.shape[0], expanded.shape[1], 4), dtype=np.uint8)
        rgba[:, :, 0] = expanded
        rgba[:, :, 1] = expanded
        rgba[:, :, 2] = expanded
        rgba[:, :, 3] = 255
        return rgba

    @staticmethod
    def bounds_from_rectangles(rectangles: list[Rectangle] | list[PhysicalRectangle]):
        if not rectangles:
            return 0.0, 0.0
        max_x = 0.0
        max_y = 0.0
        for rect in rectangles:
            if isinstance(rect, Rectangle):
                max_x = max(max_x, rect.x + rect.width)
                max_y = max(max_y, rect.y + rect.height)
            else:
                max_x = max(max_x, rect.x_um + rect.width_um)
                max_y = max(max_y, rect.y_um + rect.height_um)
        return max_x, max_y
