# Incremental Speech Processing Pipeline Guide

## Overview

The incremental speech processing pipeline processes new sessions from the `TXTs_deepseek` folder, extracts speeches, adds only new ones to Elasticsearch, extracts keywords, generates embeddings, and assigns topics using incremental matching to existing clusters.

## Architecture

The pipeline consists of four main steps:

1. **Extract and Index Speeches**: Scans `TXTs_deepseek` for new sessions, extracts speeches using the appropriate script (d17-d22 or d23-d28), and indexes only new speeches to Elasticsearch.

2. **Extract Keywords**: Extracts keywords for speeches without keywords using the Aya Expanse 8B model.

3. **Generate Embeddings**: Generates embeddings for speeches with keywords using the Turkish embedding model.

4. **Assign Topics**: Matches speeches to existing topics using cosine similarity, or creates new clusters for unmatched speeches.

## Usage

### Basic Usage

Process all new sessions:

```bash
python scripts/incremental_speech_pipeline.py
```

### Process Specific Term

Process only term 28:

```bash
python scripts/incremental_speech_pipeline.py --term 28
```

### Process Specific Term and Year

Process only term 28, year 1:

```bash
python scripts/incremental_speech_pipeline.py --term 28 --year 1
```

### Dry Run

See what would be processed without making changes:

```bash
python scripts/incremental_speech_pipeline.py --dry-run
```

### Skip Steps

Skip keyword extraction:

```bash
python scripts/incremental_speech_pipeline.py --skip-keywords
```

Skip embedding generation:

```bash
python scripts/incremental_speech_pipeline.py --skip-embeddings
```

Skip topic assignment:

```bash
python scripts/incremental_speech_pipeline.py --skip-topics
```

### Custom TXTs Path

Use a different path for TXTs_deepseek:

```bash
python scripts/incremental_speech_pipeline.py --txts-path /path/to/TXTs_deepseek
```

## Configuration

The pipeline uses environment variables for configuration:

- `ELASTICSEARCH_HOST`: Elasticsearch host (default: `http://localhost:9200`)
- `ELASTICSEARCH_INDEX`: Elasticsearch index name (default: `parliament_speeches`)

Set them before running:

```bash
export ELASTICSEARCH_HOST="http://localhost:9200"
export ELASTICSEARCH_INDEX="parliament_speeches"
python scripts/incremental_speech_pipeline.py
```

## How It Works

### Step 1: Extract and Index Speeches

1. Scans `TXTs_deepseek` folder for sessions (terms 17-28)
2. For terms 17-22: Looks for `result.mmd` files in subfolders
3. For terms 23-28: Looks for `.txt` files (excluding `fih.txt` and `gnd.txt`)
4. Extracts speeches using the appropriate extraction function
5. Checks Elasticsearch for existing speeches by `_id` (format: `{session_id}-{speech_no}`)
6. Indexes only new speeches

### Step 2: Extract Keywords

1. Queries Elasticsearch for speeches without `keywords` field
2. Uses the keyword extraction script (`extract_speech_keywords.py`) to extract keywords
3. Updates Elasticsearch with `keywords` and `keywords_str` fields

**Note**: Currently, this step reports how many speeches need keywords and suggests running the keyword extraction script separately. Full integration can be added later.

### Step 3: Generate Embeddings

1. Queries Elasticsearch for speeches with `keywords_str` field
2. Loads Turkish embedding model (`trmteb/turkish-embedding-model-fine-tuned`)
3. Generates embeddings for speeches with keywords
4. Saves embeddings to `data/keyword_embeddings.npy` (appends if file exists)

### Step 4: Assign Topics

1. Loads existing topics from Elasticsearch
2. Calculates topic centroids from existing speeches (if embeddings available)
3. Matches new speeches to existing topics using cosine similarity
4. Creates new clusters for unmatched speeches
5. Updates Elasticsearch with `hdbscan_topic_id` and `hdbscan_topic_label`

**Note**: Full embedding-based topic matching requires a mapping file that maps `speech_id` to embedding index. Currently, the pipeline creates new clusters for all new speeches. This can be enhanced by maintaining a `speech_id -> embedding_index` mapping file.

## File Structure

```
scripts/
  ├── incremental_speech_pipeline.py  # Main pipeline orchestrator
  ├── topic_matcher.py                # Topic matching logic
  └── extract_speech_keywords.py     # Keyword extraction (existing)

src/
  ├── aciklamalar_d17-d22.py         # Extraction for terms 17-22
  └── aciklamalar_d23-d28.py         # Extraction for terms 23-28

data/
  ├── keyword_embeddings.npy         # Embeddings file (appended)
  └── speech_keywords.csv             # Keywords CSV (existing)
```

## Dependencies

- `elasticsearch`: Elasticsearch client
- `sentence-transformers`: For embedding generation
- `numpy`: For array operations
- `tqdm`: For progress bars
- `sklearn`: For cosine similarity calculations

Install dependencies:

```bash
pip install elasticsearch sentence-transformers numpy tqdm scikit-learn
```

## Troubleshooting

### "Could not import aciklamalar_d17-d22"

Make sure the `src` directory is in the Python path and the extraction scripts are available.

### "No sessions found"

Check that:
- The `TXTs_deepseek` folder exists
- The folder structure matches expected patterns (`d{term}-y{year}_TXTs` or `d{term}-y{year}_txts`)
- Files are in the correct format

### "Failed to connect to Elasticsearch"

- Ensure Elasticsearch is running
- Check the `ELASTICSEARCH_HOST` environment variable
- Verify network connectivity

### "Error loading embeddings"

- Ensure the embeddings file exists at `data/keyword_embeddings.npy`
- Check file permissions
- Verify the file is a valid numpy array

## Future Enhancements

1. **Full Keyword Integration**: Integrate keyword extraction directly into the pipeline instead of suggesting separate execution.

2. **Embedding Mapping File**: Maintain a `speech_id -> embedding_index` mapping file to enable proper embedding-based topic matching.

3. **Incremental Embedding Matching**: Load embeddings for existing speeches and use cosine similarity for topic matching instead of creating new clusters.

4. **Resume Capability**: Add checkpoint/resume functionality for long-running processes.

5. **Parallel Processing**: Process multiple sessions in parallel for faster execution.

6. **Error Recovery**: Better error handling and recovery for failed extractions.

## Related Scripts

- `scripts/extract_speech_keywords.py`: Standalone keyword extraction script
- `scripts/sync_updated_fields.py`: Sync updated fields to remote Elasticsearch
- `src/keyword_clustering_hdbscan.ipynb`: Full clustering notebook (for reference)

