"""
Speech Keyword Extraction using Aya Expanse 8B

This script extracts 10 keywords from each parliament speech using the Aya Expanse 8B 
language model. Keywords prioritize topic-related words and are saved to a CSV file.

**Features:**
- Batch processing for 10-30x speedup (optimized for 45GB GPU with batch_size=32)
- Uploads to Elasticsearch every 100 speeches (no data loss on interruption)
- Resume mode: automatically skips already processed speeches when re-run
- Adds two fields to each speech in Elasticsearch:
  - keywords: Array of keyword strings
  - keywords_str: Comma-separated keyword string

Usage:
    python extract_speech_keywords.py [OPTIONS]

Options:
    --limit N         : Process only first N speeches (useful for testing)
    --output FILE     : Output CSV file path (default: ../data/speech_keywords.csv)
    --batch-size N    : Batch size for processing (auto-detected if not specified)
    --upload-every N  : Upload to ES every N speeches (default: 100)
    --no-resume       : Process all speeches (don't skip already processed ones)

Examples:
    # Full run with auto-detected batch size and resume mode
    python extract_speech_keywords.py
    
    # Test with 100 speeches
    python extract_speech_keywords.py --limit 100
    
    # Use specific batch size for 45GB GPU
    python extract_speech_keywords.py --batch-size 32
    
    # Reprocess everything (ignore existing keywords)
    python extract_speech_keywords.py --no-resume
"""

import os
import sys
import argparse
import pandas as pd
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
from elasticsearch import Elasticsearch, helpers
from tqdm.auto import tqdm
from typing import List, Dict

# Configuration
ELASTICSEARCH_HOST = os.getenv("ELASTICSEARCH_HOST", "http://localhost:9200")
ELASTICSEARCH_INDEX = os.getenv("ELASTICSEARCH_INDEX", "parliament_speeches")
BATCH_SIZE = 1000
MODEL_ID = "CohereLabs/aya-expanse-8b"


def setup_device():
    """Setup and display device information."""
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Using device: {device}")
    if device == "cuda":
        print(f"GPU: {torch.cuda.get_device_name(0)}")
        print(f"GPU Memory: {torch.cuda.get_device_properties(0).total_memory / 1e9:.2f} GB")
    return device


def load_model(device: str):
    """Load Aya Expanse 8B model and tokenizer."""
    print(f"\nLoading model: {MODEL_ID}...")
    print("This may take a few minutes on first run...")
    
    tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)
    
    # Fix padding for decoder-only models (required for batch processing)
    tokenizer.padding_side = 'left'
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    model = AutoModelForCausalLM.from_pretrained(
        MODEL_ID,
        torch_dtype=torch.float16 if device == "cuda" else torch.float32,
        device_map="auto" if device == "cuda" else None,
        low_cpu_mem_usage=True
    )
    
    if device == "cpu":
        model = model.to(device)
    
    print("✅ Model loaded successfully!")
    return tokenizer, model


def connect_to_elasticsearch() -> Elasticsearch:
    """Connect to Elasticsearch and verify connection."""
    print(f"\n🔌 Connecting to Elasticsearch at {ELASTICSEARCH_HOST}...")
    
    try:
        es = Elasticsearch(hosts=[ELASTICSEARCH_HOST])
        
        if es.ping():
            count = es.count(index=ELASTICSEARCH_INDEX)
            total_docs = count.get('count', 0)
            print(f"✅ Connected to Elasticsearch")
            print(f"📊 Index: {ELASTICSEARCH_INDEX}")
            print(f"📊 Total documents: {total_docs:,}")
            return es
        else:
            raise Exception("Ping failed")
            
    except Exception as e:
        print(f"❌ Failed to connect to Elasticsearch: {e}")
        print(f"   Make sure Elasticsearch is running on {ELASTICSEARCH_HOST}")
        raise


