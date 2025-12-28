# Elasticsearch Keyword Fields for Aggregations

## Overview

This guide explains how to make `speech_giver` and other text fields filterable for aggregations in Elasticsearch.

---

## 📚 Background: Text vs Keyword Fields

### Text Fields (Default)
- **Purpose**: Full-text search
- **Analyzed**: Tokenized into terms
- **Example**: "Özgür Özel" → ["özgür", "özel"]
- **Good for**: Searching with `match` queries
- **Bad for**: Aggregations, exact matching, sorting

### Keyword Fields
- **Purpose**: Structured data, filtering, aggregations
- **Not analyzed**: Stored as-is
- **Example**: "Özgür Özel" → "Özgür Özel"
- **Good for**: Aggregations, exact matching, sorting
- **Bad for**: Full-text search

---

## ❓ Why You Need Keyword Fields

When you try to aggregate on a text field, you get:
```json
{
  "error": {
    "type": "illegal_argument_exception",
    "reason": "Fielddata is disabled on text fields by default"
  }
}
```

**Solution**: Use a multi-field mapping with both `text` and `keyword` types.

---

## 🔧 Implementation

### Step 1: Run the Update Script

```bash
cd scripts/
python update_speech_giver_mapping.py
```

**What it does:**
1. Checks current mapping
2. Adds `speech_giver.keyword` subfield
3. Tests aggregation
4. Shows usage examples

### Step 2: Verify the Mapping

```bash
curl -X GET "http://localhost:9200/parliament_speeches/_mapping"
```

**Expected result:**
```json
{
  "parliament_speeches": {
    "mappings": {
      "properties": {
        "speech_giver": {
          "type": "text",
          "fields": {
            "keyword": {
              "type": "keyword",
              "ignore_above": 256
            }
          }
        }
      }
    }
  }
}
```

---

## 📊 Using Keyword Fields for Aggregations

### 1. Get Top Speakers

```python
from elasticsearch import Elasticsearch

es = Elasticsearch(hosts=["http://localhost:9200"])

query = {
    "size": 0,
    "aggs": {
        "top_speakers": {
            "terms": {
                "field": "speech_giver.keyword",  # ← Use .keyword
                "size": 100
            }
        }
    }
}

result = es.search(index="parliament_speeches", body=query)

for bucket in result['aggregations']['top_speakers']['buckets']:
    print(f"{bucket['key']}: {bucket['doc_count']} speeches")
```

**Output:**
```
Özgür Özel: 291 speeches
Engin Altay: 134 speeches
Erkan Akçay: 80 speeches
```

### 2. Filter by Specific MP (Exact Match)

```python
query = {
    "query": {
        "term": {
            "speech_giver.keyword": "Özgür Özel"  # ← Exact match
        }
    }
}

result = es.search(index="parliament_speeches", body=query)
```

### 3. Filter by Multiple MPs

```python
query = {
    "query": {
        "terms": {
            "speech_giver.keyword": [
                "Özgür Özel",
                "Devlet Bahçeli",
                "Meral Akşener"
            ]
        }
    }
}

result = es.search(index="parliament_speeches", body=query)
```

### 4. Aggregate by MP and Term

```python
query = {
    "size": 0,
    "aggs": {
        "by_speaker": {
            "terms": {
                "field": "speech_giver.keyword",
                "size": 50
            },
            "aggs": {
                "by_term": {
                    "terms": {
                        "field": "term"
                    }
                }
            }
        }
    }
}

result = es.search(index="parliament_speeches", body=query)
```

### 5. Count Unique Speakers

```python
query = {
    "size": 0,
    "aggs": {
        "unique_speakers": {
            "cardinality": {
                "field": "speech_giver.keyword"
            }
        }
    }
}

result = es.search(index="parliament_speeches", body=query)
unique_count = result['aggregations']['unique_speakers']['value']
print(f"Total unique speakers: {unique_count}")
```

---

## 🔍 API Integration Example

### Flask/FastAPI Endpoint

