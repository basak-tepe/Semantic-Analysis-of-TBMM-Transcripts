"""
Check if keywords field exists in Elasticsearch and show examples
"""
import os
from elasticsearch import Elasticsearch

# Configuration
ELASTICSEARCH_HOST = os.getenv("ELASTICSEARCH_HOST", "http://localhost:9200")
ELASTICSEARCH_INDEX = os.getenv("ELASTICSEARCH_INDEX", "parliament_speeches")

def check_keywords_field():
    """Check if keywords field exists and show examples."""
    
    print("=" * 80)
    print("Checking for 'keywords' field in Elasticsearch")
    print("=" * 80)
    
    try:
        # Connect to Elasticsearch
        print(f"\n🔌 Connecting to Elasticsearch at {ELASTICSEARCH_HOST}...")
        es = Elasticsearch(hosts=[ELASTICSEARCH_HOST])
        
        if not es.ping():
            print("❌ Could not connect to Elasticsearch")
            return
        
        print(f"✅ Connected to Elasticsearch")
        
        # Get total count
        total_count = es.count(index=ELASTICSEARCH_INDEX)['count']
        print(f"📊 Total documents in index: {total_count:,}")
        
        # Check for documents with keywords field
        query_with_keywords = {
            "query": {
                "exists": {"field": "keywords"}
            }
        }
        
        keywords_count = es.count(index=ELASTICSEARCH_INDEX, body=query_with_keywords)['count']
        print(f"\n📊 Documents WITH keywords field: {keywords_count:,}")
        print(f"📊 Documents WITHOUT keywords field: {(total_count - keywords_count):,}")
        
        if keywords_count > 0:
            percentage = (keywords_count / total_count) * 100
            print(f"✅ Keywords field exists! ({percentage:.1f}% of documents have keywords)")
            
            # Get mapping to see field type
            print("\n🔍 Field mapping:")
            mapping = es.indices.get_mapping(index=ELASTICSEARCH_INDEX)
            keywords_mapping = mapping[ELASTICSEARCH_INDEX]['mappings']['properties'].get('keywords')
            keywords_str_mapping = mapping[ELASTICSEARCH_INDEX]['mappings']['properties'].get('keywords_str')
            
            if keywords_mapping:
                print(f"   keywords: {keywords_mapping}")
            if keywords_str_mapping:
                print(f"   keywords_str: {keywords_str_mapping}")
            
            # Get some examples
            print("\n📋 Example documents with keywords:\n")
            
            search_result = es.search(
                index=ELASTICSEARCH_INDEX,
                body={
                    "query": {"exists": {"field": "keywords"}},
                    "size": 5,
                    "_source": ["speech_giver", "keywords", "keywords_str", "groq_topic_label", "year"]
                }
            )
            
            for i, hit in enumerate(search_result['hits']['hits'], 1):
                doc = hit['_source']
                print(f"\n{i}. Speech ID: {hit['_id']}")
                print(f"   Speaker: {doc.get('speech_giver', 'N/A')}")
                print(f"   Year: {doc.get('year', 'N/A')}")
                print(f"   Topic: {doc.get('groq_topic_label', 'N/A')[:60]}...")
                
                keywords = doc.get('keywords', [])
                if isinstance(keywords, list):
                    print(f"   Keywords (array): {keywords[:10]}")  # Show first 10
                    print(f"   Total keywords: {len(keywords)}")
                else:
                    print(f"   Keywords: {keywords}")
                
                if 'keywords_str' in doc:
                    keywords_str = doc['keywords_str'][:100]
                    print(f"   Keywords (string): {keywords_str}...")
            
            # Stats
            print("\n" + "=" * 80)
            print("📈 Summary Statistics:")
            print("=" * 80)
            print(f"Total speeches: {total_count:,}")
            print(f"Speeches with keywords: {keywords_count:,} ({percentage:.1f}%)")
            print(f"Speeches without keywords: {(total_count - keywords_count):,} ({(100-percentage):.1f}%)")
            
        else:
            print("❌ No documents have the 'keywords' field yet")
            print("   Run the keyword extraction notebook/script to populate this field")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_keywords_field()
