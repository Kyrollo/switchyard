@echo off
title Switchyard - Private LLM Gateway
cls
echo ========================================================
echo       Switchyard - Private LLM Gateway & Load Balancer
echo ========================================================
echo.
echo [1/3] Checking environment & Ollama...
python -c "import uvicorn, fastapi" 2>nul || pip install fastapi uvicorn
if not exist "frontend\node_modules" (
    echo Installing frontend dependencies...
    cd frontend && npm install && cd ..
)

echo [2/3] Starting Backend API (Port 8001)...
start "Switchyard API (Port 8001)" cmd /k "cd /d %~dp0backend && python -m uvicorn src.switchyard.main:app --port 8001 --reload"

echo [3/3] Starting Frontend UI (Port 3001)...
start "Switchyard UI (Port 3001)" cmd /k "cd /d %~dp0frontend && npm run dev"

timeout /t 3 /nobreak >nul
start http://localhost:3001
echo.
echo Switchyard is running!
echo   Frontend : http://localhost:3001
echo   Backend  : http://localhost:8001/docs
echo.
echo Press any key to stop all Switchyard processes...
pause >nul
taskkill /fi "WINDOWTITLE eq Switchyard API*" /f >nul 2>&1
taskkill /fi "WINDOWTITLE eq Switchyard UI*" /f >nul 2>&1
echo Done.
