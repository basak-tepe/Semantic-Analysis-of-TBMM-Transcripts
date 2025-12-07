"""Configuration settings for the API."""
import os
from pathlib import Path

# Project root directory
PROJECT_ROOT = Path(__file__).parent.parent

# Elasticsearch configuration
ELASTICSEARCH_HOST = os.getenv("ELASTICSEARCH_HOST", "http://localhost:9200")
ELASTICSEARCH_INDEX = os.getenv("ELASTICSEARCH_INDEX", "parliament_speeches")

# CSV file paths
MP_LOOKUP_CSV = PROJECT_ROOT / "mp_lookup.csv"
TOPIC_SUMMARY_CSV = PROJECT_ROOT / "topic_summary.csv"

# Assets directory for t-SNE images
ASSETS_DIR = PROJECT_ROOT / "assets"

# CORS settings
CORS_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:3001",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:3001",
]

