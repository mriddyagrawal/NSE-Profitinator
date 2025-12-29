@echo off
REM Navigate to script directory
cd /d "%~dp0"

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Launch Streamlit app
streamlit run streamlit_app.py

REM Keep window open on error
pause
