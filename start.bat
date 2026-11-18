@echo off
cd /d "%~dp0"
start "" http://localhost:5178
python server.py 5178
