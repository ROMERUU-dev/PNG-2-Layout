#!/usr/bin/env bash
set -euo pipefail

PACKAGE="png-2-layout"
APP_NAME="PNG 2 Layout"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEFAULT_VERSION="$(tr -d '[:space:]' < "$ROOT_DIR/VERSION")"
VERSION="${1:-$DEFAULT_VERSION}"
ARCH="$(dpkg --print-architecture)"
BUILD_ROOT="$ROOT_DIR/build/deb"
PKG_ROOT="$BUILD_ROOT/${PACKAGE}_${VERSION}_${ARCH}"
APP_DIR="$PKG_ROOT/usr/share/$PACKAGE"
DIST_DIR="$ROOT_DIR/dist"
DPKG_COMPRESSOR="${DPKG_COMPRESSOR:-gzip}"
DPKG_COMPRESSION_LEVEL="${DPKG_COMPRESSION_LEVEL:-1}"

rm -rf "$BUILD_ROOT"
mkdir -p \
  "$APP_DIR" \
  "$PKG_ROOT/DEBIAN" \
  "$PKG_ROOT/usr/bin" \
  "$PKG_ROOT/usr/share/applications" \
  "$PKG_ROOT/usr/share/icons/hicolor/scalable/apps" \
  "$DIST_DIR"

cp -a "$ROOT_DIR/src" "$APP_DIR/"
cp -a "$ROOT_DIR/assets" "$APP_DIR/"
cp -a "$ROOT_DIR/sample_data" "$APP_DIR/"
cp "$ROOT_DIR/README.md" "$APP_DIR/"
cp "$ROOT_DIR/VERSION" "$APP_DIR/"
cp "$ROOT_DIR/requirements.txt" "$APP_DIR/"
cp "$ROOT_DIR/run_app.py" "$APP_DIR/"

python3 -m pip install \
  --disable-pip-version-check \
  --no-compile \
  --target "$APP_DIR/vendor" \
  -r "$ROOT_DIR/requirements.txt"

find "$APP_DIR/src" -type d -name __pycache__ -prune -exec rm -rf {} +
find "$APP_DIR/src" -type f \( -name '*.pyc' -o -name '*.pyo' \) -delete
rm -f "$APP_DIR/sample_data"/smoke_output.*
rm -f "$APP_DIR/sample_data"/smoke_multicolor_output.*

cat > "$PKG_ROOT/usr/bin/$PACKAGE" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail

APP_DIR="/usr/share/png-2-layout"
export PYTHONPATH="$APP_DIR/vendor:$APP_DIR/src${PYTHONPATH:+:$PYTHONPATH}"
cd "$APP_DIR"
exec python3 "$APP_DIR/run_app.py" "$@"
EOF
chmod 0755 "$PKG_ROOT/usr/bin/$PACKAGE"

cp "$ROOT_DIR/assets/pxl.svg" "$PKG_ROOT/usr/share/icons/hicolor/scalable/apps/$PACKAGE.svg"

cat > "$PKG_ROOT/usr/share/applications/$PACKAGE.desktop" <<EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=$APP_NAME
Comment=Convert raster logos into layout-ready pixel geometry
Exec=$PACKAGE
Icon=$PACKAGE
Terminal=false
Categories=Graphics;Development;
StartupNotify=true
EOF

cat > "$PKG_ROOT/DEBIAN/control" <<EOF
Package: $PACKAGE
Version: $VERSION
Section: graphics
Priority: optional
Architecture: $ARCH
Maintainer: ROMERUU-dev
Depends: python3, libgl1, libxkbcommon-x11-0, libxcb-cursor0, libxcb-icccm4, libxcb-image0, libxcb-keysyms1, libxcb-randr0, libxcb-render-util0, libxcb-shape0, libxcb-xinerama0
Description: Convert PNG logos into VLSI pixel layout exports
 PNG 2 Layout is a local Linux desktop application built with PySide6.
 It converts transparent PNG logos into orthogonal pixel layouts and exports
 SVG, DXF, and GDS files.
EOF

dpkg-deb \
  -Z"$DPKG_COMPRESSOR" \
  -z"$DPKG_COMPRESSION_LEVEL" \
  --build \
  --root-owner-group \
  "$PKG_ROOT" \
  "$DIST_DIR/${PACKAGE}_${VERSION}_${ARCH}.deb"
