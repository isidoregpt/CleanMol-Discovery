@echo off
echo Starting CleanMol Backend...

if not exist .venv (
    echo Creating virtual environment...
    python -m venv .venv
)

echo Activating virtual environment...
call .venv\Scripts\activate

echo Installing dependencies...
pip install -r requirements.txt

echo Starting server on http://localhost:8787
uvicorn app.main:app --reload --port 8787
