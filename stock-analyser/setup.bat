@echo off
:: Indian Stock Analyser — Windows Setup Script
:: Run this once to install all dependencies.

echo ============================================================
echo  Indian Stock Analyser — Setup
echo ============================================================
echo.

:: ── Backend ──────────────────────────────────────────────────────────────────
echo [1/4] Setting up Python backend...
cd /d "%~dp0backend"

python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python 3.11+ is required. Download from https://python.org
    pause
    exit /b 1
)

echo Creating virtual environment...
python -m venv venv

echo Activating virtual environment...
call venv\Scripts\activate.bat

echo Installing Python dependencies...
pip install --upgrade pip
pip install -r requirements.txt

echo Copying .env.example to .env...
if not exist .env copy .env.example .env

echo Backend setup complete.
echo.

:: ── Frontend ─────────────────────────────────────────────────────────────────
echo [2/4] Setting up React Native frontend...
cd /d "%~dp0frontend"

node --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Node.js 18+ is required. Download from https://nodejs.org
    pause
    exit /b 1
)

echo Installing Node dependencies...
npm install

echo Frontend setup complete.
echo.

echo ============================================================
echo  Setup finished!
echo ============================================================
echo.
echo  Next Steps:
echo  1. Start the backend:
echo       cd backend
echo       venv\Scripts\activate
echo       python run.py
echo.
echo  2. In a new terminal, start the mobile app:
echo       cd frontend
echo       npx expo start
echo       Press 'w' for web, 'a' for Android, 'i' for iOS
echo.
echo  3. To trigger the stock analysis manually, open:
echo       http://localhost:8000/docs
echo       POST /api/recommendations/trigger
echo.
echo  4. The automatic analysis runs every weekday at 08:30 AM IST.
echo ============================================================
pause