```python
from elasticsearch import Elasticsearch
from fastapi import APIRouter, Query
from typing import List, Optional

router = APIRouter()
es = Elasticsearch(hosts=["http://localhost:9200"])

@router.get("/api/speakers/stats")
async def get_speaker_stats(
    top_n: int = Query(100, description="Number of top speakers"),
    min_speeches: int = Query(1, description="Minimum speech count")
):
    """Get top speakers by speech count."""
    
    query = {
        "size": 0,
        "aggs": {
            "speakers": {
                "terms": {
                    "field": "speech_giver.keyword",
                    "size": top_n,
                    "min_doc_count": min_speeches
                }
            }
        }
    }
    
    result = es.search(index="parliament_speeches", body=query)
    
    speakers = [
        {
            "name": bucket['key'],
            "speech_count": bucket['doc_count']
        }
        for bucket in result['aggregations']['speakers']['buckets']
    ]
    
    return {
        "total_speakers": len(speakers),
        "speakers": speakers
    }


@router.get("/api/speakers/{speaker_name}/speeches")
async def get_speaker_speeches(
    speaker_name: str,
    term: Optional[int] = None,
    page: int = 1,
    limit: int = 50
):
    """Get speeches for a specific speaker."""
    
    # Build query
    must_clauses = [
        {"term": {"speech_giver.keyword": speaker_name}}
    ]
    
    if term:
        must_clauses.append({"term": {"term": term}})
    
    query = {
        "query": {
            "bool": {
                "must": must_clauses
            }
        },
        "from": (page - 1) * limit,
        "size": limit,
        "sort": [
            {"session_date": {"order": "desc"}}
        ]
    }
    
    result = es.search(index="parliament_speeches", body=query)
    
    return {
        "speaker": speaker_name,
        "total": result['hits']['total']['value'],
        "speeches": [hit['_source'] for hit in result['hits']['hits']]
    }
```

---

## 🎯 Common Use Cases

### 1. MP Dashboard - Get MP's Speech Count by Term

```python
def get_mp_activity(mp_name: str):
    query = {
        "size": 0,
        "query": {
            "term": {"speech_giver.keyword": mp_name}
        },
        "aggs": {
            "by_term": {
                "terms": {
                    "field": "term",
                    "size": 50
                }
            }
        }
    }
    
    result = es.search(index="parliament_speeches", body=query)
    
    activity = {}
    for bucket in result['aggregations']['by_term']['buckets']:
        activity[bucket['key']] = bucket['doc_count']
    
    return activity
```

### 2. Party Analysis - Get All Speakers by Party

```python
def get_speakers_by_party(party_list: List[str]):
    """
    Get all unique speakers who served in given parties.
    Uses the political_party.keyword field.
    """
    query = {
        "size": 0,
        "query": {
            "terms": {"political_party.keyword": party_list}
        },
        "aggs": {
            "speakers": {
                "terms": {
                    "field": "speech_giver.keyword",
                    "size": 1000
                }
            }
        }
    }
    
    result = es.search(index="parliament_speeches", body=query)
    return [b['key'] for b in result['aggregations']['speakers']['buckets']]
```

### 3. Time-based Analysis - Speeches Per Speaker Per Year

```python
def get_speech_timeline(mp_name: str):
    query = {
        "size": 0,
        "query": {
            "term": {"speech_giver.keyword": mp_name}
        },
        "aggs": {
            "by_year": {
                "date_histogram": {
                    "field": "session_date",
                    "calendar_interval": "year"
                }
            }
        }
    }
    
    result = es.search(index="parliament_speeches", body=query)
    
    timeline = []
    for bucket in result['aggregations']['by_year']['buckets']:
        timeline.append({
            "year": bucket['key_as_string'][:4],
            "speeches": bucket['doc_count']
        })
    
    return timeline
```

---

## 🚀 Other Fields to Consider

You should also add keyword subfields to these fields:

### 1. Political Party
```python
"political_party": {
    "type": "text",
    "fields": {
        "keyword": {"type": "keyword"}
    }
}
```

