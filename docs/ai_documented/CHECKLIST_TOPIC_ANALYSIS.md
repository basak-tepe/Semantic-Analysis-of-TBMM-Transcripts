# ✅ Topic Analysis - Implementation Checklist

## Pre-flight Checklist

Before running topic analysis, verify:

- [ ] Elasticsearch is running on port 9200
  ```bash
  curl http://localhost:9200
  ```

- [ ] `parliament_speeches` index exists with data
  ```bash
  curl http://localhost:9200/parliament_speeches/_count
  ```

- [ ] Python dependencies installed
  ```bash
  pip install elasticsearch bertopic pandas plotly
  ```

- [ ] Run pre-flight check
  ```bash
  cd src
  python test_es_connection.py
  ```

---

## Execution Checklist

### Phase 1: Run Analysis

- [ ] Navigate to src directory
  ```bash
  cd src
  ```

- [ ] Run topic analysis script
  ```bash
  python analyze_speech_topics.py
  ```

- [ ] Monitor progress (15-35 minutes)
  - ✅ Connected to Elasticsearch
  - ✅ Fetched speeches
  - ✅ Training BERTopic (longest step)
  - ✅ Updated Elasticsearch
  - ✅ Saved model and summary

### Phase 2: Verify Results

- [ ] Check Elasticsearch for topic fields
  ```bash
  curl -X GET "localhost:9200/parliament_speeches/_search?size=1&pretty" | grep topic
  ```

- [ ] Verify BERTopic model saved
  ```bash
  ls -lh ../bertopic_model/
  ```

- [ ] Check CSV summary created
  ```bash
  ls -lh ../data/topic_summary.csv
  wc -l ../data/topic_summary.csv
  ```

### Phase 3: Test Queries

- [ ] Test Python API queries
  ```python
  from api.services.elasticsearch_service import es_service
  topics = es_service.get_topic_statistics()
  print(f"Found {len(topics)} topics")
  ```

- [ ] Test direct ES query
  ```bash
  curl -X GET "localhost:9200/parliament_speeches/_search?q=topic_id:0&size=1"
  ```

- [ ] Test topic filtering
  ```python
  speeches = es_service.search_speeches(topic_id=5, size=10)
  print(f"Found {len(speeches['speeches'])} speeches in topic 5")
  ```

---

## Verification Tests

### Test 1: Topic Statistics
```python
topics = es_service.get_topic_statistics()
assert len(topics) > 0, "No topics found!"
assert topics[0]['speech_count'] > 0, "Topic has no speeches!"
print(f"✅ Found {len(topics)} topics")
```

### Test 2: MP Topics
```python
# Use a known MP from your data
mp_topics = es_service.get_topics_by_mp("Ahmet Yılmaz")
if mp_topics:
    print(f"✅ Found {len(mp_topics)} topics for MP")
else:
    print("⚠️  No topics found - try different MP name")
```

### Test 3: Search with Topic Filter
```python
speeches = es_service.search_speeches(topic_id=0, size=10)
total = speeches['total']
results = len(speeches['speeches'])
print(f"✅ Topic 0 has {total} speeches (fetched {results})")
```

### Test 4: CSV Summary
```python
import pandas as pd
summary = pd.read_csv('../data/topic_summary.csv')
print(f"✅ CSV has {len(summary)} rows")
print(f"✅ Columns: {list(summary.columns)}")
```

---

## Troubleshooting Checklist

### If Connection Fails

- [ ] Check if Elasticsearch is running
  ```bash
  docker ps | grep elastic
  # OR
  systemctl status elasticsearch
  ```

- [ ] Check port 9200 is accessible
  ```bash
  netstat -an | grep 9200
  ```

- [ ] Try restarting Elasticsearch
  ```bash
  docker restart elasticsearch
  ```

### If Analysis Fails

- [ ] Check available memory (need 4-8 GB)
  ```bash
  free -h  # Linux
  top  # Mac
  ```

- [ ] Reduce batch size in `analyze_speech_topics.py`
  ```python
  BATCH_SIZE = 500  # Instead of 1000
  ```

- [ ] Check Python dependencies
  ```bash
  pip list | grep -E "elasticsearch|bertopic|pandas"
  ```

### If Topics Not Saved

- [ ] Check for errors in output
- [ ] Verify ES write permissions
- [ ] Refresh the index
  ```bash
  curl -X POST "localhost:9200/parliament_speeches/_refresh"
  ```

- [ ] Check if documents were updated
  ```bash
  curl -X GET "localhost:9200/parliament_speeches/_search" \
    -H 'Content-Type: application/json' -d'
  {
    "query": {"exists": {"field": "topic_id"}},
    "size": 0
  }'
  ```

---

## Success Criteria

✅ Analysis is successful when:

1. Script completes without errors
2. BERTopic model saved to `../bertopic_model/`
3. CSV summary created at `../data/topic_summary.csv`
4. ES documents have `topic_id`, `topic_label`, `topic_probability` fields
5. `es_service.get_topic_statistics()` returns topics
6. Topic count matches expected number (~30-50 topics for 30k speeches)

---

## Post-Analysis Tasks

After successful analysis:

- [ ] Review discovered topics
  ```python
  from bertopic import BERTopic
  model = BERTopic.load("../bertopic_model")
  print(model.get_topic_info())
  ```

- [ ] Create visualizations
  ```python
  fig = model.visualize_topics()
  fig.write_html("topics_visualization.html")
  ```

- [ ] Update API routes (if needed) to expose topics

- [ ] Build frontend dashboard to display topics

- [ ] Analyze topic trends over time

---

## Quick Reference

| Task | Command |
|------|---------|
| Test connection | `python src/test_es_connection.py` |
| Run analysis | `python src/analyze_speech_topics.py` |
| Check ES count | `curl http://localhost:9200/parliament_speeches/_count` |
| Load model | `BERTopic.load("../bertopic_model")` |
| Load summary | `pd.read_csv("../data/topic_summary.csv")` |
| Get topics | `es_service.get_topic_statistics()` |

---

## Expected Timeline

| Phase | Duration | Notes |
|-------|----------|-------|
| Pre-flight check | 1 min | `test_es_connection.py` |
| Fetch from ES | 1-2 min | Scroll API |
| BERTopic training | 10-30 min | Main bottleneck |
| Update ES | 2-3 min | Bulk updates |
| Export CSV | 1 min | Pandas |
| **Total** | **15-35 min** | For 30k speeches |

---

## Resources

- **Quick Start**: `QUICKSTART_TOPIC_ANALYSIS.md`
- **Full Documentation**: `docs/topic_analysis_elasticsearch.md`
- **Implementation Summary**: `SUMMARY_TOPIC_ANALYSIS.md`
- **BERTopic Docs**: https://maartengr.github.io/BERTopic/

---

**Ready to start?** 
```bash
cd src && python test_es_connection.py
```
