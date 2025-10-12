# Semantic Analysis of TBMM Transcripts

This project aims to perform semantic analysis on Turkish Grand National Assembly (TBMM) transcripts.

## Setup

1. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Setup Elasticsearch**
   - Follow the instructions in `docs/build_elasticsearch.md`
   - Run the Elasticsearch Docker container
   - Create the index using `scripts/create_elastic.py`

3. **Run Analysis**
   
   **Step 1: Load Data into Elasticsearch**
   ```bash
   # Make sure Elasticsearch is running (Docker container)
   python src/aciklamalar_d25-d28.py
   ```
   **Step 2: Perform Topic Analysis**
   ```bash
   python src/analyze_speech_topics.py
   ```
   
   **Step 3: Generate Parliament Galaxy Visualization**
   ```bash
   python src/parliament_galaxy.py
   ```

## Features

- **Data Scraping**: Extract transcripts from TBMM website
- **Elasticsearch Integration**: Store and search parliamentary speeches
- **Semantic Analysis**: Analyze speech topics and patterns
- **Data Visualization**: Generate insights from parliamentary data

## Requirements

- Python
- Elasticsearch 8.6.1
- Docker (for Elasticsearch)

## Usage

See individual script files in `src/` directory for specific functionality.
