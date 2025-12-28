"""
Clean topic_label Field in Elasticsearch

This script cleans topic_label fields that are longer than 60 characters
and contain formatting patterns by extracting just the topic name.

Patterns handled:
1. **başlık:** Topic Name **gerekçe:** ... → Extract "Topic Name"
2. ... **başlık** Topic Name" → Extract "Topic Name" (at end)
3. ... **proposed Title** Topic Name → Extract "Topic Name"
4. **Topic Name With Multiple Words** ... → Extract if >15 chars and >3 words
"""

from elasticsearch import Elasticsearch, helpers
import re
from typing import Dict, List

# Configuration
ES_HOST = "http://localhost:9200"
INDEX_NAME = "parliament_speeches"
BATCH_SIZE = 500
CHARACTER_THRESHOLD = 60


def clean_topic_label(label: str) -> str:
    """
    Clean a topic label by extracting just the title if it's too long.
    
    Rules:
    1. If label <= 60 characters, return as-is
    2. If contains **başlık:** (with colon), extract text until next **
    3. If contains **başlık** (no colon) at end, extract text after it
    4. If contains **proposed Title** or similar, extract text after it
    5. If starts with **, extract first word group if >15 chars and >3 words
    6. Otherwise, return as-is
    
    Args:
        label: Raw topic label
        
    Returns:
        Cleaned topic label
    """
    if not label or len(label) <= CHARACTER_THRESHOLD:
        return label
    
    # Pattern 1: Check for **başlık:** pattern (with colon)
    if "**başlık:**" in label.lower() or "**baslik:**" in label.lower():
        # Extract text between **başlık:** and next **
        match = re.search(
            r'\*\*(?:başlık|baslik):\*\*\s*(.+?)\s*\*\*',
            label,
            re.IGNORECASE
        )
        
        if match:
            cleaned = match.group(1).strip()
            return cleaned
    
    # Pattern 2: Check for **başlık** at the end (without colon)
    # Format: ... **başlık** Topic Name" or ... **başlık** Topic Name
    if "**başlık**" in label.lower() or "**baslik**" in label.lower():
        match = re.search(
            r'\*\*(?:başlık|baslik)\*\*\s*(.+?)(?:"|$)',
            label,
            re.IGNORECASE
        )
        
        if match:
            cleaned = match.group(1).strip()
            # Remove trailing quote if present
            cleaned = cleaned.rstrip('"').strip()
            if cleaned:
                return cleaned
    
    # Pattern 3: Check for **proposed Title** or similar markers
    # Format: ... **proposed Title** Topic Name
    if "**proposed" in label.lower() or "**önerilen" in label.lower():
        match = re.search(
            r'\*\*(?:proposed|önerilen)\s+(?:title|başlık)\*\*\s*(.+?)$',
            label,
            re.IGNORECASE
        )
        
        if match:
            cleaned = match.group(1).strip()
            # Remove trailing quote if present
            cleaned = cleaned.rstrip('"').strip()
            if cleaned:
                return cleaned
    
    # Pattern 4: Check if starts with ** and has content
    # Format: **Some Topic Name** rest of text...
    match = re.match(r'\*\*([^*]+)\*\*', label)
    if match:
        potential_topic = match.group(1).strip()
        
        # Check criteria: >15 chars and >3 words
        word_count = len(potential_topic.split())
        char_count = len(potential_topic)
        
        if char_count > 15 and word_count > 3:
            return potential_topic
    
    # If no pattern matched, return as-is
    return label


