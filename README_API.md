# TBMM MP Analysis API

FastAPI backend for serving Member of Parliament analysis data to the frontend application.

## Setup

1. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Ensure Elasticsearch is Running**
   - Make sure Elasticsearch is running on `http://localhost:9200`
   - The index `parliament_speeches` should exist and contain data

3. **Ensure CSV Files Exist**
   - `mp_lookup.csv` - MP metadata (name, party, terms)
   - `topic_summary.csv` - Topic distribution data

## Running the API

```bash
# From project root
uvicorn api.main:app --reload --port 8000
```

The API will be available at `http://localhost:8000`

## API Endpoints

### List All MPs
```
GET /api/mps
```

Returns a list of all MPs with their ID, name, and party.

**Response:**
```json
{
  "mps": [
    {
      "id": "abc123",
      "name": "John Doe",
      "party": "Example Party"
    }
  ]
}
```

### Get MP Details
```
GET /api/mps/{mp_id}
```

Returns complete information about a specific MP including:
- Profile (name, party, terms)
- Top 4 topics with counts and percentages
- Activity by year (speeches, laws, votes)
- Political stance

**Response:**
```json
{
  "id": "abc123",
  "data": {
    "name": "John Doe",
    "party": "Example Party",
    "terms": ["2015-2019", "2019-2023"],
    "topics": [
      {
        "name": "Healthcare Reform",
        "count": 145,
        "percentage": 35.0
      }
    ],
    "activity": [
      {
        "year": "2015",
        "speeches": 45,
        "laws": 0,
        "votes": 0
      }
    ],
    "stance": "Member of Example Party with focus on Healthcare Reform..."
  }
}
```

### Health Check
```
GET /health
```

Returns API health status and Elasticsearch connection status.

## Configuration

Configuration can be modified in `api/config.py`:
- `ELASTICSEARCH_HOST` - Elasticsearch connection URL
- `ELASTICSEARCH_INDEX` - Index name
- `CORS_ORIGINS` - Allowed frontend origins

## Frontend Integration

The frontend should:
1. Fetch list of MPs from `GET /api/mps`
2. For each selected MP, fetch details from `GET /api/mps/{mp_id}`
3. Use the response data to populate the React components

The API response format matches the frontend's expected data structure.

