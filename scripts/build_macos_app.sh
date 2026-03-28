#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
PYTHON_BIN="${PYTHON:-python3}"
PYINSTALLER_CONFIG_DIR="${PYINSTALLER_CONFIG_DIR:-${TMPDIR:-/tmp}/pyinstaller-lightnovel-pydownloader}"

if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "这个脚本只支持在 macOS 上执行。"
  exit 1
fi

cd "${ROOT_DIR}"

mkdir -p "${PYINSTALLER_CONFIG_DIR}"

echo "Installing build dependencies with ${PYTHON_BIN}..."
"${PYTHON_BIN}" -m pip install -r requirements-build.txt

echo "Cleaning previous build artifacts..."
rm -rf build dist

echo "Building macOS app bundle..."
PYINSTALLER_CONFIG_DIR="${PYINSTALLER_CONFIG_DIR}" "${PYTHON_BIN}" -m PyInstaller --clean --noconfirm lightnovel_gui_macos.spec

echo
echo "Build complete:"
echo "  ${ROOT_DIR}/dist/抓书姬.app"
