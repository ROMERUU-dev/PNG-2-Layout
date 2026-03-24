from __future__ import annotations

from collections import deque

import numpy as np

from .models import CleanupSettings, DrcSettings


class GeometryCleanup:
    @staticmethod
    def apply(mask: np.ndarray, settings: CleanupSettings) -> np.ndarray:
        cleaned = mask.astype(bool, copy=True)
        if settings.remove_islands_min_pixels > 0:
            cleaned = GeometryCleanup._filter_components(
                cleaned,
                keep_value=True,
                min_pixels=settings.remove_islands_min_pixels,
            )
        if settings.fill_holes_max_pixels > 0:
            inverted = ~cleaned
            filtered = GeometryCleanup._filter_components(
                inverted,
                keep_value=True,
                min_pixels=settings.fill_holes_max_pixels + 1,
                ignore_border=True,
            )
            cleaned = ~filtered
        if settings.trim_transparent_margins:
            cleaned = GeometryCleanup.trim_margins(cleaned)
        return cleaned

    @staticmethod
    def trim_margins(mask: np.ndarray) -> np.ndarray:
        ys, xs = np.nonzero(mask)
        if len(xs) == 0 or len(ys) == 0:
            return mask[:1, :1].copy()
        return mask[ys.min() : ys.max() + 1, xs.min() : xs.max() + 1]

    @staticmethod
    def _filter_components(
        mask: np.ndarray,
        keep_value: bool,
        min_pixels: int,
        ignore_border: bool = False,
    ) -> np.ndarray:
        height, width = mask.shape
        visited = np.zeros_like(mask, dtype=bool)
        result = mask.copy()

        for y in range(height):
            for x in range(width):
                if visited[y, x] or mask[y, x] != keep_value:
                    continue
                component, touches_border = GeometryCleanup._collect_component(mask, visited, x, y)
                if ignore_border and touches_border:
                    continue
                if len(component) < min_pixels:
                    for cx, cy in component:
                        result[cy, cx] = not keep_value
        return result

    @staticmethod
    def _collect_component(mask: np.ndarray, visited: np.ndarray, start_x: int, start_y: int):
        height, width = mask.shape
        queue: deque[tuple[int, int]] = deque([(start_x, start_y)])
        visited[start_y, start_x] = True
        target = mask[start_y, start_x]
        component: list[tuple[int, int]] = []
        touches_border = False

        while queue:
            x, y = queue.popleft()
            component.append((x, y))
            if x == 0 or y == 0 or x == width - 1 or y == height - 1:
                touches_border = True
            for nx, ny in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
                if nx < 0 or ny < 0 or nx >= width or ny >= height:
                    continue
                if visited[ny, nx] or mask[ny, nx] != target:
                    continue
                visited[ny, nx] = True
                queue.append((nx, ny))
        return component, touches_border


class GridDrcCleanup:
    """Simple Manhattan regularization on the orthogonal cell grid."""

    @staticmethod
    def apply(mask: np.ndarray, settings: DrcSettings) -> np.ndarray:
        if not settings.enabled:
            return mask.astype(bool, copy=True)

        cleaned = mask.astype(bool, copy=True)
        for _ in range(max(0, settings.orthogonal_cleanup_iterations)):
            cleaned = GridDrcCleanup._cleanup_jogs(cleaned)

        if settings.minimum_spacing_cells > 1:
            cleaned = GridDrcCleanup._fill_small_gaps(cleaned, settings.minimum_spacing_cells)
        if settings.minimum_width_cells > 1:
            cleaned = GridDrcCleanup._remove_narrow_runs(cleaned, settings.minimum_width_cells)

        return cleaned

    @staticmethod
    def _cleanup_jogs(mask: np.ndarray) -> np.ndarray:
        result = mask.copy()
        height, width = mask.shape
        for y in range(height):
            for x in range(width):
                left = x > 0 and mask[y, x - 1]
                right = x + 1 < width and mask[y, x + 1]
                up = y > 0 and mask[y - 1, x]
                down = y + 1 < height and mask[y + 1, x]

                if not mask[y, x] and ((left and right) or (up and down)):
                    result[y, x] = True
                elif mask[y, x] and ((not left and not right) or (not up and not down)):
                    result[y, x] = False
        return result

    @staticmethod
    def _fill_small_gaps(mask: np.ndarray, minimum_spacing: int) -> np.ndarray:
        result = mask.copy()
        GridDrcCleanup._fill_gaps_along_axis(result, minimum_spacing, horizontal=True)
        GridDrcCleanup._fill_gaps_along_axis(result, minimum_spacing, horizontal=False)
        return result

    @staticmethod
    def _remove_narrow_runs(mask: np.ndarray, minimum_width: int) -> np.ndarray:
        result = mask.copy()
        GridDrcCleanup._remove_runs_along_axis(result, minimum_width, horizontal=True)
        GridDrcCleanup._remove_runs_along_axis(result, minimum_width, horizontal=False)
        return result

    @staticmethod
    def _fill_gaps_along_axis(mask: np.ndarray, minimum_spacing: int, horizontal: bool) -> None:
        outer = mask.shape[0] if horizontal else mask.shape[1]
        inner = mask.shape[1] if horizontal else mask.shape[0]
        for outer_index in range(outer):
            line = mask[outer_index, :] if horizontal else mask[:, outer_index]
            start = 0
            while start < inner:
                if line[start]:
                    start += 1
                    continue
                gap_start = start
                while start < inner and not line[start]:
                    start += 1
                gap_end = start
                gap_length = gap_end - gap_start
                has_left = gap_start > 0 and line[gap_start - 1]
                has_right = gap_end < inner and line[gap_end]
                if has_left and has_right and gap_length < minimum_spacing:
                    line[gap_start:gap_end] = True

    @staticmethod
    def _remove_runs_along_axis(mask: np.ndarray, minimum_width: int, horizontal: bool) -> None:
        outer = mask.shape[0] if horizontal else mask.shape[1]
        inner = mask.shape[1] if horizontal else mask.shape[0]
        for outer_index in range(outer):
            line = mask[outer_index, :] if horizontal else mask[:, outer_index]
            start = 0
            while start < inner:
                if not line[start]:
                    start += 1
                    continue
                run_start = start
                while start < inner and line[start]:
                    start += 1
                run_end = start
                run_length = run_end - run_start
                has_left_gap = run_start > 0 and not line[run_start - 1]
                has_right_gap = run_end < inner and not line[run_end]
                if has_left_gap and has_right_gap and run_length < minimum_width:
                    line[run_start:run_end] = False
