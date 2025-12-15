# Topic Analysis with Elasticsearch Integration

## Overview

This system performs topic analysis on parliament speeches using BERTopic and stores the results directly in Elasticsearch for efficient querying.

## Architecture

```
┌─────────────────────┐
│  Elasticsearch      │
│  (localhost:9200)   │
│                     │
│  Index:             │
│  parliament_speeches│
│                     │
│  30k+ documents     │
└──────────┬──────────┘
           │
           │ 1. Fetch speeches
           │    (scroll API)
           ▼
┌─────────────────────┐
│ analyze_speech_     │
│ topics.py           │
│                     │
│ • BERTopic Model    │
│ • Turkish language  │
│ • Auto topics       │
└──────────┬──────────┘
           │
           │ 2. Analyze & assign topics
           │
           ▼
┌─────────────────────┐
│  Elasticsearch      │
│  (Updated docs)     │
│                     │
│  + topic_id         │
│  + topic_label      │
│  + topic_probability│
└─────────────────────┘
```

## Features

### 1. **Elasticsearch Storage** ✅
- Topics stored directly in speech documents
- No separate database needed
- Efficient querying by topic
- Scales to millions of documents

### 2. **New Fields Added to Index**
```json
{
  "topic_id": 5,
  "topic_label": "0_ekonomi_bütçe_mali_vergi",
  "topic_probability": 0.87,
  "topic_analyzed": true
}
```

### 3. **Efficient Data Retrieval**
- Uses Elasticsearch scroll API for large datasets
- Batch processing (1000 speeches per batch)
- Memory-efficient streaming

### 4. **Automatic Topic Discovery**
- BERTopic automatically determines optimal number of topics
- Turkish language support
- Topic labels based on most representative words

---

## Installation & Setup

### 1. Install Dependencies

```bash
pip install elasticsearch bertopic pandas plotly
```

### 2. Update Elasticsearch Mapping

First, update your index mapping to include topic fields:

```bash
cd scripts
python create_elastic.py
```

**Note**: If you already have data in Elasticsearch, you'll need to either:
- Reindex with the new mapping, OR
- The new fields will be added dynamically when you run topic analysis

### 3. Verify Elasticsearch Connection

```bash
# Check if Elasticsearch is running
curl http://localhost:9200

# Check your index
curl http://localhost:9200/parliament_speeches/_count
```

---

## Usage

### Run Topic Analysis

```bash
cd src
python analyze_speech_topics.py
```

### Expected Output

```
================================================================================
PARLIAMENT SPEECH TOPIC ANALYSIS
================================================================================

🔌 Connecting to Elasticsearch at http://localhost:9200...
✅ Connected to Elasticsearch
📊 Index: parliament_speeches
📊 Total documents: 30,000

📥 Fetching speeches from Elasticsearch...
   Batch 1: Processing 1000 speeches...
   Batch 2: Processing 1000 speeches...
   ...
✅ Successfully fetched 30,000 speeches with valid content

⚙️  Training BERTopic model on 30,000 speeches...
   This may take several minutes depending on your hardware...
✅ Model trained and saved to ../bertopic_model
📊 Discovered 45 topics (excluding outliers)
📊 Outliers: 1,234 speeches

💾 Updating Elasticsearch with topic assignments...
   Updating 30,000 documents...
✅ Successfully updated 30,000 documents

📊 Creating topic summary...
✅ Topic summary saved to ../data/topic_summary.csv
   Total rows: 8,765

📈 Generating topic visualization...

🏆 Top 10 Topics:
================================================================================
Topic 0: 0_ekonomi_bütçe_mali_vergi
   Count: 3,456 speeches

Topic 1: 1_eğitim_okul_öğrenci_öğretmen
   Count: 2,789 speeches

Topic 2: 2_sağlık_hastane_doktor_hasta
   Count: 2,134 speeches
...

================================================================================
✅ TOPIC ANALYSIS COMPLETE!
================================================================================
📊 Total speeches analyzed: 30,000
📊 Documents updated in ES: 30,000
📊 Model saved to: ../bertopic_model
📊 Summary saved to: ../data/topic_summary.csv
================================================================================
```

