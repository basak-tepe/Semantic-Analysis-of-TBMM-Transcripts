#!/bin/bash
# Start the FastAPI server using the virtual environment's Python

cd "$(dirname "$0")"
source myenv/bin/activate
python3.11 -m uvicorn api.main:app --reload --port 8000

