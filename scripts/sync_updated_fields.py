#!/usr/bin/env python3
"""
Sync specific fields from local Elasticsearch to remote GCP Elasticsearch.
Updates: ner_entities, hdbscan_topic_id, hdbscan_topic_label

Usage:
    python scripts/sync_updated_fields.py --remote-host http://GCP_VM_IP:9200
"""
import os
import sys
import argparse
from elasticsearch import Elasticsearch
from elasticsearch.helpers import scan, bulk
from tqdm import tqdm
from typing import Dict, List, Optional

# Configuration
LOCAL_ES_HOST = os.getenv("LOCAL_ES_HOST", "http://localhost:9200")
REMOTE_ES_HOST = os.getenv("REMOTE_ES_HOST", None)  # Must be provided
INDEX_NAME = os.getenv("ELASTICSEARCH_INDEX", "parliament_speeches")
BATCH_SIZE = 500


def connect_elasticsearch(host: str, label: str, index_name: str = INDEX_NAME) -> Elasticsearch:
    """Connect to Elasticsearch and verify connection."""
    print(f"\n📡 Connecting to {label} Elasticsearch at {host}...")
    try:
        es = Elasticsearch(hosts=[host])
        if not es.ping():
            raise Exception("Ping failed")
        count = es.count(index=index_name)['count']
        print(f"✅ Connected to {label} Elasticsearch")
        print(f"   Documents: {count:,}")
        return es
    except Exception as e:
        print(f"❌ Failed to connect to {label} Elasticsearch: {e}")
        sys.exit(1)


def sync_updated_fields(
    local_es: Elasticsearch,
    remote_es: Elasticsearch,
    index_name: str,
    sync_ner: bool = True,
    sync_topics: bool = True,
    batch_size: int = 500
):
    """
    Sync updated fields from local to remote Elasticsearch.
    
    Args:
        local_es: Local Elasticsearch client
        remote_es: Remote Elasticsearch client
        sync_ner: Whether to sync NER entities
        sync_topics: Whether to sync HDBSCAN topics
        batch_size: Batch size for bulk updates
    """
    print("\n" + "=" * 80)
    print("Field Sync: Local → Remote")
    print("=" * 80)
    print(f"   NER Entities: {'✅' if sync_ner else '❌'}")
    print(f"   HDBSCAN Topics: {'✅' if sync_topics else '❌'}")
    print("=" * 80)
    
    # Build query to find documents with updated fields
    must_clauses = []
    
    if sync_ner:
        must_clauses.append({
            "nested": {
                "path": "ner_entities",
                "query": {"exists": {"field": "ner_entities.entity"}}
            }
        })
    
    if sync_topics:
        must_clauses.append({
            "bool": {
                "should": [
                    {"exists": {"field": "hdbscan_topic_id"}},
                    {"exists": {"field": "hdbscan_topic_label"}}
                ],
                "minimum_should_match": 1
            }
        })
    
    if not must_clauses:
        print("❌ No fields selected for sync")
        return
    
    query = {
        "query": {
            "bool": {
                "must": must_clauses
            }
        },
        "_source": ["ner_entities", "hdbscan_topic_id", "hdbscan_topic_label"]
    }
    
    # Count documents to sync
    print("\n🔍 Counting documents to sync...")
    # Extract query for count API
    count_query = query.get("query", {"match_all": {}})
    count_response = local_es.count(index=index_name, body={"query": count_query})
    total_docs = count_response['count']
    print(f"   Found {total_docs:,} documents with updated fields")
    
    if total_docs == 0:
        print("⚠️  No documents found with the specified fields")
        return
    
    # Process in batches
    print(f"\n🚀 Syncing {total_docs:,} documents...")
    batch = []
    processed = 0
    updated_ner = 0
    updated_topics = 0
    errors = 0
    
    for doc in tqdm(scan(local_es, query=query, index=index_name, size=batch_size), total=total_docs):
        doc_id = doc['_id']
        source = doc['_source']
        
        # Prepare update document
        update_doc = {}
        
        # Add NER entities if present
        if sync_ner and 'ner_entities' in source:
            update_doc['ner_entities'] = source['ner_entities']
            updated_ner += 1
        
        # Add HDBSCAN topic fields if present
        if sync_topics:
            if 'hdbscan_topic_id' in source:
                update_doc['hdbscan_topic_id'] = source['hdbscan_topic_id']
            if 'hdbscan_topic_label' in source:
                update_doc['hdbscan_topic_label'] = source['hdbscan_topic_label']
            if update_doc.get('hdbscan_topic_id') is not None or update_doc.get('hdbscan_topic_label'):
                updated_topics += 1
        
        # Only add to batch if there's something to update
        if update_doc:
            batch.append({
                "_op_type": "update",
                "_index": index_name,
                "_id": doc_id,
                "doc": update_doc
            })
        
        processed += 1
        
        # Bulk update when batch is full
        if len(batch) >= batch_size:
            try:
                success, failed = bulk(remote_es, batch, stats_only=False, raise_on_error=False)
                if failed:
                    errors += len(failed)
                    if errors <= 5:  # Show first 5 errors
                        for fail in failed[:5]:
                            tqdm.write(f"   ⚠️  Error: {fail.get('update', {}).get('error', 'Unknown error')}")
            except Exception as e:
                tqdm.write(f"   ❌ Bulk update error: {e}")
                errors += len(batch)
            batch = []
    
    # Process remaining batch
    if batch:
        try:
            success, failed = bulk(remote_es, batch, stats_only=False, raise_on_error=False)
            if failed:
                errors += len(failed)
        except Exception as e:
            print(f"❌ Final batch error: {e}")
            errors += len(batch)
    
    # Refresh remote index
    print("\n♻️  Refreshing remote index...")
    remote_es.indices.refresh(index=index_name)
    
    # Summary
    print("\n" + "=" * 80)
    print("✅ Sync Complete!")
    print("=" * 80)
    print(f"   Total processed: {processed:,}")
    if sync_ner:
        print(f"   Documents with NER entities: {updated_ner:,}")
    if sync_topics:
        print(f"   Documents with HDBSCAN topics: {updated_topics:,}")
    print(f"   Errors: {errors}")
    print("=" * 80)


