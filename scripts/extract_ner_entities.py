#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Extract NER entities from parliamentary speeches and store in Elasticsearch.

This script:
1. Loads the TerminatorPower/nerT Turkish NER model
2. Processes all speeches in Elasticsearch
3. Extracts entities (PERSON, LOCATION, ORGANIZATION)
4. Links entities to Wikipedia via Wikidata API
5. Updates Elasticsearch documents with ner_entities field
"""

import collections
import time
import warnings
from typing import List, Dict, Any, Optional
from transformers import pipeline
import requests
from elasticsearch import Elasticsearch
from elasticsearch.helpers import scan
from tqdm import tqdm
import sys
import os

# Suppress NumPy 2.0 deprecation warnings from transformers library
warnings.filterwarnings("ignore", category=DeprecationWarning, message=".*np.float_.*")
warnings.filterwarnings("ignore", category=DeprecationWarning, message=".*np.int_.*")
warnings.filterwarnings("ignore", category=DeprecationWarning, message=".*np.complex_.*")

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from api.config import ELASTICSEARCH_HOST, ELASTICSEARCH_INDEX

# Wikidata API headers
HEADERS = {
    # Aşağıda suzan hocanın kullandığı header var
    # "User-Agent": "Turkish-NEL-Research/1.0 (contact: suzan.uskudarli@bogazici.edu.tr)"
}


def wikidata_search(entity: str, lang: str = "tr", limit: int = 1, sleep: float = 0.5) -> List[Dict]:
    """Search for entity in Wikidata."""
    url = "https://www.wikidata.org/w/api.php"
    params = {
        "action": "wbsearchentities",
        "search": entity,
        "language": lang,
        "format": "json",
        "limit": limit
    }

    try:
        r = requests.get(url, params=params, headers=HEADERS, timeout=10)
        r.raise_for_status()
        data = r.json()
        time.sleep(sleep)  # Important: avoid rate limiting
        return data.get("search", [])
    except Exception as e:
        print(f"[Wikidata error] Entity: {entity} | {e}")
        return []


def wikidata_to_wikipedia(qid: str, lang: str = "tr") -> Optional[str]:
    """Convert Wikidata QID to Wikipedia URL."""
    url = "https://www.wikidata.org/w/api.php"
    params = {
        "action": "wbgetentities",
        "ids": qid,
        "props": "sitelinks",
        "format": "json"
    }

    try:
        r = requests.get(url, params=params, headers=HEADERS, timeout=10)
        r.raise_for_status()
        data = r.json()
        entity = data["entities"][qid]
        key = f"{lang}wiki"
        return entity["sitelinks"][key]["url"] if key in entity["sitelinks"] else None
    except Exception:
        return None


def aggregate_tokens(entities: List[Dict]) -> List[Dict]:
    """Aggregate subword tokens (handle ## prefixes from BERT tokenization)."""
    if not entities:
        return []
    
    merged = []
    i = 0
    
    while i < len(entities):
        token = entities[i]
        word = token["word"]
        entity_group = token["entity_group"]
        score = token["score"]
        start = token["start"]
        end = token["end"]
        
        # Keep merging consecutive ## tokens of the same entity type
        j = i + 1
        while j < len(entities):
            next_token = entities[j]
            # Check if next token is a subword (starts with ##) and same entity group
            if next_token["word"].startswith("##") and next_token["entity_group"] == entity_group:
                word += next_token["word"][2:]  # remove ##
                end = next_token["end"]
                # Average the scores
                score = (score + next_token["score"]) / 2
                j += 1
            else:
                break
        
        merged.append({
            "entity_group": entity_group,
            "word": word,
            "score": score,
            "start": start,
            "end": end
        })
        
        i = j if j > i + 1 else i + 1
    
    return merged


def extract_entities(text: str, ner_pipeline) -> List[Dict]:
    """Extract entities from text using NER pipeline."""
    if not text or not text.strip():
        return []
    
    try:
        # Suppress warnings for this specific call
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", category=DeprecationWarning)
            raw_entities = ner_pipeline(text)
        
        if not raw_entities:
            return []
        
        # Aggregate subword tokens
        entities = aggregate_tokens(raw_entities)
        
        # Count entity frequencies
        entity_counter = collections.Counter(
            e["word"] for e in entities
        )
        
        # Build entity list with metadata
        entity_list = []
        for entity_name, freq in entity_counter.items():
            # Find the first occurrence for metadata
            first_occurrence = next(
                (e for e in entities if e["word"] == entity_name),
                None
            )
            
            if first_occurrence:
                entity_list.append({
                    "entity": entity_name,
                    "entity_group": first_occurrence["entity_group"],
                    "frequency": freq,
                    "confidence": float(first_occurrence["score"])  # Ensure float type
                })
        
        return entity_list
    except Exception as e:
        # Only log actual errors, not deprecation warnings
        if "np.float_" not in str(e) and "np.int_" not in str(e):
            print(f"[NER error] {e}")
        return []


# Cache for Wikidata lookups to avoid redundant API calls
_wikidata_cache: Dict[str, Optional[str]] = {}


def link_entities_to_wikipedia(entities: List[Dict], cache: Dict[str, Optional[str]] = None) -> List[Dict]:
    """Link entities to Wikipedia via Wikidata API with caching."""
    if cache is None:
        cache = _wikidata_cache
    
    linked_entities = []
    
    for entity_data in entities:
        entity_name = entity_data["entity"]
        
        # Check cache first
        if entity_name in cache:
            wiki_url = cache[entity_name]
        else:
            # Search Wikidata
            candidates = wikidata_search(entity_name)
            
            if candidates:
                qid = candidates[0]["id"]
                wiki_url = wikidata_to_wikipedia(qid)
            else:
                wiki_url = None
            
            # Cache the result (even if None to avoid retrying)
            cache[entity_name] = wiki_url
        
        # Add Wikipedia URL if found
        entity_data["wikipedia_url"] = wiki_url
        
        linked_entities.append(entity_data)
    
    return linked_entities


def process_speech_document(doc: Dict[str, Any], ner_pipeline, link_wikipedia: bool = True, cache: Dict[str, Optional[str]] = None) -> Optional[Dict]:
    """Process a single speech document and extract entities."""
    source = doc.get("_source", {})
    content = source.get("content", "")
    
    if not content:
        return None
    
    # Extract entities
    entities = extract_entities(content, ner_pipeline)
    
    if not entities:
        return None
    
    # Link to Wikipedia if requested
    if link_wikipedia:
        entities = link_entities_to_wikipedia(entities, cache=cache)
    
    # Return update document
    return {
        "_id": doc["_id"],
        "_source": {
            "ner_entities": entities
        }
    }


def update_elasticsearch_mapping(es: Elasticsearch, index_name: str):
    """Update Elasticsearch mapping to include ner_entities field."""
    mapping = {
        "properties": {
            "ner_entities": {
                "type": "nested",
                "properties": {
                    "entity": {"type": "keyword"},
                    "entity_group": {"type": "keyword"},
                    "frequency": {"type": "integer"},
                    "wikipedia_url": {"type": "keyword"},
                    "confidence": {"type": "float"}
                }
            }
        }
    }
    
    try:
        es.indices.put_mapping(index=index_name, body=mapping)
        print(f"✅ Updated mapping for '{index_name}' with ner_entities field")
    except Exception as e:
        print(f"⚠️  Warning: Could not update mapping: {e}")
        print("   The field will be added dynamically, but explicit mapping is recommended.")


def main():
    """Main function to process all speeches."""
    print("=" * 80)
    print("NER Entity Extraction Script")
    print("=" * 80)
    
    # Connect to Elasticsearch
    print(f"\n📡 Connecting to Elasticsearch at {ELASTICSEARCH_HOST}...")
    es = Elasticsearch(hosts=[ELASTICSEARCH_HOST])
    
    try:
        if not es.ping():
            print("❌ Failed to connect to Elasticsearch")
            sys.exit(1)
        print("✅ Connected to Elasticsearch")
    except Exception as e:
        print(f"❌ Connection error: {e}")
        sys.exit(1)
    
    # Update mapping
    print(f"\n🔧 Updating Elasticsearch mapping...")
    update_elasticsearch_mapping(es, ELASTICSEARCH_INDEX)
    
    # Load NER model
    print(f"\n🤖 Loading NER model (TerminatorPower/nerT)...")
    print("   This may take a few minutes on first run...")
    try:
        ner_pipeline = pipeline(
            "token-classification",
            model="TerminatorPower/nerT",
            aggregation_strategy="simple"
        )
        print("✅ NER model loaded successfully")
    except Exception as e:
        print(f"❌ Failed to load NER model: {e}")
        sys.exit(1)
    
    # Get total document count
    print(f"\n📊 Counting documents in '{ELASTICSEARCH_INDEX}'...")
    try:
        count_response = es.count(index=ELASTICSEARCH_INDEX)
        total_docs = count_response["count"]
        print(f"   Found {total_docs:,} documents")
    except Exception as e:
        print(f"❌ Error counting documents: {e}")
        sys.exit(1)
    
    if total_docs == 0:
        print("⚠️  No documents found in index. Exiting.")
        sys.exit(0)
    
    # Ask user about Wikipedia linking
    print("\n" + "=" * 80)
    print("Configuration:")
    print("=" * 80)
    print("⚠️  WARNING: Wikipedia linking adds ~0.5s per unique entity")
    print("   Without caching, this can take 30+ hours for 8,930 documents")
    print("   With caching (recommended), it's much faster after initial lookups")
    print()
    link_wiki = input("Link entities to Wikipedia? (y/n, default: n): ").strip().lower()
    link_wiki = link_wiki == "y"
    
    if link_wiki:
        print("✅ Wikipedia linking enabled (with caching)")
        print("   First pass will be slower, but subsequent entities will be instant")
    else:
        print("✅ Wikipedia linking disabled - faster processing")
        print("   You can add Wikipedia links later by re-running with -w flag")
    
    batch_size = input("Batch size for updates (default: 100): ").strip()
    batch_size = int(batch_size) if batch_size.isdigit() else 100
    
    # Initialize cache
    wiki_cache: Dict[str, Optional[str]] = {}
    
    # Process documents
    print("\n" + "=" * 80)
    print("Processing speeches...")
    print("=" * 80)
    
    batch = []
    processed = 0
    updated = 0
    errors = 0
    
    # Use scan to iterate through all documents
    query = {
        "query": {"match_all": {}},
        "_source": ["content"]  # Only fetch content field to save memory
    }
    
    try:
        for doc in tqdm(scan(es, query=query, index=ELASTICSEARCH_INDEX), total=total_docs):
            processed += 1
            
            try:
                # Process document (suppress NumPy deprecation warnings)
                with warnings.catch_warnings():
                    warnings.filterwarnings("ignore", category=DeprecationWarning)
                    update_doc = process_speech_document(doc, ner_pipeline, link_wikipedia=link_wiki, cache=wiki_cache)
                
                if update_doc:
                    batch.append({
                        "_op_type": "update",
                        "_index": ELASTICSEARCH_INDEX,
                        "_id": update_doc["_id"],
                        "doc": update_doc["_source"]
                    })
                    updated += 1
                    
                    # Progress update for cache stats
                    if processed % 50 == 0 and link_wiki:
                        cache_hits = len([v for v in wiki_cache.values() if v is not None])
                        cache_total = len(wiki_cache)
                        tqdm.write(f"   Cache: {cache_total} entities ({cache_hits} with Wikipedia links)")
                
                # Bulk update when batch is full
                if len(batch) >= batch_size:
                    from elasticsearch.helpers import bulk
                    try:
                        success, failed = bulk(es, batch, stats_only=False, raise_on_error=False)
                        if failed:
                            tqdm.write(f"\n⚠️  Warning: {len(failed)} bulk update failures in batch")
                            for fail in failed[:3]:  # Show first 3 failures
                                tqdm.write(f"   {fail}")
                    except Exception as bulk_err:
                        tqdm.write(f"\n❌ Bulk update error: {bulk_err}")
                    batch = []
                    
            except Exception as e:
                error_msg = str(e)
                # Don't count NumPy deprecation warnings as real errors
                if "np.float_" not in error_msg and "np.int_" not in error_msg and "np.complex_" not in error_msg:
                    errors += 1
                    if errors <= 10:  # Print first 10 real errors
                        tqdm.write(f"\n⚠️  Error processing document {doc.get('_id', 'unknown')}: {e}")
            
            # Progress update every 100 documents
            if processed % 100 == 0:
                tqdm.write(f"Processed: {processed:,} | Updated: {updated:,} | Errors: {errors}")
        
        # Process remaining batch
        if batch:
            from elasticsearch.helpers import bulk
            try:
                success, failed = bulk(es, batch, stats_only=False, raise_on_error=False)
                if failed:
                    print(f"\n⚠️  Warning: {len(failed)} failures in final batch")
            except Exception as bulk_err:
                print(f"\n❌ Final batch error: {bulk_err}")
        
        # Force refresh to ensure all updates are visible
        print("\n♻️  Refreshing index to ensure updates are committed...")
        try:
            es.indices.refresh(index=ELASTICSEARCH_INDEX)
            print("✅ Index refreshed")
        except Exception as refresh_err:
            print(f"⚠️  Refresh warning: {refresh_err}")
        
        print("\n" + "=" * 80)
        print("✅ Processing complete!")
        print("=" * 80)
        print(f"   Total processed: {processed:,}")
        print(f"   Documents updated: {updated:,}")
        print(f"   Errors: {errors}")
        if link_wiki:
            cache_total = len(wiki_cache)
            cache_linked = len([v for v in wiki_cache.values() if v is not None])
            print(f"   Unique entities cached: {cache_total:,}")
            print(f"   Entities with Wikipedia links: {cache_linked:,}")
        print("=" * 80)
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
        if batch:
            print(f"   Processing remaining {len(batch)} documents in batch...")
            from elasticsearch.helpers import bulk
            bulk(es, batch)
        print(f"   Processed {processed:,} documents before interruption")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

