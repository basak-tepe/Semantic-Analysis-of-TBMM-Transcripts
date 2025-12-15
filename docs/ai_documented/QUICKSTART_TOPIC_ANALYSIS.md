# 🚀 Quick Start: Topic Analysis

## What Changed?

✅ **Updated Files:**
1. `scripts/create_elastic.py` - Added topic fields to ES mapping
2. `src/analyze_speech_topics.py` - Complete rewrite for ES integration
3. `api/services/elasticsearch_service.py` - Added topic query methods
4. `docs/topic_analysis_elasticsearch.md` - Full documentation

## 🎯 Quick Start

### Step 1: Ensure Elasticsearch is Running

```bash
# Check if ES is running
curl http://localhost:9200

# You should see something like:
# {
#   "name" : "...",
#   "cluster_name" : "elasticsearch",
#   "version" : { ... }
# }
```

### Step 2: (Optional) Update ES Mapping

If you want to recreate the index with new fields:

```bash
cd scripts
python create_elastic.py
```

**Note**: This will delete existing data! If you want to keep your data, skip this - the fields will be added dynamically.

### Step 3: Run Topic Analysis

```bash
cd src
python analyze_speech_topics.py
```

Expected time: **15-35 minutes** for 30k speeches

### Step 4: Verify Results

```bash
# Check if topics were added
curl -X GET "localhost:9200/parliament_speeches/_search?size=1&pretty" | grep topic

# You should see:
# "topic_id" : 5,
# "topic_label" : "0_ekonomi_bütçe_mali",
# "topic_probability" : 0.87
```

## 📊 What You Get

### 1. **Elasticsearch Documents** (Updated)
Every speech now has:
- `topic_id` - Numeric topic ID
- `topic_label` - Topic keywords (e.g., "0_ekonomi_bütçe_mali")
- `topic_probability` - Confidence score
- `topic_analyzed` - Boolean flag

### 2. **BERTopic Model** (`../bertopic_model/`)
Saved model for future analysis

### 3. **CSV Summary** (`../data/topic_summary.csv`)
Aggregated view: MP × Topic × Count

## 🔍 Query Examples

### Python API

```python
from api.services.elasticsearch_service import es_service

# Get all topics
topics = es_service.get_topic_statistics()

# Get MP's topic distribution
mp_topics = es_service.get_topics_by_mp("Ahmet Yılmaz")

# Search speeches by topic
speeches = es_service.search_speeches(topic_id=5, size=100)

# Multi-filter search
speeches = es_service.search_speeches(
    mp_name="Ahmet Yılmaz",
    topic_id=5,
    term=27
)
```

### Direct ES Query

```bash
# Get speeches in topic 5
curl -X GET "localhost:9200/parliament_speeches/_search" \
  -H 'Content-Type: application/json' -d'
{
  "query": {"term": {"topic_id": 5}},
  "size": 10
}'
```

### Using Pandas

```python
import pandas as pd

# Load summary
summary = pd.read_csv('../data/topic_summary.csv')

# Top topics for MP
mp_data = summary[summary['speech_giver'] == 'Ahmet Yılmaz']
print(mp_data.nlargest(10, 'speech_count'))
```

## 🎨 Visualize Topics

```python
from bertopic import BERTopic

# Load model
model = BERTopic.load("../bertopic_model")

# Interactive visualization
fig = model.visualize_topics()
fig.write_html("topics.html")

# Topic hierarchy
fig = model.visualize_hierarchy()
fig.write_html("hierarchy.html")

# Topic over time (if you have dates)
fig = model.visualize_topics_over_time(topics_over_time)
fig.write_html("timeline.html")
```

## ⚡ Performance

| Dataset Size | Time | Memory |
|-------------|------|--------|
| 10k speeches | 5-10 min | 2-3 GB |
| 30k speeches | 15-35 min | 4-8 GB |
| 100k speeches | 1-2 hours | 8-16 GB |

## 🐛 Troubleshooting

### ES Not Connected
```bash
# Check ES status
docker ps | grep elastic
# OR
systemctl status elasticsearch
```

### Out of Memory
```python
# In analyze_speech_topics.py, reduce batch size:
BATCH_SIZE = 500  # Instead of 1000
```

### Topics Don't Update
```bash
# Force refresh ES index
curl -X POST "localhost:9200/parliament_speeches/_refresh"
```

## 📖 Full Documentation

See `docs/topic_analysis_elasticsearch.md` for:
- Detailed architecture
- Advanced usage
- API integration examples
- Troubleshooting guide

## 🎯 Next Steps

1. ✅ Run `python analyze_speech_topics.py`
2. 📊 Check results in ES
3. 🔍 Query topics via API
4. 📈 Create visualizations
5. 🎨 Build dashboard

---

**Need Help?** Check the full docs: `docs/topic_analysis_elasticsearch.md`
