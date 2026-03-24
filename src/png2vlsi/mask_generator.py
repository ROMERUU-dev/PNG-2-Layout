from __future__ import annotations

import numpy as np


class MaskGenerator:
    @staticmethod
    def alpha_to_mask(alpha: np.ndarray, threshold: int) -> np.ndarray:
        threshold = int(max(0, min(255, threshold)))
        return alpha >= threshold
