# LLM Topic Name Generation Setup

This document explains how to set up and use the LLM-based topic naming feature that generates human-readable Turkish topic names from BERTopic's keyword-based labels.

## Overview

The system uses Groq's LLM API to transform keyword-based topic labels like `"0_ekonomi_bütçe_mali_vergi"` into readable Turkish names like `"Ekonomi ve Bütçe Politikaları"`.

## Prerequisites

1. **Groq API Account**
   - Create free account at: https://console.groq.com/
   - Free tier includes:
     - 14,400 requests/day
     - 7,200,000 tokens/day
     - Perfect for ~250 topics

2. **Python Dependencies**
   ```bash
   pip install groq>=0.4.0
   ```
   
   Or install all requirements:
   ```bash
   pip install -r requirements.txt
   ```

## Configuration

### 1. Get Groq API Key

1. Visit https://console.groq.com/keys
2. Create a new API key
3. Copy the key (starts with `gsk_...`)

### 2. Set Environment Variables

**Option A: Export in terminal (temporary)**
```bash
export GROQ_API_KEY="gsk_your_api_key_here"
export GROQ_MODEL="llama-3.1-70b-versatile"  # Optional, this is default
export USE_LLM_NAMING="true"  # Optional, default is true
```

**Option B: Add to `.env` file (recommended)**
```bash
# Create .env file in project root
cat > .env << EOF
GROQ_API_KEY=gsk_your_api_key_here
GROQ_MODEL=llama-3.1-70b-versatile
USE_LLM_NAMING=true
EOF
```

**Option C: Add to shell profile (permanent)**
```bash
# Add to ~/.bashrc or ~/.zshrc
echo 'export GROQ_API_KEY="gsk_your_api_key_here"' >> ~/.zshrc
source ~/.zshrc
```

### 3. Verify Configuration

```bash
# Check if API key is set
echo $GROQ_API_KEY

# Should output: gsk_...
```

## Usage

### Automatic Mode (Default)

When you run topic analysis, LLM naming happens automatically:

```bash
cd src
python analyze_speech_topics.py
```

The script will:
1. Run BERTopic analysis
2. Save topic details to CSV
3. **Automatically generate readable names with LLM**
4. Update Elasticsearch with readable names
5. Export summary with readable names

### Manual/Test Mode

Test the LLM naming independently:

```bash
cd src
python llm_topic_namer.py ../data/data_secret/topic_details.csv
```

This will:
- Load topic_details.csv
- Generate names for all topics
- Print results (but not update Elasticsearch)

### Disable LLM Naming

If you want to skip LLM naming:

```bash
export USE_LLM_NAMING="false"
python analyze_speech_topics.py
```

Or set in `.env`:
```
USE_LLM_NAMING=false
```

## Configuration Options

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `GROQ_API_KEY` | (required) | Your Groq API key |
| `GROQ_MODEL` | `llama-3.1-70b-versatile` | LLM model to use |
| `USE_LLM_NAMING` | `true` | Enable/disable LLM naming |

### Available Models

Groq offers several models:

| Model | Speed | Quality | Best For |
|-------|-------|---------|----------|
| `llama-3.1-70b-versatile` | Fast | High | **Recommended** - Best balance |
| `mixtral-8x7b-32768` | Very Fast | Good | Quick testing |
| `llama-3.1-8b-instant` | Ultra Fast | Decent | Budget/high volume |

## Output Examples

### Before (Keywords)
```
0_ekonomi_bütçe_mali_vergi
1_eğitim_okul_öğrenci_öğretmen
5_sağlık_hastane_doktor_tedavi
12_güvenlik_polis_asker_terör
```

### After (LLM-Generated)
```
Ekonomi ve Bütçe Politikaları
Eğitim Sistemi ve Öğretmenlik
Sağlık Hizmetleri ve Tedavi
Güvenlik ve Terörle Mücadele
```

## Troubleshooting

### Error: "Groq API key not found"

**Solution:**
```bash
# Check if key is set
echo $GROQ_API_KEY

# If empty, set it:
export GROQ_API_KEY="gsk_your_key_here"
```

### Error: "groq package not installed"

**Solution:**
```bash
pip install groq
```

### Error: "Rate limit exceeded"

**Solution:**
- Wait a few minutes (free tier resets)
- Or reduce number of topics being processed
- The script has built-in exponential backoff

### Generated names are in English

**Issue:** LLM not following Turkish language instruction

**Solution:**
- Try different model (llama-3.1-70b-versatile is best for Turkish)
- Check if topic keywords are in Turkish
- Verify representative docs contain Turkish text

### Names are too long or generic

**Solution:**
The prompt is optimized for 5-word max. If needed, edit the prompt in `src/llm_topic_namer.py`:
```python
# Line ~80
prompt = f"""... en fazla 5 kelime olmalı."""
# Change to: en fazla 3 kelime olmalı
```

## Cost Estimation

### Free Tier Limits
- **Requests**: 14,400/day
- **Tokens**: 7,200,000/day

### Typical Usage
For 250 topics:
- **Requests**: 250 (~1.7% of daily limit)
- **Tokens**: ~125,000 (~1.7% of daily limit)
- **Time**: 2-5 minutes
- **Cost**: FREE ✅

### Multiple Runs
You can re-run analysis **multiple times per day** without hitting limits.

## Data Flow

```
BERTopic Analysis
    ↓
topic_details.csv (with keywords & docs)
    ↓
Groq LLM (generates readable names)
    ↓
Elasticsearch (updated with readable names)
    ↓
topic_summary.csv (exported with readable names)
    ↓
Frontend API (serves readable names)
```

## Files Created/Modified

### Created
- `src/llm_topic_namer.py` - LLM service module
- `docs/LLM_TOPIC_NAMING_SETUP.md` - This file

### Modified
- `src/analyze_speech_topics.py` - Added LLM integration
- `requirements.txt` - Added groq dependency

### Generated
- `data/data_secret/topic_details.csv` - Topic info for LLM
- Elasticsearch documents updated with `topic_label` field

## Rollback

If you want to revert to keyword-based labels:

### Option 1: Disable and re-run
```bash
export USE_LLM_NAMING="false"
python src/analyze_speech_topics.py
```

### Option 2: Restore from backup
If you have a backup of topic_summary.csv with keyword labels, restore it.

## Advanced Usage

### Custom Prompt

Edit `src/llm_topic_namer.py`, line ~80:
```python
def _build_prompt(self, keywords: str, representative_docs: List[str]) -> str:
    # Modify the Turkish prompt here
    prompt = f"""Your custom prompt..."""
```

### Different Model

```bash
export GROQ_MODEL="mixtral-8x7b-32768"
```

### Process Subset of Topics

Edit `src/llm_topic_namer.py` to add filtering:
```python
# Only process topics 0-50
for idx, row in enumerate(topics[:50], 1):
```

## Support

For issues:
1. Check Groq API status: https://status.groq.com/
2. Review API documentation: https://console.groq.com/docs
3. Check script output for specific error messages

## Security Notes

- **Never commit** API keys to git
- Add `.env` to `.gitignore`
- Rotate keys periodically
- Use environment variables in production