def get_documents_to_clean(es, index_name):
    """
    Get all documents with topic_label and filter by length in Python.
    
    Note: This fetches documents and filters by length in Python since
    topic_label may not have a .keyword subfield for Elasticsearch filtering.
    
    Args:
        es: Elasticsearch client
        index_name: Name of the index
        
    Returns:
        List of documents with their IDs and topic_labels
    """
    print(f"🔍 Fetching documents with topic_label field...")
    
    # Use scroll API for large datasets
    query = {
        "query": {
            "exists": {"field": "topic_label"}
        },
        "_source": ["topic_label"]
    }
    
    try:
        # Initialize scroll
        all_docs = []
        scroll_size = 1000
        
        result = es.search(
            index=index_name,
            body=query,
            scroll='2m',
            size=scroll_size
        )
        
        scroll_id = result['_scroll_id']
        hits = result['hits']['hits']
        
        # Process first batch
        for hit in hits:
            all_docs.append({
                'id': hit['_id'],
                'topic_label': hit['_source'].get('topic_label', '')
            })
        
        # Keep scrolling until no more results
        while len(hits) > 0:
            result = es.scroll(scroll_id=scroll_id, scroll='2m')
            scroll_id = result['_scroll_id']
            hits = result['hits']['hits']
            
            for hit in hits:
                all_docs.append({
                    'id': hit['_id'],
                    'topic_label': hit['_source'].get('topic_label', '')
                })
        
        # Clear scroll
        es.clear_scroll(scroll_id=scroll_id)
        
        print(f"📊 Found {len(all_docs):,} total documents with topic_label")
        
        # Filter by length in Python
        documents = [
            doc for doc in all_docs 
            if len(doc['topic_label']) > CHARACTER_THRESHOLD
        ]
        
        print(f"📊 {len(documents):,} documents have topic_label > {CHARACTER_THRESHOLD} characters")
        return documents
        
    except Exception as e:
        print(f"❌ Error searching documents: {e}")
        return []


def clean_documents(es, index_name, documents):
    """
    Clean topic_label fields and update in Elasticsearch.
    
    Args:
        es: Elasticsearch client
        index_name: Name of the index
        documents: List of documents to clean
        
    Returns:
        Dictionary with statistics
    """
    print("\n🧹 Cleaning topic labels...")
    
    stats = {
        'total': len(documents),
        'cleaned': 0,
        'unchanged': 0,
        'errors': 0,
        'pattern1': 0,  # **başlık:** pattern
        'pattern2': 0,  # **başlık** at end pattern
        'pattern3': 0,  # **proposed Title** pattern
        'pattern4': 0,  # **Topic Name** pattern
    }
    
    actions = []
    cleaned_examples = []
    
    for doc in documents:
        original_label = doc['topic_label']
        cleaned_label = clean_topic_label(original_label)
        
        if original_label != cleaned_label:
            stats['cleaned'] += 1
            
            # Detect which pattern was used
            if "**başlık:**" in original_label.lower() or "**baslik:**" in original_label.lower():
                stats['pattern1'] += 1
                pattern = "Pattern 1 (**başlık:**)"
            elif ("**başlık**" in original_label.lower() or "**baslik**" in original_label.lower()) and \
                 ("**başlık:**" not in original_label.lower() and "**baslik:**" not in original_label.lower()):
                stats['pattern2'] += 1
                pattern = "Pattern 2 (**başlık** at end)"
            elif "**proposed" in original_label.lower() or "**önerilen" in original_label.lower():
                stats['pattern3'] += 1
                pattern = "Pattern 3 (**proposed Title**)"
            elif original_label.startswith("**"):
                stats['pattern4'] += 1
                pattern = "Pattern 4 (**Topic**)"
            else:
                pattern = "Unknown"
            
            # Save first 10 examples (5 from each pattern)
            if len(cleaned_examples) < 10:
                cleaned_examples.append({
                    'id': doc['id'],
                    'original': original_label[:100] + "..." if len(original_label) > 100 else original_label,
                    'cleaned': cleaned_label,
                    'pattern': pattern
                })
            
            # Prepare bulk update action
            actions.append({
                '_op_type': 'update',
                '_index': index_name,
                '_id': doc['id'],
                'doc': {
                    'topic_label': cleaned_label
                }
            })
        else:
            stats['unchanged'] += 1
    
    # Show examples before updating
    if cleaned_examples:
        print(f"\n📋 Sample cleanings (showing {len(cleaned_examples)}):")
        for i, example in enumerate(cleaned_examples, 1):
            print(f"\n{i}. [{example['pattern']}]")
            print(f"   Document ID: {example['id']}")
            print(f"   Original: {example['original']}")
            print(f"   Cleaned:  {example['cleaned']}")
    
    # Perform bulk update
    if actions:
        print(f"\n💾 Updating {len(actions):,} documents in batches of {BATCH_SIZE}...")
        
        try:
            success, errors = helpers.bulk(
                es,
                actions,
                chunk_size=BATCH_SIZE,
                raise_on_error=False
            )
            
            stats['errors'] = len(errors) if errors else 0
            
            if errors:
                print(f"⚠️  {stats['errors']} documents had errors")
                for error in errors[:3]:
                    print(f"   Error: {error}")
            
        except Exception as e:
            print(f"❌ Bulk update error: {e}")
            stats['errors'] = len(actions)
    
    return stats


