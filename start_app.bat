@echo off
cd /d "%~dp0"
echo Starting Handyman Market Research Dashboard on http://localhost:8765 ...
start "" "http://localhost:8765"
python app.py --port 8765
pause