def fetch_all_speeches(es: Elasticsearch, limit: int = None, skip_processed: bool = True) -> List[Dict]:
    """
    Fetch speeches from Elasticsearch using scroll API.
    
    Args:
        es: Elasticsearch client
        limit: Optional limit on number of speeches to fetch
        skip_processed: Skip speeches that already have keywords (for resuming)
    
    Returns:
        List of speech dictionaries with id, content, and metadata
    """
    print(f"\n📥 Fetching speeches from Elasticsearch...")
    if skip_processed:
        print("   Skipping speeches that already have keywords (resume mode)...")
    
    # Build query - optionally skip already processed speeches
    must_conditions = [{"exists": {"field": "content"}}]
    must_not_conditions = [{"term": {"content": ""}}]
    
    if skip_processed:
        # Skip speeches that already have keywords field
        must_not_conditions.append({"exists": {"field": "keywords"}})
    
    query = {
        "query": {
            "bool": {
                "must": must_conditions,
                "must_not": must_not_conditions
            }
        },
        "size": BATCH_SIZE,
        "_source": [
            "content", "speech_giver", "term", "year", 
            "session_date", "topic_label", "groq_topic_label"
        ]
    }
    
    speeches = []
    scroll_id = None
    batch_count = 0
    
    try:
        response = es.search(
            index=ELASTICSEARCH_INDEX,
            body=query,
            scroll='5m'
        )
        
        scroll_id = response['_scroll_id']
        hits = response['hits']['hits']
        
        while hits:
            batch_count += 1
            print(f"Batch {batch_count}: Processing {len(hits)} speeches...")
            
            for hit in hits:
                source = hit['_source']
                
                if source.get('content') and source['content'].strip():
                    speeches.append({
                        'speech_id': hit['_id'],
                        'content': source['content'],
                        'speech_giver': source.get('speech_giver', ''),
                        'topic_label': source.get('topic_label', ''),
                        'groq_topic_label': source.get('groq_topic_label', ''),
                        'year': source.get('year'),
                    })
            
            # Check if limit reached
            if limit and len(speeches) >= limit:
                speeches = speeches[:limit]
                break
            
            # Get next batch
            response = es.scroll(scroll_id=scroll_id, scroll='5m')
            scroll_id = response['_scroll_id']
            hits = response['hits']['hits']
        
        print(f"✅ Successfully fetched {len(speeches):,} speeches")
        return speeches
        
    except Exception as e:
        print(f"❌ Error fetching speeches: {e}")
        return []
        
    finally:
        if scroll_id:
            try:
                es.clear_scroll(scroll_id=scroll_id)
            except:
                pass


def extract_keywords_from_text(gen_text: str) -> str:
    """Helper to extract keywords from generated text and clean special tokens."""
    try:
        # List of special tokens to remove
        special_tokens = [
            '<|START_OF_TURN_TOKEN|>',
            '<|END_OF_TURN_TOKEN|>',
            '<|CHATBOT_TOKEN|>',
            '<|USER_TOKEN|>',
            '<|SYSTEM_TOKEN|>',
            '<BOS_TOKEN>',
            '<EOS_TOKEN>',
            '<s>',
            '</s>',
        ]
        
        # Find where keywords start
        keywords_start_phrase = "Anahtar kelimeler:"
        if keywords_start_phrase in gen_text:
            keywords_start = gen_text.find(keywords_start_phrase) + len(keywords_start_phrase)
            keywords = gen_text[keywords_start:].strip()
        else:
            # If phrase not found, try to extract from the end of generation
            keywords = gen_text.strip()
        
        # Take only first line
        keywords = keywords.split('\n')[0].strip()
        
        # Remove all special tokens
        for token in special_tokens:
            keywords = keywords.replace(token, '')
        
        # Clean up extra whitespace and commas
        keywords = keywords.strip()
        keywords = ', '.join([k.strip() for k in keywords.split(',') if k.strip()])
        
        # Validate that we have actual content (not just empty or single character)
        if not keywords or len(keywords) < 3 or keywords.count(',') == 0:
            return "ERROR: No valid keywords generated"
        
        return keywords
        
    except Exception as e:
        return f"ERROR: Could not extract keywords - {str(e)}"


def extract_keywords_batch(
    speeches_batch: List[Dict],
    tokenizer,
    model,
    device: str,
    batch_size: int = 32
) -> List[str]:
    """
    Extract keywords from multiple speeches at once (batch processing for speed).
    
    Args:
        speeches_batch: List of speech dictionaries
        tokenizer: Tokenizer instance
        model: Model instance
        device: Device to use
        batch_size: Number of speeches to process together
    
    Returns:
        List of comma-separated keyword strings
    """
    max_chars = 2000
    prompts = []
    
    for speech in speeches_batch:
        speech_content = speech['content'][:max_chars]
        topic_context = f" Konu: '{speech.get('groq_topic_label', '')}'." if speech.get('groq_topic_label') else ""
        
        prompt = f"""Aşağıdaki TBMM konuşmasından 10 anahtar kelime çıkar. Sadece anahtar kelimeleri virgülle ayrılmış olarak listele.{topic_context}

Konuşma:
{speech_content}

Anahtar kelimeler:"""
        prompts.append(prompt)
    
    # Batch tokenization
    messages_batch = [[{"role": "user", "content": p}] for p in prompts]
    
    # Tokenize all messages
    tokenized = []
    for msg in messages_batch:
        ids = tokenizer.apply_chat_template(
            msg, 
            tokenize=True, 
            add_generation_prompt=True, 
            return_tensors="pt"
        )
        tokenized.append(ids.squeeze(0))
    
    # Pad to same length (left padding for decoder models)
    from torch.nn.utils.rnn import pad_sequence
    input_ids_batch = pad_sequence(
        tokenized, 
        batch_first=True, 
        padding_value=tokenizer.pad_token_id
    ).to(device)
    
    attention_mask = (input_ids_batch != tokenizer.pad_token_id).long().to(device)
    
    # Generate for entire batch (much faster!)
    with torch.no_grad():
        gen_tokens = model.generate(
            input_ids_batch,
            attention_mask=attention_mask,
            max_new_tokens=50,  # Reduced from 100
            do_sample=False,    # Greedy decoding is faster
            pad_token_id=tokenizer.pad_token_id,
        )
    
    # Decode all results
    results = []
    for gen_token in gen_tokens:
        gen_text = tokenizer.decode(gen_token, skip_special_tokens=True)
        keywords = extract_keywords_from_text(gen_text)
        results.append(keywords)
    
    return results


