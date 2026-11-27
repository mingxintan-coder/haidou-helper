#!/bin/bash
# 海斗助手 Mac 启动：双击这个文件（第一次要在「终端机」里允许执行，见 README）
cd "$(dirname "$0")"
PY=python3
if ! command -v $PY >/dev/null 2>&1; then
  echo "没有找到 Python 3。请先到 https://www.python.org/downloads/macos/ 下载安装（要有 tkinter 的官方版本）。"
  read -n 1 -s -r -p "按任意键关闭"
  exit 1
fi
if ! $PY -c "import tkinter" 2>/dev/null; then
  echo "这个 Python 没有 tkinter（Homebrew 的 Python 常见）。请安装 python.org 的官方版本，或执行 brew install python-tk。"
  read -n 1 -s -r -p "按任意键关闭"
  exit 1
fi
$PY -c "import rapidocr, onnxruntime, PIL, certifi" 2>/dev/null || {
  echo "第一次使用：安装屏幕识别组件（约 60MB，只装一次）…"
  $PY -m pip install -q --disable-pip-version-check -U rapidocr onnxruntime pillow certifi
}
$PY haidou_helper.py "$@"
