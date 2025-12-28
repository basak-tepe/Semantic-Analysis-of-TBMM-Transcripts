"""
Update Elasticsearch Mapping for speech_giver Field

This script adds a keyword subfield to speech_giver to enable aggregations.
The mapping will be: speech_giver.keyword
"""

from elasticsearch import Elasticsearch
import json

# Configuration
ES_HOST = "http://localhost:9200"
INDEX_NAME = "parliament_speeches"


def check_current_mapping(es, index_name):
    """Check the current mapping for speech_giver field."""
    try:
        mapping = es.indices.get_mapping(index=index_name)
        speech_giver_mapping = mapping[index_name]['mappings']['properties'].get('speech_giver', {})
        
        print("📋 Current speech_giver mapping:")
        print(json.dumps(speech_giver_mapping, indent=2))
        return speech_giver_mapping
    except Exception as e:
        print(f"⚠️ Error getting mapping: {e}")
        return None


def update_mapping(es, index_name):
    """
    Update the mapping to add keyword subfield to speech_giver.
    
    This uses the PUT mapping API which allows adding new fields
    but cannot change existing field types.
    """
    mapping = {
        "properties": {
            "speech_giver": {
                "type": "text",
                "fields": {
                    "keyword": {
                        "type": "keyword",
                        "ignore_above": 256  # Standard limit for keywords
                    }
                }
            }
        }
    }
    
    try:
        response = es.indices.put_mapping(
            index=index_name,
            body=mapping
        )
        
        if response.get('acknowledged'):
            print("✅ Mapping updated successfully!")
            print("\n📌 You can now use 'speech_giver.keyword' for aggregations:")
            print("   - Exact match filtering")
            print("   - Terms aggregations")
            print("   - Sorting")
            return True
        else:
            print("❌ Mapping update failed")
            return False
            
    except Exception as e:
        print(f"❌ Error updating mapping: {e}")
        print("\n💡 If you get a 'mapper_parsing_exception', you may need to reindex.")
        print("   This happens if speech_giver is already a different type.")
        return False


def test_aggregation(es, index_name):
    """Test aggregation on speech_giver.keyword field."""
    try:
        # Get top 10 MPs by speech count
        query = {
            "size": 0,
            "aggs": {
                "top_speakers": {
                    "terms": {
                        "field": "speech_giver.keyword",
                        "size": 10
                    }
                }
            }
        }
        
        response = es.search(index=index_name, body=query)
        
        print("\n📊 Top 10 Speakers (Test Aggregation):")
        for bucket in response['aggregations']['top_speakers']['buckets']:
            print(f"   {bucket['key']}: {bucket['doc_count']} speeches")
        
        return True
        
    except Exception as e:
        print(f"❌ Test aggregation failed: {e}")
        return False


def main():
    """Main execution function."""
    print("=" * 80)
    print("ELASTICSEARCH MAPPING UPDATE - speech_giver.keyword")
    print("=" * 80)
    
    # Connect to Elasticsearch
    try:
        es = Elasticsearch(hosts=[ES_HOST])
        
        if not es.ping():
            print("❌ Cannot connect to Elasticsearch at", ES_HOST)
            return
        
        print(f"✅ Connected to Elasticsearch at {ES_HOST}\n")
        
    except Exception as e:
        print(f"❌ Elasticsearch connection failed: {e}")
        return
    
    # Check if index exists
    if not es.indices.exists(index=INDEX_NAME):
        print(f"❌ Index '{INDEX_NAME}' does not exist")
        return
    
    print(f"✅ Index '{INDEX_NAME}' found\n")
    
    # Step 1: Check current mapping
    print("STEP 1: Checking current mapping...")
    print("-" * 80)
    current_mapping = check_current_mapping(es, INDEX_NAME)
    print()
    
    # Step 2: Update mapping
    print("STEP 2: Updating mapping to add keyword subfield...")
    print("-" * 80)
    success = update_mapping(es, INDEX_NAME)
    print()
    
    if not success:
        print("⚠️ Mapping update failed. You may need to reindex your data.")
        print("   See reindex instructions in the documentation.")
        return
    
    # Step 3: Verify new mapping
    print("STEP 3: Verifying updated mapping...")
    print("-" * 80)
    check_current_mapping(es, INDEX_NAME)
    print()
    
    # Step 4: Test aggregation
    print("STEP 4: Testing aggregation with speech_giver.keyword...")
    print("-" * 80)
    test_aggregation(es, INDEX_NAME)
    print()
    
    # Final instructions
    print("=" * 80)
    print("✅ SETUP COMPLETE!")
    print("=" * 80)
    print("\n📌 Usage in queries:")
    print("\n1. Aggregation (Get MP speech counts):")
    print('   {')
    print('     "size": 0,')
    print('     "aggs": {')
    print('       "speakers": {')
    print('         "terms": {"field": "speech_giver.keyword", "size": 100}')
    print('       }')
    print('     }')
    print('   }')
    
    print("\n2. Exact match filter:")
    print('   {')
    print('     "query": {')
    print('       "term": {"speech_giver.keyword": "Özgür Özel"}')
    print('     }')
    print('   }')
    
    print("\n3. Multiple MPs filter:")
    print('   {')
    print('     "query": {')
    print('       "terms": {"speech_giver.keyword": ["Özgür Özel", "Devlet Bahçeli"]}')
    print('     }')
    print('   }')
    
    print("\n💡 Note: If you have existing documents, they will automatically")
    print("   get the .keyword subfield. No reindexing needed!")
    print("=" * 80)


if __name__ == "__main__":
    main()
