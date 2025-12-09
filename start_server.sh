#!/bin/bash
# Start the FastAPI server using the virtual environment's Python

cd "$(dirname "$0")"
source venv/bin/activate
python -m uvicorn api.main:app --reload --port 8000

