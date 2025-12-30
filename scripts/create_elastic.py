"""
Create Elasticsearch Index for Parliament Speeches

This script creates the parliament_speeches index with proper mappings.
Key features:
- speech_giver.keyword for aggregations (get top speakers)
- speech_title.keyword for exact matching
- political_party_at_time for term-specific party info
"""

from elasticsearch import Elasticsearch, helpers

# Connect to local ES instance
es = Elasticsearch(hosts=["http://localhost:9200"])

try:
    info = es.info()
    print("✅ Connected to Elasticsearch")
    print(f"   Version: {info['version']['number']}")
except Exception as e:
    print("❌ Connection failed:", e)
    exit(1)

index_name = "parliament_speeches"

# Delete existing index (CAUTION: This deletes all data!)
# Comment out after first run to preserve data
print(f"\n🗑️  Deleting existing index '{index_name}' if it exists...")
es.indices.delete(index=index_name, ignore=[400, 404])

# Create index with mapping
print(f"\n🔧 Creating index '{index_name}' with mappings...")

mapping = {
    "properties": {
        "session_id": {"type": "keyword"},
        "term": {"type": "integer"},
        "year": {"type": "integer"},
        "speech_no": {"type": "integer"},
        "province": {"type": "keyword"},
        
        # speech_giver: text for search + keyword subfield for aggregations
        "speech_giver": {
            "type": "text",
            "fields": {
                "keyword": {
                    "type": "keyword",
                    "ignore_above": 256
                }
            }
        },
        
        # political_party: list of strings like ["17.dönem Party1", "18.dönem Party2"]
        "political_party": {"type": "keyword"},
        
        # political_party_at_time: party for the specific term of the speech
        "political_party_at_time": {"type": "keyword"},
        
        "terms_served": {"type": "integer"},
        
        # speech_title: text for search + keyword for exact matching
        "speech_title": {
            "type": "text",
            "fields": {
                "keyword": {
                    "type": "keyword",
                    "ignore_above": 256
                }
            }
        },
        
        "page_ref": {"type": "keyword"},
        "content": {"type": "text"},
        "file": {"type": "keyword"},
        "session_date": {"type": "date", "format": "dd.MM.yyyy||strict_date_optional_time||epoch_millis"},
        "topic_id": {"type": "integer"},
        "topic_label": {"type": "keyword"},
        "topic_analyzed": {"type": "boolean"},
        
        # NER entities: nested array of extracted named entities
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
    es.indices.create(index=index_name, mappings=mapping)
    print(f"✅ Index '{index_name}' created successfully!")
    
    print("\n📋 Key mapping features:")
    print("   • speech_giver.keyword - Use for aggregations (top speakers)")
    print("   • speech_title.keyword - Use for exact title matching")
    print("   • political_party_at_time - Party for specific term")
    print("   • political_party - Full party history (list)")
    
    print("\n💡 Example aggregation query:")
    print('   {')
    print('     "aggs": {')
    print('       "top_speakers": {')
    print('         "terms": {"field": "speech_giver.keyword", "size": 100}')
    print('       }')
    print('     }')
    print('   }')
    
except Exception as e:
    print(f"❌ Error creating index: {e}")
    exit(1)

print("\n" + "=" * 80)
print("✅ Setup complete! You can now run your ingestion scripts.")
print("=" * 80)
    




