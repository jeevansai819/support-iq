@echo off
echo ========================================
echo   SupportIQ - AI Customer Support
echo ========================================
echo.

REM Check that Ollama is running
echo [1/3] Checking Ollama...
curl -s http://localhost:11434 >nul 2>&1
if %errorlevel% neq 0 (
    echo WARNING: Ollama does not appear to be running.
    echo          AI Analysis will not be available until Ollama is started.
    echo          Start Ollama and run: ollama pull llama3.2:3b
    echo.
)

REM Start the FastAPI backend in a new window
echo [2/3] Starting FastAPI backend on http://127.0.0.1:8000 ...
start "SupportIQ Backend" cmd /k "cd /d %~dp0 && venv\Scripts\uvicorn.exe backend.main:app --host 127.0.0.1 --port 8000 --reload"

REM Small delay to let the backend start
timeout /t 3 /nobreak >nul

REM Start the Streamlit frontend
echo [3/3] Starting Streamlit frontend on http://localhost:8501 ...
start "SupportIQ Frontend" cmd /k "cd /d %~dp0 && venv\Scripts\streamlit.exe run frontend\app.py"

echo.
echo ========================================
echo   SupportIQ is starting up!
echo   Backend:  http://127.0.0.1:8000
echo   Frontend: http://localhost:8501
echo   API Docs: http://127.0.0.1:8000/docs
echo ========================================
echo.
pause
