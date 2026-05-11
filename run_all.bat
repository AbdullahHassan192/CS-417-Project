@echo off
echo ========================================================
echo    TALASH Milestone 3 - One-Click Runner
echo    Full Integrated System: Auth + DB + Analysis + UI
echo ========================================================
echo.

echo [1/6] Installing Python dependencies...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo Error installing Python dependencies. Make sure Python is installed.
    pause
    exit /b %errorlevel%
)
echo.

echo [2/6] Installing M3 extra dependencies...
pip install python-jose passlib aiosqlite sqlalchemy cryptography bcrypt numpy
if %errorlevel% neq 0 (
    echo Warning: Some M3 dependencies may have failed. Continuing...
)
echo.

echo [3/6] Initializing Database and Seeding Data...
python manage.py seed --csv-dir ./output --assessments-dir ./data/candidates_assessments
if %errorlevel% neq 0 (
    echo Warning: DB seed had issues. The app will still start but may have empty data.
)
echo.

echo [4/6] Running M2/M3 Analysis Batch Processor...
python -m analysis.batch_processor --input-csvs ./output --output ./data/candidates_assessments
echo.

echo [5/6] Starting FastAPI Backend (in new window)...
start cmd /k "title TALASH M3 Backend && color 0A && echo. && echo ============================= && echo  TALASH M3 Backend Server && echo  http://localhost:8000 && echo  API Docs: http://localhost:8000/docs && echo ============================= && echo. && uvicorn backend.main:app --reload --port 8000"
echo.

echo [6/6] Installing Frontend deps and starting React (in new window)...
cd frontend
call npm install
if %errorlevel% neq 0 (
    echo Error installing Node.js dependencies. Make sure Node.js and npm are installed.
    pause
    exit /b %errorlevel%
)
start cmd /k "title TALASH M3 Frontend && color 0B && echo. && echo ============================= && echo  TALASH M3 Frontend && echo  http://localhost:5173 && echo ============================= && echo. && npm run dev -- --open"
cd ..

echo.
echo ========================================================
echo   Setup complete! Both servers are starting up.
echo.
echo   Backend API:   http://localhost:8000
echo   API Docs:      http://localhost:8000/docs
echo   Frontend UI:   http://localhost:5173
echo.
echo   Login:  admin@talash.ai / talash2025
echo ========================================================
pause