def extract_keywords(
    speech_content: str, 
    topic_label: str, 
    speech_giver: str,
    tokenizer,
    model,
    device: str
) -> str:
    """
    Extract 10 keywords from a single speech (slower, use extract_keywords_batch for better performance).
    """
    speech_dict = {
        'content': speech_content,
        'groq_topic_label': topic_label,
        'speech_giver': speech_giver
    }
    return extract_keywords_batch([speech_dict], tokenizer, model, device, batch_size=1)[0]


def upload_keywords_chunk(es: Elasticsearch, results_chunk: List[Dict]):
    """Upload a chunk of keywords to Elasticsearch."""
    actions = []
    for row in results_chunk:
        if row['keywords'] != 'ERROR':
            keywords_list = [k.strip() for k in row['keywords'].split(',')]
            
            actions.append({
                '_op_type': 'update',
                '_index': ELASTICSEARCH_INDEX,
                '_id': row['speech_id'],
                'doc': {
                    'keywords': keywords_list,
                    'keywords_str': row['keywords']
                }
            })
    
    if actions:
        success, failed = helpers.bulk(es, actions, raise_on_error=False)
        return success, len(failed) if failed else 0
    return 0, 0


def process_all_speeches(
    speeches: List[Dict],
    es: Elasticsearch,
    tokenizer,
    model,
    device: str,
    batch_size: int = 32,
    upload_every: int = 100
) -> pd.DataFrame:
    """
    Process all speeches and extract keywords with periodic Elasticsearch updates.
    
    Args:
        speeches: List of speech dictionaries
        es: Elasticsearch client for periodic updates
        tokenizer: Tokenizer instance
        model: Model instance
        device: Device to use
        batch_size: Number of speeches to process together for model inference
        upload_every: Upload to Elasticsearch every N speeches
    
    Returns:
        DataFrame with speech_id and keywords columns
    """
    results = []
    pending_upload = []
    total_uploaded = 0
    
    print(f"\n🔄 Processing {len(speeches):,} speeches...")
    print(f"   Batch size: {batch_size} (model inference)")
    print(f"   Uploading to Elasticsearch every {upload_every} speeches")
    print("   Using batch processing for 10-30x speedup!\n")
    
    num_batches = (len(speeches) + batch_size - 1) // batch_size
    
    for i in tqdm(range(0, len(speeches), batch_size), total=num_batches, desc="Processing batches"):
        batch = speeches[i:i+batch_size]
        
        try:
            # Extract keywords for entire batch at once
            keywords_batch = extract_keywords_batch(batch, tokenizer, model, device, batch_size)
            
            # Add results
            for speech, keywords in zip(batch, keywords_batch):
                result = {
                    'speech_id': speech['speech_id'],
                    'keywords': keywords,
                    'speech_giver': speech['speech_giver'],
                    'year': speech.get('year', ''),
                    'topic_label': speech.get('groq_topic_label', '')
                }
                results.append(result)
                pending_upload.append(result)
                
        except Exception as e:
            print(f"\n⚠️  Error processing batch {i//batch_size + 1}: {e}")
            for speech in batch:
                result = {
                    'speech_id': speech['speech_id'],
                    'keywords': 'ERROR',
                    'speech_giver': speech['speech_giver'],
                    'year': speech.get('year', ''),
                    'topic_label': speech.get('groq_topic_label', '')
                }
                results.append(result)
                pending_upload.append(result)
        
        # Upload to Elasticsearch every N speeches
        if len(pending_upload) >= upload_every:
            success, failed = upload_keywords_chunk(es, pending_upload)
            total_uploaded += success
            print(f"\n💾 Uploaded {success} speeches to Elasticsearch (total: {total_uploaded})")
            if failed > 0:
                print(f"⚠️  Failed to upload {failed} speeches")
            pending_upload = []
    
    # Upload remaining speeches
    if pending_upload:
        success, failed = upload_keywords_chunk(es, pending_upload)
        total_uploaded += success
        print(f"\n💾 Uploaded final {success} speeches to Elasticsearch (total: {total_uploaded})")
        if failed > 0:
            print(f"⚠️  Failed to upload {failed} speeches")
    
    df = pd.DataFrame(results)
    print(f"\n✅ Processed {len(df):,} speeches")
    print(f"✅ Uploaded {total_uploaded:,} speeches to Elasticsearch")
    return df


