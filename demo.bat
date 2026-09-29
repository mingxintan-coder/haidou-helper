@echo off
cd /d "%~dp0"
python haidou_helper.py --mock
if errorlevel 1 pause