def verify_sync(local_es: Elasticsearch, remote_es: Elasticsearch, index_name: str):
    """Verify that sync was successful."""
    print("\n🔍 Verifying sync...")
    
    # Check NER entities
    # Note: count() API doesn't accept 'size' parameter, only 'query'
    local_ner_query = {
        "query": {
            "nested": {
                "path": "ner_entities",
                "query": {"exists": {"field": "ner_entities.entity"}}
            }
        }
    }
    local_ner_count = local_es.count(index=index_name, body=local_ner_query)['count']
    
    remote_ner_count = remote_es.count(index=index_name, body=local_ner_query)['count']
    
    print(f"   Local documents with NER: {local_ner_count:,}")
    print(f"   Remote documents with NER: {remote_ner_count:,}")
    
    # Check HDBSCAN topics
    local_topic_query = {
        "query": {
            "exists": {"field": "hdbscan_topic_id"}
        }
    }
    local_topic_count = local_es.count(index=index_name, body=local_topic_query)['count']
    remote_topic_count = remote_es.count(index=index_name, body=local_topic_query)['count']
    
    print(f"   Local documents with topics: {local_topic_count:,}")
    print(f"   Remote documents with topics: {remote_topic_count:,}")
    
    if local_ner_count == remote_ner_count and local_topic_count == remote_topic_count:
        print("✅ Verification passed!")
    else:
        print("⚠️  Counts don't match - some documents may not have synced")


def main():
    parser = argparse.ArgumentParser(
        description="Sync updated fields (NER entities, HDBSCAN topics) from local to remote ES"
    )
    parser.add_argument(
        "--local-host",
        default=LOCAL_ES_HOST,
        help=f"Local Elasticsearch host (default: {LOCAL_ES_HOST})"
    )
    parser.add_argument(
        "--remote-host",
        default=REMOTE_ES_HOST,
        required=not REMOTE_ES_HOST,
        help="Remote Elasticsearch host (GCP VM IP)"
    )
    parser.add_argument(
        "--index",
        default=INDEX_NAME,
        help=f"Index name (default: {INDEX_NAME})"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=BATCH_SIZE,
        help=f"Batch size for bulk updates (default: {BATCH_SIZE})"
    )
    parser.add_argument(
        "--sync-ner",
        action="store_true",
        default=True,
        help="Sync NER entities (default: True)"
    )
    parser.add_argument(
        "--sync-topics",
        action="store_true",
        default=True,
        help="Sync HDBSCAN topics (default: True)"
    )
    parser.add_argument(
        "--no-ner",
        action="store_true",
        help="Skip NER entities sync"
    )
    parser.add_argument(
        "--no-topics",
        action="store_true",
        help="Skip HDBSCAN topics sync"
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Verify sync after completion"
    )
    
    args = parser.parse_args()
    
    # Determine what to sync
    sync_ner = args.sync_ner and not args.no_ner
    sync_topics = args.sync_topics and not args.no_topics
    
    if not sync_ner and not sync_topics:
        print("❌ Error: At least one field type must be selected for sync")
        sys.exit(1)
    
    # Connect to both ES instances
    local_es = connect_elasticsearch(args.local_host, "LOCAL", args.index)
    remote_es = connect_elasticsearch(args.remote_host, "REMOTE", args.index)
    
    # Perform sync
    sync_updated_fields(
        local_es=local_es,
        remote_es=remote_es,
        index_name=args.index,
        sync_ner=sync_ner,
        sync_topics=sync_topics,
        batch_size=args.batch_size
    )
    
    # Verify if requested
    if args.verify:
        verify_sync(local_es, remote_es, args.index)


if __name__ == "__main__":
    main()

