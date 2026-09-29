@echo off
cd /d "%~dp0"
python -c "import rapidocr, onnxruntime, PIL" 2>nul || (
  echo Installing screen OCR components, about 60MB, only once...
  python -m pip install -q --disable-pip-version-check -U rapidocr onnxruntime pillow
)
python haidou_helper.py --web %*
if errorlevel 1 pause