### 2. Political Party at Time
```python
"political_party_at_time": {
    "type": "keyword"  # Already keyword-only is fine
}
```

### 3. Session ID
```python
"session_id": {
    "type": "text",
    "fields": {
        "keyword": {"type": "keyword"}
    }
}
```

---

## 📝 Script to Update Multiple Fields

```python
def update_all_text_fields_with_keyword():
    """Add keyword subfields to all relevant text fields."""
    
    mapping = {
        "properties": {
            "speech_giver": {
                "type": "text",
                "fields": {"keyword": {"type": "keyword", "ignore_above": 256}}
            },
            "political_party": {
                "type": "text",
                "fields": {"keyword": {"type": "keyword", "ignore_above": 256}}
            },
            "session_id": {
                "type": "text",
                "fields": {"keyword": {"type": "keyword", "ignore_above": 256}}
            },
            "file": {
                "type": "text",
                "fields": {"keyword": {"type": "keyword", "ignore_above": 256}}
            }
        }
    }
    
    es.indices.put_mapping(index="parliament_speeches", body=mapping)
    print("✅ Updated all fields with keyword subfields")
```

---

## ⚠️ Important Notes

### 1. **No Reindexing Needed**
When you add a `.keyword` subfield to an existing text field, Elasticsearch automatically indexes it for all existing documents. No need to reindex!

### 2. **ignore_above**
The `ignore_above: 256` parameter means strings longer than 256 characters won't be indexed as keywords. This is fine for names but adjust if needed.

### 3. **Use .keyword for Aggregations**
Always remember to use `.keyword` suffix:
- ✅ `speech_giver.keyword`
- ❌ `speech_giver`

### 4. **Search vs Filter**
- Use `speech_giver` (text) for full-text search: `"match": {"speech_giver": "özgür"}`
- Use `speech_giver.keyword` for exact match: `"term": {"speech_giver.keyword": "Özgür Özel"}`

---

## 🧪 Testing

### Test 1: Check Mapping
```bash
curl -X GET "http://localhost:9200/parliament_speeches/_mapping/field/speech_giver"
```

### Test 2: Test Aggregation
```bash
curl -X POST "http://localhost:9200/parliament_speeches/_search" \
  -H 'Content-Type: application/json' \
  -d '{
    "size": 0,
    "aggs": {
      "speakers": {
        "terms": {"field": "speech_giver.keyword", "size": 10}
      }
    }
  }'
```

### Test 3: Exact Match
```bash
curl -X POST "http://localhost:9200/parliament_speeches/_search" \
  -H 'Content-Type: application/json' \
  -d '{
    "query": {
      "term": {"speech_giver.keyword": "Özgür Özel"}
    }
  }'
```

---

## 🔧 Troubleshooting

### Issue: "Fielddata is disabled"
**Solution**: You're using `speech_giver` instead of `speech_giver.keyword`. Add `.keyword` suffix.

### Issue: "No such field speech_giver.keyword"
**Solution**: Run the update mapping script to add the keyword subfield.

### Issue: Aggregation returns nothing
**Solution**: Check if documents exist with that field populated. Use `_search` to verify.

### Issue: Case-sensitive matching issues
**Solution**: Keyword fields are case-sensitive. Make sure you're using exact names or use text field for case-insensitive search.

---

## 📚 Further Reading

- [Elasticsearch Multi-fields](https://www.elastic.co/guide/en/elasticsearch/reference/current/multi-fields.html)
- [Terms Aggregation](https://www.elastic.co/guide/en/elasticsearch/reference/current/search-aggregations-bucket-terms-aggregation.html)
- [Keyword Type](https://www.elastic.co/guide/en/elasticsearch/reference/current/keyword.html)

---

## ✅ Summary

1. **Run the script**: `python scripts/update_speech_giver_mapping.py`
2. **Use `.keyword` suffix**: For all aggregations and exact matches
3. **No reindexing needed**: Existing documents automatically get the keyword field
4. **Test it**: Try aggregations and see the performance boost!

Your `speech_giver` field will now be fully optimized for aggregations! 🎉
