@echo off
echo 🚀 Starting Store Monitoring System...
echo.

echo 📦 Activating virtual environment...
call venv\Scripts\activate.bat

echo 🌐 Starting FastAPI server...
echo Frontend will be available at: http://localhost:8000/static/index.html
echo API docs available at: http://localhost:8000/docs
echo.
echo Press Ctrl+C to stop the server
echo.

uvicorn app.main:app --reload