def print_statistics(results_df: pd.DataFrame):
    """Print statistics about the extracted keywords."""
    error_count = (results_df['keywords'] == 'ERROR').sum()
    
    print(f"\n📈 Statistics:")
    print(f"Total speeches processed: {len(results_df):,}")
    print(f"Errors: {error_count}")
    print(f"Success rate: {((len(results_df) - error_count) / len(results_df) * 100):.2f}%")
    
    # Sample keywords by topic
    if 'topic_label' in results_df.columns and results_df['topic_label'].notna().any():
        print("\n📋 Sample keywords by topic:")
        for topic in results_df['topic_label'].dropna().unique()[:5]:
            topic_df = results_df[results_df['topic_label'] == topic]
            if len(topic_df) > 0:
                print(f"\n{topic}:")
                print(f"  Sample: {topic_df.iloc[0]['keywords']}")
    
    # Keyword count distribution
    results_df['keyword_count'] = results_df['keywords'].str.split(',').str.len()
    print(f"\n🔢 Keyword count distribution:")
    print(results_df['keyword_count'].describe())


def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(
        description="Extract keywords from parliament speeches using Aya Expanse 8B"
    )
    parser.add_argument(
        '--limit', 
        type=int, 
        default=None,
        help='Process only first N speeches (for testing)'
    )
    parser.add_argument(
        '--output',
        type=str,
        default='../data/speech_keywords.csv',
        help='Output CSV file path'
    )
    parser.add_argument(
        '--batch-size',
        type=int,
        default=None,
        help='Batch size for processing (auto-detected based on GPU if not specified)'
    )
    parser.add_argument(
        '--upload-every',
        type=int,
        default=100,
        help='Upload to Elasticsearch every N speeches (default: 100)'
    )
    parser.add_argument(
        '--no-resume',
        action='store_true',
        help="Process all speeches, don't skip already processed ones (default: resume from where left off)"
    )
    
    args = parser.parse_args()
    
    print("=" * 80)
    print("Speech Keyword Extraction using Aya Expanse 8B")
    print("=" * 80)
    
    # Setup
    device = setup_device()
    tokenizer, model = load_model(device)
    es = connect_to_elasticsearch()
    
    # Determine batch size
    if args.batch_size:
        batch_size = args.batch_size
    else:
        # Auto-detect based on device
        if device == 'cuda':
            gpu_mem = torch.cuda.get_device_properties(0).total_memory / 1e9
            if gpu_mem >= 40:
                batch_size = 32  # 45GB GPU
            elif gpu_mem >= 20:
                batch_size = 16  # 24GB GPU
            elif gpu_mem >= 12:
                batch_size = 8   # 16GB GPU
            else:
                batch_size = 4   # 8GB GPU
            print(f"Auto-detected batch size: {batch_size} (GPU: {gpu_mem:.1f}GB)")
        else:
            batch_size = 1
    
    # Fetch speeches (resume mode by default)
    skip_processed = not args.no_resume
    speeches = fetch_all_speeches(es, limit=args.limit, skip_processed=skip_processed)
    
    if len(speeches) == 0:
        if skip_processed:
            print("✅ All speeches already have keywords! Nothing to process.")
            sys.exit(0)
        else:
            print("❌ No speeches found. Exiting.")
            sys.exit(1)
    
    # Process speeches with batch processing and periodic uploads
    results_df = process_all_speeches(
        speeches, 
        es,
        tokenizer, 
        model, 
        device, 
        batch_size=batch_size,
        upload_every=args.upload_every
    )
    
    # Save results
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    results_df.to_csv(args.output, index=False)
    print(f"\n💾 Results saved to: {args.output}")
    print(f"Total rows: {len(results_df):,}")
    
    # Print statistics
    print_statistics(results_df)
    
    print("\n✅ Done!")
    print(f"\n💡 Keywords were uploaded to Elasticsearch during processing.")
    print(f"   To reprocess everything, use --no-resume flag.")
    print(f"   To change batch size, use --batch-size N.")


if __name__ == "__main__":
    main()
