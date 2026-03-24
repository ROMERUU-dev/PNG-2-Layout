from __future__ import annotations

from .models import PhysicalRectangle, Rectangle, ScalingSettings


class PhysicalScaler:
    @staticmethod
    def resolve_pixel_size_um(grid_width: int, grid_height: int, settings: ScalingSettings) -> float:
        if settings.mode == "target_width":
            return settings.target_width_um / max(1, grid_width)
        if settings.mode == "target_height":
            return settings.target_height_um / max(1, grid_height)
        if settings.mode == "fit_box":
            width_limit = settings.target_width_um / max(1, grid_width)
            height_limit = settings.target_height_um / max(1, grid_height)
            return min(width_limit, height_limit)
        return settings.pixel_size_um

    @staticmethod
    def scale_rectangles(
        rectangles: list[Rectangle],
        pixel_size_um: float,
        grid_height: int,
    ) -> list[PhysicalRectangle]:
        scaled: list[PhysicalRectangle] = []
        for rect in rectangles:
            scaled.append(
                PhysicalRectangle(
                    x_um=rect.x * pixel_size_um,
                    y_um=(grid_height - rect.y - rect.height) * pixel_size_um,
                    width_um=rect.width * pixel_size_um,
                    height_um=rect.height * pixel_size_um,
                )
            )
        return scaled
