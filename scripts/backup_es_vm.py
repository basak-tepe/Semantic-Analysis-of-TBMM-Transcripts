#!/usr/bin/env python3
"""
Backup Elasticsearch data directly from VM (no Docker needed).
Run this on the GCP VM where Elasticsearch is running.
"""
from elasticsearch import Elasticsearch
from elasticsearch.helpers import scan
import json
from datetime import datetime
import os
import sys

# Connect directly to Elasticsearch
es = Elasticsearch("http://localhost:9200")

# Verify connection
try:
    info = es.info()
    print(f"✅ Connected to Elasticsearch {info['version']['number']}")
    print(f"   Cluster: {info['cluster_name']}")
    print(f"   Node: {info['name']}")
except Exception as e:
    print(f"❌ Connection failed: {e}")
    print("Make sure Elasticsearch is running on localhost:9200")
    sys.exit(1)

index_name = "parliament_speeches"

# Check index exists
if not es.indices.exists(index=index_name):
    print(f"❌ Index '{index_name}' not found")
    # List available indices
    try:
        indices = es.indices.get_alias("*")
        print(f"Available indices: {list(indices.keys())}")
    except:
        pass
    sys.exit(1)

# Get stats
stats = es.indices.stats(index=index_name)
doc_count = stats['indices'][index_name]['total']['docs']['count']
index_size = stats['indices'][index_name]['total']['store']['size_in_bytes'] / 1024 / 1024
print(f"📊 Index '{index_name}':")
print(f"   Documents: {doc_count:,}")
print(f"   Size: {index_size:.2f} MB")

# Export documents
print(f"\n🔄 Exporting documents (this may take a while)...")
documents = []
count = 0
batch_size = 1000

try:
    for doc in scan(es, index=index_name, scroll='5m', size=batch_size):
        documents.append({
            "_id": doc["_id"],
            "_source": doc["_source"]
        })
        count += 1
        if count % 10000 == 0:
            print(f"  📦 Exported {count:,} documents...")
    
    print(f"\n✅ Exported {count:,} documents")
    
    # Save backup
    backup_file = f"es_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    backup_dir = os.path.expanduser("~/es_backups")
    os.makedirs(backup_dir, exist_ok=True)
    backup_path = os.path.join(backup_dir, backup_file)
    
    print(f"💾 Saving to {backup_path}...")
    with open(backup_path, 'w', encoding='utf-8') as f:
        json.dump(documents, f, ensure_ascii=False, indent=2)
    
    file_size_mb = os.path.getsize(backup_path) / 1024 / 1024
    print(f"\n✅ Backup saved successfully!")
    print(f"   File: {backup_path}")
    print(f"   Size: {file_size_mb:.2f} MB")
    print(f"   Documents: {count:,}")
    print(f"\n📋 To copy to local machine:")
    print(f"   gcloud compute scp tbmm-elasticsearch:{backup_path} . --zone=europe-west3-a")
    
except Exception as e:
    print(f"❌ Error during export: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

