from __future__ import annotations

from pathlib import Path


APP_NAME = "PNG2VLSI Pixel"
COMMENT = "Convert raster logos into layout-ready pixel geometry"
DESKTOP_ID = "png2vlsi-pixel.desktop"


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def exec_path() -> Path:
    return project_root() / "launch.sh"


def default_icon_path() -> Path | None:
    candidate = project_root() / "assets" / "pxl.svg"
    if candidate.exists():
        return candidate
    return None


def desktop_targets() -> list[Path]:
    targets = [Path.home() / ".local/share/applications" / DESKTOP_ID]
    for folder_name in ("Desktop", "Escritorio"):
        desktop_dir = Path.home() / folder_name
        if desktop_dir.exists():
            targets.append(desktop_dir / DESKTOP_ID)
    return targets


def build_desktop_entry() -> str:
    lines = [
        "[Desktop Entry]",
        "Version=1.0",
        "Type=Application",
        f"Name={APP_NAME}",
        f"Comment={COMMENT}",
        f"Exec={exec_path()}",
        "Terminal=false",
        "Categories=Graphics;Development;",
        "StartupNotify=true",
        f"Path={project_root()}",
    ]
    icon_path = default_icon_path()
    if icon_path is not None:
        lines.append(f"Icon={icon_path}")
    lines.append("")
    return "\n".join(lines)


def install_entry(target: Path, content: str) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    target.chmod(0o755)


def install_launcher_entries() -> list[Path]:
    content = build_desktop_entry()
    installed_paths: list[Path] = []
    for target in desktop_targets():
        install_entry(target, content)
        installed_paths.append(target)
    return installed_paths
