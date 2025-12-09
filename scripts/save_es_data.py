#!/usr/bin/env python3
"""
Fetch all data from Elasticsearch and save to local CSV file.
This allows you to close the Elasticsearch connection to free up memory.
"""

import pandas as pd
from elasticsearch import Elasticsearch
from tqdm import tqdm

INDEX_NAME = "parliament_speeches"
ES_URL = "http://localhost:9200"
# Change this to your desired path
OUTPUT_FILE = "your-desired-path/speeches_full.csv"


def fetch_all_speeches():
    """Fetch all speeches from Elasticsearch using scroll API."""
    print(f"📥 Connecting to Elasticsearch at {ES_URL}")
    es = Elasticsearch(ES_URL)
    
    if not es.ping():
        raise ConnectionError("Cannot connect to Elasticsearch server.")
    
    print(f"✅ Connected! Fetching documents from index: {INDEX_NAME}")
    
    results = []
    page_size = 1000
    
    # Use scroll API for large datasets
    resp = es.search(
        index=INDEX_NAME,
        query={"match_all": {}},
        scroll="5m",
        size=page_size,
        _source=True  # Fetch all fields
    )
    
    scroll_id = resp["_scroll_id"]
    hits = resp["hits"]["hits"]
    
    # Progress bar
    total_docs = resp["hits"]["total"]["value"]
    print(f"📊 Total documents to fetch: {total_docs}")
    
    pbar = tqdm(total=total_docs, desc="Fetching documents")
    
    while len(hits) > 0:
        for h in hits:
            results.append(h["_source"])
            pbar.update(1)
        
        # Get next batch
        resp = es.scroll(scroll_id=scroll_id, scroll="5m")
        scroll_id = resp["_scroll_id"]
        hits = resp["hits"]["hits"]
    
    pbar.close()
    
    print(f"\n✅ Retrieved {len(results)} documents.")
    
    # Close connection
    es.close()
    print("🔌 Elasticsearch connection closed.")
    
    # Convert to DataFrame
    print("📝 Converting to DataFrame...")
    df = pd.DataFrame(results)
    
    # Save to CSV
    print(f"💾 Saving to {OUTPUT_FILE}...")
    df.to_csv(OUTPUT_FILE, index=False)
    print(f"✅ Saved {len(df)} speeches to {OUTPUT_FILE}")
    print(f"📊 DataFrame shape: {df.shape}")
    print(f"📋 Columns: {list(df.columns)}")
    
    return df


if __name__ == "__main__":
    df = fetch_all_speeches()
    print("\n✅ Done! You can now close the Elasticsearch connection.")
