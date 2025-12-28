# Update Topic Labels Script Guide

## Overview

The `update_topic_labels.py` script allows you to update Elasticsearch topic labels with LLM-generated readable names **WITHOUT re-running BERTopic analysis**.

This is useful when:
- You want to regenerate topic names with different prompts
- You want to improve existing topic labels
- Your ES documents already have `topic_id` but need better labels
- You want to experiment with different LLM models

## Quick Start

```bash
# Navigate to scripts directory
cd scripts

# Run with default settings
python update_topic_labels.py

# Preview changes without updating (dry run)
python update_topic_labels.py --dry-run
```

## Prerequisites

1. **BERTopic analysis must have been run at least once**
   - This creates `topic_details.csv` which the script needs
   - Elasticsearch documents must have `topic_id` field

2. **Groq API key must be set**
   ```bash
   export GROQ_API_KEY="gsk_your_key_here"
   ```

3. **Elasticsearch must be running**
   ```bash
   # Verify ES is running
   curl http://localhost:9200
   ```

## Usage

### Basic Usage

```bash
# Update all topic labels
python update_topic_labels.py
```

The script will:
1. Check if `topic_details.csv` exists
2. Connect to Elasticsearch
3. Verify documents have topic assignments
4. Generate new readable names with LLM
5. Preview the changes
6. Ask for confirmation
7. Update all documents in Elasticsearch

### Dry Run (Preview Only)

```bash
# Preview what changes would be made without updating ES
python update_topic_labels.py --dry-run
```

This is useful to:
- See what names the LLM will generate
- Test different prompts or models
- Verify everything works before applying changes

### Custom Paths and Settings

```bash
# Use custom CSV file location
python update_topic_labels.py --csv /path/to/topic_details.csv

# Use different Elasticsearch index
python update_topic_labels.py --index my_custom_index

# Use different Elasticsearch host
python update_topic_labels.py --host http://remote-server:9200

# Combine multiple options
python update_topic_labels.py \
  --csv ../data/topic_details.csv \
  --index parliament_speeches \
  --host http://localhost:9200
```

### Using Different LLM Models

```bash
# Use faster model
export GROQ_MODEL="mixtral-8x7b-32768"
python update_topic_labels.py

# Use ultra-fast model
export GROQ_MODEL="llama-3.1-8b-instant"
python update_topic_labels.py
```

## Command Line Options

```
Options:
  --csv PATH          Path to topic_details.csv
                      (default: ../data/data_secret/topic_details.csv)
  
  --index NAME        Elasticsearch index name
                      (default: parliament_speeches)
  
  --host URL          Elasticsearch host URL
                      (default: http://localhost:9200)
  
  --dry-run           Preview changes without updating Elasticsearch
  
  --api-key KEY       Groq API key (or set GROQ_API_KEY env var)
  
  -h, --help          Show help message
```

## Example Output

```
================================================================================
ELASTICSEARCH TOPIC LABEL UPDATER
================================================================================

This script updates topic labels in Elasticsearch with LLM-generated
readable names WITHOUT re-running BERTopic analysis.

✅ Groq API key found
✅ Model: llama-3.1-70b-versatile
✅ Found topic_details.csv at ../data/data_secret/topic_details.csv

🔌 Connecting to Elasticsearch at http://localhost:9200...
✅ Connected to Elasticsearch

📊 Checking if parliament_speeches has topic assignments...
✅ Found 27,201 documents with topic assignments

   Sample document:
   • topic_id: 5
   • current topic_label: 5_ekonomi_bütçe_mali_vergi

================================================================================
🤖 GENERATING READABLE TOPIC NAMES
================================================================================

   Model: llama-3.1-70b-versatile
   Processing 251 topics...
   [1/251] Topic 0: Generating name...
   ✅ Topic 0: "Genel Meclis Prosedürleri"
   [2/251] Topic 1: Generating name...
   ✅ Topic 1: "Ekonomi ve Bütçe Politikaları"
   ...

✅ Successfully generated 251 topic names

📋 Preview of 251 topic name changes:
================================================================================
  1. Topic   0: Genel Meclis Prosedürleri
  2. Topic   1: Ekonomi ve Bütçe Politikaları
  3. Topic   2: Eğitim Sistemi ve Öğretmenlik
  4. Topic   3: Sağlık Hizmetleri ve Tedavi
  5. Topic   4: Tarım ve Çiftçilik
  6. Topic   5: Güvenlik ve Terörle Mücadele
  7. Topic   6: Enerji ve Doğal Kaynaklar
  8. Topic   7: Adalet Sistemi ve Hukuk
  9. Topic   8: İnsan Hakları ve Özgürlükler
 10. Topic   9: Dış Politika ve Uluslararası İlişkiler
     ... and 241 more topics
================================================================================

================================================================================
💾 UPDATING ELASTICSEARCH
================================================================================

⚠️  This will update topic_label for all documents in Elasticsearch.

Proceed with update? [y/N]: y

💾 Updating Elasticsearch with readable topic names...
   ✅ Topic 0: Updated 1,234 documents to "Genel Meclis Prosedürleri"
   ✅ Topic 1: Updated 2,456 documents to "Ekonomi ve Bütçe Politikaları"
   ...

✅ Total documents updated: 27,201

================================================================================
✅ UPDATE COMPLETE!
================================================================================
📊 Total documents updated: 27,201
📊 Topics processed: 251

✨ Your API will now serve readable topic names!
================================================================================
```

