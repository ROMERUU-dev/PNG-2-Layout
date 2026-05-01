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
        bounds = GeometryCleanup.trim_bounds(mask)
        return GeometryCleanup.crop_to_bounds(mask, bounds)

    @staticmethod
    def trim_bounds(mask: np.ndarray) -> tuple[int, int, int, int]:
        ys, xs = np.nonzero(mask)
        if len(xs) == 0 or len(ys) == 0:
            return (0, 1, 0, 1)
        return (int(ys.min()), int(ys.max()) + 1, int(xs.min()), int(xs.max()) + 1)

    @staticmethod
    def crop_to_bounds(mask: np.ndarray, bounds: tuple[int, int, int, int]) -> np.ndarray:
        y0, y1, x0, x1 = bounds
        return mask[y0:y1, x0:x1].copy()

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
            cleaned = GridDrcCleanup._close_diagonal_gaps(cleaned)
            cleaned = GridDrcCleanup._fill_single_cell_notches(cleaned)

        if settings.minimum_spacing_cells > 1:
            cleaned = GridDrcCleanup._fill_small_gaps(cleaned, settings.minimum_spacing_cells)
            cleaned = GridDrcCleanup._close_diagonal_gaps(cleaned)
        if settings.minimum_width_cells > 1:
            cleaned = GridDrcCleanup._remove_narrow_runs(cleaned, settings.minimum_width_cells)
            cleaned = GridDrcCleanup._remove_thin_islands(cleaned, settings.minimum_width_cells)

        # One final Manhattan pass after spacing/width repair tends to remove
        # leftover pinches and corner artifacts created by earlier fixes.
        cleaned = GridDrcCleanup._cleanup_jogs(cleaned)
        cleaned = GridDrcCleanup._close_diagonal_gaps(cleaned)
        cleaned = GridDrcCleanup._fill_single_cell_notches(cleaned)

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
    def _close_diagonal_gaps(mask: np.ndarray) -> np.ndarray:
        result = mask.copy()
        height, width = mask.shape
        for y in range(height - 1):
            for x in range(width - 1):
                block = mask[y : y + 2, x : x + 2]
                if block[0, 0] and block[1, 1] and not block[0, 1] and not block[1, 0]:
                    result[y : y + 2, x : x + 2] = True
                elif block[0, 1] and block[1, 0] and not block[0, 0] and not block[1, 1]:
                    result[y : y + 2, x : x + 2] = True
        return result

    @staticmethod
    def _fill_single_cell_notches(mask: np.ndarray) -> np.ndarray:
        result = mask.copy()
        height, width = mask.shape
        for y in range(1, height - 1):
            for x in range(1, width - 1):
                if mask[y, x]:
                    continue
                left = mask[y, x - 1]
                right = mask[y, x + 1]
                up = mask[y - 1, x]
                down = mask[y + 1, x]
                if (left and right) or (up and down):
                    result[y, x] = True
        return result

    @staticmethod
    def _remove_thin_islands(mask: np.ndarray, minimum_width: int) -> np.ndarray:
        if minimum_width <= 1:
            return mask

        result = mask.copy()
        height, width = mask.shape
        for y in range(height):
            for x in range(width):
                if not mask[y, x]:
                    continue
                horizontal = GridDrcCleanup._run_length(mask, x, y, horizontal=True)
                vertical = GridDrcCleanup._run_length(mask, x, y, horizontal=False)
                if horizontal < minimum_width and vertical < minimum_width:
                    result[y, x] = False
        return result

    @staticmethod
    def _run_length(mask: np.ndarray, x: int, y: int, horizontal: bool) -> int:
        length = 1
        dx, dy = (1, 0) if horizontal else (0, 1)

        cursor_x, cursor_y = x - dx, y - dy
        while 0 <= cursor_x < mask.shape[1] and 0 <= cursor_y < mask.shape[0] and mask[cursor_y, cursor_x]:
            length += 1
            cursor_x -= dx
            cursor_y -= dy

        cursor_x, cursor_y = x + dx, y + dy
        while 0 <= cursor_x < mask.shape[1] and 0 <= cursor_y < mask.shape[0] and mask[cursor_y, cursor_x]:
            length += 1
            cursor_x += dx
            cursor_y += dy

        return length

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
