# Complete backup script - works without Docker
from elasticsearch import Elasticsearch
from elasticsearch.helpers import scan
import json
from datetime import datetime
import os

# Connect via your Cloudflare tunnel URL
es = Elasticsearch("https://filme-receive-cir-inherited.trycloudflare.com")

# Verify connection
try:
    info = es.info()
    print(f"✅ Connected to Elasticsearch {info['version']['number']}")
except Exception as e:
    print(f"❌ Connection failed: {e}")
    exit(1)

# Check index exists
index_name = "parliament_speeches"
if not es.indices.exists(index=index_name):
    print(f"❌ Index '{index_name}' not found")
    exit(1)

# Get index stats
stats = es.indices.stats(index=index_name)
doc_count = stats['indices'][index_name]['total']['docs']['count']
print(f"📊 Index has {doc_count:,} documents")

# Export all documents
print("\n🔄 Exporting documents (this may take a while)...")
documents = []
count = 0
batch_size = 1000

query = {
    "query": {"match_all": {}},
    "_source": True
}

try:
    for doc in scan(es, query=query, index=index_name, scroll='5m', size=batch_size):
        documents.append({
            "_id": doc["_id"],
            "_source": doc["_source"]
        })
        count += 1
        if count % 10000 == 0:
            print(f"  📦 Exported {count:,} documents...")
    
    print(f"\n✅ Exported {count:,} documents")
    
    # Save to file
    backup_file = f"es_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    backup_path = os.path.join("backups", backup_file)
    os.makedirs("backups", exist_ok=True)
    
    print(f"💾 Saving to {backup_path}...")
    with open(backup_path, 'w', encoding='utf-8') as f:
        json.dump(documents, f, ensure_ascii=False, indent=2)
    
    file_size_mb = os.path.getsize(backup_path) / 1024 / 1024
    print(f"✅ Backup saved successfully!")
    print(f"   File: {backup_path}")
    print(f"   Size: {file_size_mb:.2f} MB")
    print(f"   Documents: {count:,}")
    
except Exception as e:
    print(f"❌ Error during export: {e}")
    import traceback
    traceback.print_exc()