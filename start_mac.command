#!/bin/bash
# 海斗助手 Mac 启动。打开方式：终端机输入 bash 加空格，把这个文件拖进去，按 Enter（见 README）
cd "$(dirname "$0")"
PY=python3
if ! command -v $PY >/dev/null 2>&1; then
  echo "没有找到 Python 3。请先到 https://www.python.org/downloads/macos/ 下载安装。"
  exit 1
fi
if ! $PY -c "import tkinter" 2>/dev/null; then
  echo "这个 Python 没有 tkinter（Homebrew 的 Python 常见）。请安装 python.org 的官方版本，或执行 brew install python-tk。"
  exit 1
fi
# 基本组件（证书、截图）：一定要有
$PY -c "import PIL, certifi" 2>/dev/null || {
  echo "安装基本组件（证书、截图）…"
  $PY -m pip install -q --disable-pip-version-check -U pillow certifi
}
# 屏幕识别（OCR）：装不了也能用助手，只是三选一要手动输入。只试一次
MARK="$HOME/.lol_haidou_helper/ocr_install_tried"
if ! $PY -c "import rapidocr, onnxruntime" 2>/dev/null && [ ! -f "$MARK" ]; then
  echo "安装屏幕识别组件（约 60MB，只装一次）…"
  mkdir -p "$HOME/.lol_haidou_helper"
  if ! $PY -m pip install -q --disable-pip-version-check -U rapidocr onnxruntime; then
    touch "$MARK"
    echo ""
    echo "【屏幕识别装不上】你的 Python 版本是 $($PY -c 'import sys;print(sys.version.split()[0])')，识别要用的 onnxruntime 还不支持。"
    echo "助手照样能用（选英雄、出装、实时决策都正常），只是三选一要手动输入。"
    echo "想要自动识别：到 python.org 装 Python 3.12，然后用 python3.12 开（把这个文件里 PY=python3 改成 PY=python3.12）。"
    echo ""
  fi
fi
$PY haidou_helper.py "$@"