def verify_cleaning(es, index_name):
    """
    Verify that cleaning worked by sampling some documents.
    
    Args:
        es: Elasticsearch client
        index_name: Name of the index
    """
    print("\n✅ Verifying cleaning...")
    
    query = {
        "query": {
            "exists": {"field": "topic_label"}
        },
        "_source": ["topic_label"],
        "size": 100
    }
    
    try:
        result = es.search(index=index_name, body=query)
        
        long_labels = []
        for hit in result['hits']['hits']:
            label = hit['_source'].get('topic_label', '')
            if len(label) > CHARACTER_THRESHOLD:
                long_labels.append(label)
        
        if not long_labels:
            print("✅ All sampled topic labels are clean (≤ 60 characters)!")
        else:
            print(f"⚠️  Found {len(long_labels)} documents in sample with long topic_label")
            print("   (These might not match any cleaning pattern)")
            
            for label in long_labels[:3]:
                print(f"\n   Example ({len(label)} chars): {label[:100]}...")
        
    except Exception as e:
        print(f"⚠️  Could not verify: {e}")


def main():
    """Main execution function."""
    print("=" * 80)
    print("ELASTICSEARCH TOPIC LABEL CLEANING")
    print("=" * 80)
    print(f"Index: {INDEX_NAME}")
    print(f"Threshold: {CHARACTER_THRESHOLD} characters")
    print("\nPatterns detected:")
    print("  1. **başlık:** Topic Name **gerekçe:** ...")
    print("  2. ... **başlık** Topic Name\" (at end)")
    print("  3. ... **proposed Title** Topic Name")
    print("  4. **Topic Name With Words** ... (if >15 chars and >3 words)")
    print("=" * 80)
    
    # Connect to Elasticsearch
    try:
        es = Elasticsearch(hosts=[ES_HOST])
        
        if not es.ping():
            print(f"❌ Cannot connect to Elasticsearch at {ES_HOST}")
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
    
    # Step 1: Get documents to clean
    documents = get_documents_to_clean(es, INDEX_NAME)
    
    if not documents:
        print("\n✅ No documents need cleaning!")
        return
    
    # Step 2: Clean and update
    stats = clean_documents(es, INDEX_NAME, documents)
    
    # Step 3: Show statistics
    print("\n" + "=" * 80)
    print("📊 CLEANING STATISTICS")
    print("=" * 80)
    print(f"Total documents checked: {stats['total']:,}")
    print(f"🔧 Cleaned: {stats['cleaned']:,}")
    print(f"   • Pattern 1 (**başlık:** ...): {stats['pattern1']:,}")
    print(f"   • Pattern 2 (... **başlık** Topic): {stats['pattern2']:,}")
    print(f"   • Pattern 3 (**proposed Title** ...): {stats['pattern3']:,}")
    print(f"   • Pattern 4 (**Topic** ...): {stats['pattern4']:,}")
    print(f"✓ Unchanged: {stats['unchanged']:,}")
    print(f"❌ Errors: {stats['errors']:,}")
    print("=" * 80)
    
    # Step 4: Verify
    verify_cleaning(es, INDEX_NAME)
    
    # Final message
    print("\n" + "=" * 80)
    print("✅ CLEANING COMPLETE!")
    print("=" * 80)
    
    if stats['cleaned'] > 0:
        print(f"\n💡 {stats['cleaned']:,} topic labels have been cleaned.")
        print("   Clean, display-ready format")
    
    print("\n🔍 To verify specific documents:")
    print(f'   curl "http://localhost:9200/{INDEX_NAME}/_search?q=topic_label:*&size=5"')


if __name__ == "__main__":
    main()
