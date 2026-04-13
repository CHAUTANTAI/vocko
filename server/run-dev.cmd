@echo off
REM PowerShell: from this folder use .\run-dev.cmd (not server\run-dev.cmd — PS treats "server" as a module name).
REM From repo root: .\server\run-dev.cmd
setlocal
cd /d "%~dp0"

echo [run-dev] pip install -r requirements.txt
python -m pip install -r requirements.txt
if errorlevel 1 exit /b 1

echo [run-dev] python src/init_indexes.py
python src/init_indexes.py
if errorlevel 1 exit /b 1

echo [run-dev] uvicorn src.main:app --reload --host 127.0.0.1 --port 8000
python -m uvicorn src.main:app --reload --host 127.0.0.1 --port 8000
exit /b %errorlevel%
