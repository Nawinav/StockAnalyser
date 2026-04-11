@echo off
:: Start the backend server (must have run setup.bat first)
cd /d "%~dp0backend"
call venv\Scripts\activate.bat
echo Starting Indian Stock Analyser backend on http://localhost:8000 ...
echo API docs: http://localhost:8000/docs
echo.
python run.py
pause
