@echo off
cd /d "%~dp0"
python -m counterform serve --port 8768
pause
