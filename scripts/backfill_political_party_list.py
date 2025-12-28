"""
Backfill Script: Update political_party field to list format

This script updates all existing documents in Elasticsearch by changing the
`political_party` field from a single string to a list of strings in the format:
["17.dönem Party Name", "18.dönem Party Name", ...]

Uses the mps_aggregated_by_term.csv data.
"""

import sys
import os
from elasticsearch import Elasticsearch, helpers
from typing import Dict, List
import time

# Add src directory to path for imports
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'src'))

try:
    from mp_aggregated_lookup import get_mp_party_list, get_terms_served
except ImportError:
    print("❌ Error: Could not import mp_aggregated_lookup module")
    print("   Make sure mp_aggregated_lookup.py exists in the src/ directory")
    sys.exit(1)

# Configuration
ELASTICSEARCH_HOST = os.getenv("ELASTICSEARCH_HOST", "http://localhost:9200")
ELASTICSEARCH_INDEX = os.getenv("ELASTICSEARCH_INDEX", "parliament_speeches")
BATCH_SIZE = 500  # Process in batches
SCROLL_SIZE = 1000  # How many docs to fetch per scroll


def connect_to_elasticsearch() -> Elasticsearch:
    """Connect to Elasticsearch."""
    print(f"🔌 Connecting to Elasticsearch at {ELASTICSEARCH_HOST}...")
    
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
        sys.exit(1)


def fetch_all_documents(es: Elasticsearch) -> List[Dict]:
    """
    Fetch all documents from Elasticsearch using scroll API.
    
    Returns:
        List of documents with _id, speech_giver, and current political_party
    """
    print(f"\n📥 Fetching all documents...")
    
    query = {
        "query": {
            "match_all": {}
        },
        "size": SCROLL_SIZE,
        "_source": ["speech_giver", "political_party", "terms_served"]
    }
    
    documents = []
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
            print(f"   Batch {batch_count}: Processing {len(hits)} documents...")
            
            for hit in hits:
                documents.append({
                    '_id': hit['_id'],
                    'speech_giver': hit['_source'].get('speech_giver'),
                    'current_party': hit['_source'].get('political_party'),
                    'current_terms': hit['_source'].get('terms_served')
                })
            
            response = es.scroll(scroll_id=scroll_id, scroll='5m')
            scroll_id = response['_scroll_id']
            hits = response['hits']['hits']
        
        print(f"✅ Fetched {len(documents):,} documents")
        return documents
        
    except Exception as e:
        print(f"❌ Error fetching documents: {e}")
        return []
        
    finally:
        if scroll_id:
            try:
                es.clear_scroll(scroll_id=scroll_id)
            except:
                pass


def update_documents_with_party_list(es: Elasticsearch, documents: List[Dict]) -> tuple:
    """
    Update documents with new political_party list format.
    
    Returns:
        Tuple of (updated_count, skipped_count, failed_count)
    """
    print(f"\n💾 Updating documents with new political_party list format...")
    
    updated_count = 0
    skipped_count = 0  # Already in list format
    failed_count = 0
    no_data_count = 0
    
    # Prepare bulk update actions
    actions = []
    
    for doc in documents:
        doc_id = doc['_id']
        speech_giver = doc.get('speech_giver')
        current_party = doc.get('current_party')
        
        # Skip if no speaker name
        if not speech_giver:
            skipped_count += 1
            continue
        
        # Check if already in list format
        if isinstance(current_party, list):
            skipped_count += 1
            continue
        
        # Look up new party list
        party_list = get_mp_party_list(speech_giver, fuzzy_match=True, threshold=0.85)
        terms_served = get_terms_served(speech_giver, fuzzy_match=True, threshold=0.85)
        
        if party_list:
            actions.append({
                '_op_type': 'update',
                '_index': ELASTICSEARCH_INDEX,
                '_id': doc_id,
                'doc': {
                    'political_party': party_list,
                    'terms_served': terms_served
                }
            })
        else:
            # No data found, convert existing string to list format if present
            if current_party and isinstance(current_party, str):
                actions.append({
                    '_op_type': 'update',
                    '_index': ELASTICSEARCH_INDEX,
                    '_id': doc_id,
                    'doc': {
                        'political_party': [current_party]  # Convert string to list
                    }
                })
            else:
                no_data_count += 1
    
    # Bulk update in batches
    if actions:
        print(f"\n   Updating {len(actions):,} documents in batches of {BATCH_SIZE}...")
        
        for i in range(0, len(actions), BATCH_SIZE):
            batch = actions[i:i + BATCH_SIZE]
            batch_num = (i // BATCH_SIZE) + 1
            total_batches = (len(actions) + BATCH_SIZE - 1) // BATCH_SIZE
            
            try:
                success, errors = helpers.bulk(
                    es,
                    batch,
                    raise_on_error=False,
                    chunk_size=BATCH_SIZE
                )
                
                updated_count += success
                failed_count += len(errors) if errors else 0
                
                print(f"   ✅ Batch {batch_num}/{total_batches}: Updated {success} documents")
                
                if errors:
                    print(f"   ⚠️  Batch {batch_num}/{total_batches}: {len(errors)} errors")
                
                # Small delay to avoid overwhelming ES
                time.sleep(0.1)
                
            except Exception as e:
                print(f"   ❌ Error in batch {batch_num}: {e}")
                failed_count += len(batch)
    
    print(f"\n📊 Update Summary:")
    print(f"   ✅ Updated: {updated_count:,}")
    print(f"   ⏭️  Skipped (already list format): {skipped_count:,}")
    print(f"   ⚠️  No party data found: {no_data_count:,}")
    print(f"   ❌ Failed: {failed_count:,}")
    
    return updated_count, skipped_count, failed_count


def main():
    """Main execution function."""
    print("=" * 80)
    print("BACKFILL POLITICAL_PARTY TO LIST FORMAT")
    print("=" * 80)
    print(f"Index: {ELASTICSEARCH_INDEX}")
    print(f"Host: {ELASTICSEARCH_HOST}")
    print(f"New Format: [\"17.dönem Party Name\", \"18.dönem Party Name\", ...]")
    print("=" * 80)
    
    start_time = time.time()
    
    # Connect to ES
    es = connect_to_elasticsearch()
    
    # Fetch all documents
    documents = fetch_all_documents(es)
    
    if not documents:
        print("❌ No documents found. Exiting.")
        return
    
    # Update documents
    updated, skipped, failed = update_documents_with_party_list(es, documents)
    
    duration = time.time() - start_time
    
    print("\n" + "=" * 80)
    print("✅ BACKFILL COMPLETE!")
    print("=" * 80)
    print(f"⏱️  Total time: {duration:.1f}s ({duration/60:.1f} minutes)")
    print(f"📊 Total documents processed: {len(documents):,}")
    print(f"✅ Successfully updated: {updated:,}")
    print(f"⏭️  Skipped: {skipped:,}")
    print(f"❌ Failed: {failed:,}")
    print("\n💡 political_party field is now a list format!")
    print("   Example: [\"17.dönem Anavatan Partisi\", \"18.dönem Anavatan Partisi\"]")
    print("=" * 80)


if __name__ == "__main__":
    main()
