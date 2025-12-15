# Topic Exclusion and Column Name Fixes

## Summary

Fixed issues with topic analysis where topic_id -1 (outliers) needed to be excluded and column names were updated in `topic_summary.csv`.

## Changes Made

### 1. Updated `api/services/csv_service.py`

**`get_topics_for_mp()` method:**
- ✅ Now excludes `topic_id == -1` (outliers)
- ✅ Uses correct column names: `topic_id`, `topic_label`, `speech_count`
- ✅ Returns `topic_id` in results for reference
- ✅ Handles both old and new column name formats

**New methods added:**
- `get_topic_details(topic_id, top_n_mps)` - Get detailed info about a specific topic
- `get_all_topics_summary(exclude_outliers)` - Get summary of all topics with stats

### 2. Updated `api/services/annual_review_service.py`

Fixed all methods to use new column names from `topic_summary.csv`:

| Old Column Name | New Column Name |
|----------------|-----------------|
| `topic` | `topic_id` |
| `Name` | `topic_label` |
| `Count` | `speech_count` |
| `count` | `speech_count` |

**Methods fixed:**
- ✅ `get_most_talked_topic()` - Uses `topic_id`, `topic_label`, `speech_count`
- ✅ `get_niche_topic()` - Uses `topic_id`, `topic_label`, `speech_count`
- ✅ `get_most_diverse_debate()` - Uses `topic_id`, `topic_label`, `speech_count`

All methods now **exclude topic_id -1 (outliers)** automatically.

### 3. Updated `src/analyze_speech_topics.py`

**`export_topic_summary()` function:**
- ✅ Added `exclude_outliers` parameter (default: True)
- ✅ Excludes topic_id -1 from exported CSV
- ✅ Prints statistics about excluded outliers
- ✅ Shows unique topics and MPs count

## New CSV Structure

The `topic_summary.csv` now has:

```csv
speech_giver,topic_id,topic_label,speech_count,term,year
Ahmet Yılmaz,5,5_ekonomi_bütçe_mali,45,"[26, 27]","[3, 4]"
```

**Columns:**
- `speech_giver`: MP name
- `topic_id`: Topic ID (0, 1, 2, ... but NOT -1 if outliers excluded)
- `topic_label`: Topic keywords (e.g., "5_ekonomi_bütçe_mali")
- `speech_count`: Number of speeches
- `term`: Parliamentary terms (list)
- `year`: Years (list)

## Impact

### ✅ MP Detail Page
- Shows only valid topics (no outliers)
- Correct percentages and counts

### ✅ Annual Review Page
- Most talked topic works correctly
- Niche topic calculates properly
- Most diverse debate shows accurate data
- All exclusions of outliers working

### ✅ API Responses
- `/api/mp/{id}` returns topics without outliers
- Topic statistics are accurate
- No confusion with -1 topic entries

## Testing

To verify everything works:

```python
# Test MP topics
from api.services.csv_service import csv_service
topics = csv_service.get_topics_for_mp("Özgür Özel", top_n=5)
# Should have no topic_id == -1

# Test annual review
from api.services.annual_review_service import annual_review_service
review = annual_review_service.get_annual_review(term=27, year=4)
# Should return valid data with no errors
```

## Re-running Topic Analysis

If you need to regenerate `topic_summary.csv`:

```bash
cd src
python analyze_speech_topics.py
```

The script will:
1. Fetch speeches from Elasticsearch
2. Run BERTopic analysis
3. **Automatically exclude outliers (topic_id -1)** from topic_summary.csv
4. Update Elasticsearch with topic assignments (including outliers in ES, just not in summary CSV)

## Key Points

✅ **Outliers in Elasticsearch**: Topic -1 IS saved to ES (for completeness)
✅ **Outliers in CSV**: Topic -1 is EXCLUDED from topic_summary.csv (for analysis)
✅ **API responses**: Automatically filter out topic -1
✅ **Column names**: All updated to match new structure

## Backward Compatibility

The `csv_service` methods handle both old and new column names:
```python
count_column = 'speech_count' if 'speech_count' in df.columns else 'count'
label_column = 'topic_label' if 'topic_label' in df.columns else 'Name'
```

This ensures the code works even if someone has an old CSV file.