---

## Querying Topics

### 1. **Using Python API**

```python
from api.services.elasticsearch_service import es_service

# Get all topics with statistics
topics = es_service.get_topic_statistics()
# Returns: [{'topic_id': 0, 'topic_label': '0_ekonomi_...', 'speech_count': 3456}, ...]

# Get topics for specific MP
mp_topics = es_service.get_topics_by_mp("Ahmet Yılmaz")
# Returns MP's topic distribution

# Search speeches by topic
speeches = es_service.search_speeches(topic_id=5, size=100)
# Returns all speeches in topic 5

# Search with multiple filters
speeches = es_service.search_speeches(
    mp_name="Ahmet Yılmaz",
    topic_id=5,
    term=27,
    size=50
)
# Returns: Ahmet Yılmaz's speeches in topic 5 during term 27
```

### 2. **Direct Elasticsearch Queries**

```bash
# Get speeches by topic
curl -X GET "localhost:9200/parliament_speeches/_search" -H 'Content-Type: application/json' -d'
{
  "query": {
    "term": {"topic_id": 5}
  },
  "size": 100
}'

# Get topic statistics
curl -X GET "localhost:9200/parliament_speeches/_search" -H 'Content-Type: application/json' -d'
{
  "size": 0,
  "aggs": {
    "topics": {
      "terms": {
        "field": "topic_id",
        "size": 100
      }
    }
  }
}'

# Get MP's topic distribution
curl -X GET "localhost:9200/parliament_speeches/_search" -H 'Content-Type: application/json' -d'
{
  "size": 0,
  "query": {
    "match": {"speech_giver": "Ahmet Yılmaz"}
  },
  "aggs": {
    "topics": {
      "terms": {
        "field": "topic_id",
        "size": 20
      }
    }
  }
}'
```

### 3. **Using Pandas for Analysis**

```python
import pandas as pd

# Load the summary CSV
summary = pd.read_csv('../data/topic_summary.csv')

# Get top topics for specific MP
mp_topics = summary[summary['speech_giver'] == 'Ahmet Yılmaz']
mp_topics.nlargest(10, 'speech_count')

# Get most active MPs on specific topic
topic_5 = summary[summary['topic_id'] == 5]
topic_5.nlargest(10, 'speech_count')
```

---

## Performance

### Timing Estimates (for 30k speeches)

| Task | Estimated Time | Notes |
|------|---------------|-------|
| Fetch from ES | 1-2 minutes | Using scroll API |
| BERTopic Training | 10-30 minutes | Depends on GPU/CPU |
| Update ES | 2-3 minutes | Bulk updates |
| **Total** | **15-35 minutes** | One-time process |

### Memory Usage

- **Peak memory**: ~4-8 GB (during BERTopic training)
- **ES storage**: +200-300 bytes per document for topic fields
- **Total increase**: ~6-9 MB for 30k documents

---

## Output Files

### 1. **BERTopic Model** (`../bertopic_model/`)
- Saved model for future use
- Can be loaded to analyze new speeches
- Contains all topic information

### 2. **Topic Summary CSV** (`../data/topic_summary.csv`)

```csv
speech_giver,topic_id,topic_label,speech_count,term,year
Ahmet Yılmaz,5,0_ekonomi_bütçe_mali,45,"[26, 27]","[3, 4]"
Mehmet Ali,5,0_ekonomi_bütçe_mali,32,"[27]","[4]"
```

**Columns:**
- `speech_giver`: MP name
- `topic_id`: Numeric topic ID
- `topic_label`: Topic keywords
- `speech_count`: Number of speeches
- `term`: Parliamentary terms (list)
- `year`: Years (list)

### 3. **Elasticsearch Documents** (Updated)