## Workflow

```
┌─────────────────────────────┐
│ topic_details.csv           │
│ (from previous analysis)    │
└──────────┬──────────────────┘
           │
           │ Read existing topics
           ▼
┌─────────────────────────────┐
│ Groq LLM                    │
│ Generate readable names     │
└──────────┬──────────────────┘
           │
           │ New topic mappings
           ▼
┌─────────────────────────────┐
│ Preview Changes             │
│ (show user what will change)│
└──────────┬──────────────────┘
           │
           │ User confirms
           ▼
┌─────────────────────────────┐
│ Elasticsearch               │
│ Bulk update topic_label     │
└─────────────────────────────┘
```

## Safety Features

### 1. Dry Run Mode
Always preview changes first:
```bash
python update_topic_labels.py --dry-run
```

### 2. User Confirmation
The script asks for confirmation before updating:
```
Proceed with update? [y/N]:
```

### 3. Validation Checks
- Verifies topic_details.csv exists
- Checks ES connection
- Confirms documents have topic_id
- Shows sample current labels

### 4. Detailed Progress
- Shows each topic being processed
- Reports success/failure per topic
- Final summary of changes

## Troubleshooting

### Error: "topic_details.csv not found"

**Cause**: BERTopic analysis hasn't been run yet

**Solution**:
```bash
cd src
python analyze_speech_topics.py
```

### Error: "No documents with topic_id found"

**Cause**: Elasticsearch doesn't have topic assignments

**Solution**: Run full topic analysis first:
```bash
cd src
python analyze_speech_topics.py
```

### Error: "GROQ_API_KEY not set"

**Solution**:
```bash
export GROQ_API_KEY="gsk_your_key_here"
```

### Error: "Cannot connect to Elasticsearch"

**Solution**:
```bash
# Check if ES is running
curl http://localhost:9200

# If not, start it
docker start elasticsearch
```

### Different names than expected

**Try different model**:
```bash
# More consistent
export GROQ_MODEL="llama-3.1-70b-versatile"

# Faster but less consistent
export GROQ_MODEL="mixtral-8x7b-32768"
```

## Use Cases

### 1. Improve Existing Names

You ran topic analysis but want better names:
```bash
# Preview new names
python update_topic_labels.py --dry-run

# If satisfied, apply
python update_topic_labels.py
```

### 2. Try Different Prompts

Edit `src/llm_topic_namer.py` to change prompt, then:
```bash
python update_topic_labels.py
```

### 3. Use Different Model

```bash
export GROQ_MODEL="mixtral-8x7b-32768"
python update_topic_labels.py --dry-run  # Preview
python update_topic_labels.py             # Apply
```

### 4. Update Specific Index

```bash
python update_topic_labels.py --index my_other_index
```

## Performance

- **Time**: 2-5 minutes for 250 topics
- **API calls**: 1 per topic (~250 requests)
- **ES updates**: Bulk operations (fast)
- **Memory**: < 100 MB
- **Cost**: FREE (Groq free tier)

## Best Practices

1. **Always dry-run first**
   ```bash
   python update_topic_labels.py --dry-run
   ```

2. **Backup before major changes**
   ```bash
   # Export current labels if needed
   curl -X GET "localhost:9200/parliament_speeches/_search" > backup.json
   ```

3. **Test with small dataset**
   - Try on dev/test index first
   - Verify quality before production

4. **Monitor rate limits**
   - Groq free tier: 14,400 requests/day
   - Space out multiple runs if needed

5. **Review generated names**
   - Check preview output carefully
   - Ensure Turkish quality is good
   - Verify names make sense

## Advanced Usage

### Custom Processing

Edit the script to add custom logic:

```python
# After line with process_all_topics()
# Filter or modify topic_mapping as needed

# Example: Only update specific topics
topic_mapping = {k: v for k, v in topic_mapping.items() if k < 100}
```

### Parallel Processing

For very large numbers of topics, consider batching:

```bash
# Process in batches to avoid timeouts
python update_topic_labels.py --dry-run  # First 250
# Edit CSV to process next batch
```

### Integration with CI/CD

```bash
#!/bin/bash
# Auto-update script

export GROQ_API_KEY="your-key"

# Update without confirmation (careful!)
echo "y" | python update_topic_labels.py
```

## Comparison with Full Analysis

| Feature | Full Analysis | Update Script |
|---------|--------------|---------------|
| Run BERTopic | ✅ Yes (30+ min) | ❌ No |
| Generate names | ✅ Yes | ✅ Yes |
| Update ES | ✅ Yes | ✅ Yes |
| Time | 30-60 minutes | 2-5 minutes |
| Use case | Initial analysis | Improve names |

## FAQ

**Q: Will this affect my existing topic_id assignments?**  
A: No, only `topic_label` is updated. `topic_id` stays the same.

**Q: Can I revert changes?**  
A: Re-run with different settings, or restore from backup.

**Q: How often should I update?**  
A: Only when you want to improve names or use different prompts.

**Q: Will this break my API?**  
A: No, the API reads `topic_label` which this updates seamlessly.

**Q: Can I update without confirmation?**  
A: Yes, but not recommended. Pipe "y" to script if needed:
```bash
echo "y" | python update_topic_labels.py
```

## See Also

- Main setup guide: `LLM_TOPIC_NAMING_SETUP.md`
- Implementation details: `LLM_TOPIC_NAMING_README.md`
- Test suite: `scripts/test_topic_namer.py`