Each speech document now has:
```json
{
  "_id": "term27-year4-session001-1",
  "_source": {
    "speech_giver": "Ahmet Yılmaz",
    "content": "...",
    "term": 27,
    "year": 4,
    "topic_id": 5,
    "topic_label": "0_ekonomi_bütçe_mali_vergi",
    "topic_probability": 0.87,
    "topic_analyzed": true
  }
}
```

---

## Advanced Usage

### Re-run Topic Analysis

If you want to re-analyze with different parameters:

```python
# Edit analyze_speech_topics.py to change BERTopic parameters
topic_model = BERTopic(
    language="turkish",
    nr_topics=50,  # Fixed number of topics
    min_topic_size=50,  # Minimum speeches per topic
    verbose=True
)
```

### Load Existing Model

```python
from bertopic import BERTopic

# Load saved model
topic_model = BERTopic.load("../bertopic_model")

# Use for new speeches
new_topics, new_probs = topic_model.transform(["yeni konuşma metni"])
```

### Export Topics for Visualization

```python
from bertopic import BERTopic

model = BERTopic.load("../bertopic_model")

# Get topic visualization
fig = model.visualize_topics()
fig.write_html("topics_visualization.html")

# Get topic hierarchy
fig = model.visualize_hierarchy()
fig.write_html("topics_hierarchy.html")
```

---

## Troubleshooting

### Issue: "Cannot connect to Elasticsearch"

**Solution:**
```bash
# Check if ES is running
docker ps  # If using Docker
# OR
curl http://localhost:9200

# Start ES if needed
docker start elasticsearch
```

### Issue: "Out of memory during BERTopic training"

**Solutions:**
1. Process in smaller batches
2. Reduce model complexity:
   ```python
   topic_model = BERTopic(
       language="turkish",
       calculate_probabilities=False,  # Reduces memory
       nr_topics=30  # Fewer topics
   )
   ```
3. Use a smaller subset for testing

### Issue: "Slow performance"

**Solutions:**
1. Increase batch size in scroll API
2. Use GPU for BERTopic (if available)
3. Run during off-peak hours

### Issue: "Topics don't make sense"

**Solutions:**
1. Increase `min_topic_size` parameter
2. Clean/preprocess text more thoroughly
3. Remove outlier topics (topic_id = -1)

---

## Integration with API

The updated `elasticsearch_service.py` now supports:

### New API Methods

```python
# Get all topics
GET /api/topics
# Returns: List of all topics with counts

# Get MP's topics
GET /api/mp/{name}/topics
# Returns: Topic distribution for MP

# Search with topic filter
GET /api/speeches?topic_id=5&term=27
# Returns: Speeches filtered by topic and term
```

---

## Benefits Over CSV Approach

| Feature | CSV | Elasticsearch |
|---------|-----|---------------|
| Storage | Separate file | Integrated |
| Querying | pandas filters | ES queries |
| Performance | Load entire file | Index-based |
| Scalability | < 1M rows | Billions of docs |
| Updates | Reload entire file | Update single doc |
| Multi-filter | Complex code | Simple queries |
| API Integration | File I/O overhead | Direct connection |

---

## Next Steps

1. ✅ Run topic analysis
2. ✅ Verify topics in Elasticsearch
3. ✅ Query topics via API
4. 📊 Create topic visualization dashboard
5. 📊 Analyze topic trends over time
6. 📊 Compare MP topic distributions

---

## Related Documentation

- [BERTopic Documentation](https://maartengr.github.io/BERTopic/)
- [Elasticsearch Python Client](https://elasticsearch-py.readthedocs.io/)
- [API Services](../api/services/elasticsearch_service.py)

---

## Notes

- Topic IDs are assigned automatically by BERTopic
- Topic -1 represents outliers (speeches that don't fit any topic)
- Topic labels are generated from most representative words
- Re-running analysis will reassign topics (may differ slightly)
- Model can be updated incrementally as new speeches are added
