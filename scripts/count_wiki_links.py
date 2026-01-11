#!/usr/bin/env python3
"""
Count speeches with Wikipedia links in their NER entities.
"""

import os
import sys
from elasticsearch import Elasticsearch
from elasticsearch.helpers import scan

# Configuration
ELASTICSEARCH_HOST = os.getenv("ELASTICSEARCH_HOST", "http://localhost:9200")
ELASTICSEARCH_INDEX = os.getenv("ELASTICSEARCH_INDEX", "parliament_speeches")

def count_wiki_links(term_filter=None):
    """Count speeches with Wikipedia links in NER entities.
    
    Args:
        term_filter: Optional term number to filter by (e.g., 27)
    """
    
    # Connect to Elasticsearch
    print(f"📡 Connecting to Elasticsearch at {ELASTICSEARCH_HOST}...")
    try:
        es = Elasticsearch(hosts=[ELASTICSEARCH_HOST])
        if not es.ping():
            raise Exception("Ping failed")
        print("✅ Connected to Elasticsearch")
        
        # Refresh index to ensure all updates are visible
        print("♻️  Refreshing index to ensure all updates are visible...")
        try:
            es.indices.refresh(index=ELASTICSEARCH_INDEX)
            print("✅ Index refreshed")
        except Exception as e:
            print(f"⚠️  Warning: Could not refresh index: {e}")
    except Exception as e:
        print(f"❌ Failed to connect: {e}")
        sys.exit(1)
    
    # Build query with optional term filter
    term_filter_clause = []
    if term_filter:
        term_filter_clause = [{"term": {"term": term_filter}}]
        print(f"\n🔍 Filtering by term: {term_filter}")
    
    # First, check a sample document to see the structure
    print("\n🔍 Checking sample document structure...")
    sample_check = {
        "query": {
            "bool": {
                "must": term_filter_clause + [
                    {
                        "nested": {
                            "path": "ner_entities",
                            "query": {
                                "exists": {"field": "ner_entities.entity"}
                            }
                        }
                    }
                ]
            }
        },
        "size": 1,
        "_source": ["ner_entities", "term"]
    }
    
    try:
        response = es.search(index=ELASTICSEARCH_INDEX, **sample_check)
        if response['hits']['total']['value'] > 0:
            sample_doc = response['hits']['hits'][0]['_source']
            entities = sample_doc.get('ner_entities', [])
            print(f"   Sample document has {len(entities)} entities")
            if entities:
                sample_entity = entities[0]
                print(f"   Sample entity structure:")
                print(f"      - entity: {sample_entity.get('entity', 'N/A')}")
                print(f"      - wikipedia_url: {sample_entity.get('wikipedia_url', 'N/A')}")
                print(f"      - wikipedia_url type: {type(sample_entity.get('wikipedia_url'))}")
                print(f"      - wikipedia_url is None: {sample_entity.get('wikipedia_url') is None}")
                print(f"      - wikipedia_url is empty string: {sample_entity.get('wikipedia_url') == ''}")
        else:
            print("   ⚠️  No documents with NER entities found")
    except Exception as e:
        print(f"⚠️  Error checking sample: {e}")
    
    # Query 1: Count total documents with NER entities
    print("\n📊 Counting documents...")
    
    query_with_ner = {
        "query": {
            "bool": {
                "must": term_filter_clause + [
                    {
                        "nested": {
                            "path": "ner_entities",
                            "query": {
                                "exists": {"field": "ner_entities.entity"}
                            }
                        }
                    }
                ]
            }
        },
        "size": 0
    }
    
    try:
        response = es.search(index=ELASTICSEARCH_INDEX, **query_with_ner)
        total_with_ner = response['hits']['total']['value']
        print(f"   Total documents with NER entities: {total_with_ner:,}")
    except Exception as e:
        print(f"❌ Error counting documents with NER: {e}")
        sys.exit(1)
    
    # Query 2: Count documents with at least one Wikipedia link
    # Use a manual scan approach since nested queries can be tricky
    print("\n🔍 Scanning documents to count Wikipedia links...")
    
    total_with_wiki = 0
    total_entities_count = 0
    entities_with_wiki_count = 0
    
    scan_query = {
        "query": {
            "bool": {
                "must": term_filter_clause + [
                    {
                        "nested": {
                            "path": "ner_entities",
                            "query": {
                                "exists": {"field": "ner_entities.entity"}
                            }
                        }
                    }
                ]
            }
        },
        "_source": ["ner_entities", "term"]
    }
    
    try:
        from elasticsearch.helpers import scan
        from tqdm import tqdm
        
        print("   Scanning documents...")
        for doc in tqdm(scan(es, query=scan_query, index=ELASTICSEARCH_INDEX, size=1000), 
                       total=min(total_with_ner, 10000), desc="   Progress"):
            entities = doc.get('_source', {}).get('ner_entities', [])
            has_wiki = False
            
            for entity in entities:
                total_entities_count += 1
                wiki_url = entity.get('wikipedia_url')
                if wiki_url and wiki_url.strip():  # Non-empty string
                    entities_with_wiki_count += 1
                    has_wiki = True
            
            if has_wiki:
                total_with_wiki += 1
        
        print(f"   Documents with Wikipedia links: {total_with_wiki:,}")
        print(f"   Total entities scanned: {total_entities_count:,}")
        print(f"   Entities with Wikipedia links: {entities_with_wiki_count:,}")
        
    except ImportError:
        print("   ⚠️  tqdm not available, using simple query instead...")
        # Fallback to query approach
        query_with_wiki = {
            "query": {
                "nested": {
                    "path": "ner_entities",
                    "query": {
                        "bool": {
                            "must": [
                                {"exists": {"field": "ner_entities.entity"}},
                                {
                                    "bool": {
                                        "must": [
                                            {"exists": {"field": "ner_entities.wikipedia_url"}},
                                            {"wildcard": {"ner_entities.wikipedia_url": "*"}}
                                        ]
                                    }
                                }
                            ]
                        }
                    }
                }
            },
            "size": 0
        }
        
        try:
            response = es.search(index=ELASTICSEARCH_INDEX, **query_with_wiki)
            total_with_wiki = response['hits']['total']['value']
            print(f"   Documents with Wikipedia links: {total_with_wiki:,}")
        except Exception as e:
            print(f"❌ Error counting documents with Wikipedia links: {e}")
            sys.exit(1)
    except Exception as e:
        print(f"❌ Error scanning documents: {e}")
        sys.exit(1)
    
    # Query 3: Get sample documents to show statistics
    print("\n📈 Detailed Statistics:")
    
    # Get a sample of documents with Wikipedia links
    sample_query = {
        "query": {
            "nested": {
                "path": "ner_entities",
                "query": {
                    "bool": {
                        "must": [
                            {"exists": {"field": "ner_entities.entity"}},
                            {
                                "bool": {
                                    "must": [
                                        {"exists": {"field": "ner_entities.wikipedia_url"}},
                                        {"wildcard": {"ner_entities.wikipedia_url": "*"}}  # Non-empty
                                    ]
                                }
                            }
                        ]
                    }
                }
            }
        },
        "size": 1000,
        "_source": ["ner_entities", "term", "year"]
    }
    
    try:
        response = es.search(index=ELASTICSEARCH_INDEX, **sample_query)
        docs = response['hits']['hits']
        
        # Count entities with Wikipedia links
        total_entities = 0
        entities_with_wiki = 0
        entities_by_term = {}
        
        for doc in docs:
            entities = doc['_source'].get('ner_entities', [])
            term = doc['_source'].get('term')
            
            if term not in entities_by_term:
                entities_by_term[term] = {'total': 0, 'with_wiki': 0}
            
            for entity in entities:
                total_entities += 1
                entities_by_term[term]['total'] += 1
                
                if entity.get('wikipedia_url'):
                    entities_with_wiki += 1
                    entities_by_term[term]['with_wiki'] += 1
        
        print(f"\n   Sample analysis (from {len(docs)} documents):")
        print(f"   Total entities: {total_entities:,}")
        print(f"   Entities with Wikipedia links: {entities_with_wiki:,}")
        if total_entities > 0:
            percentage = (entities_with_wiki / total_entities) * 100
            print(f"   Percentage: {percentage:.1f}%")
        
        # Show breakdown by term
        if entities_by_term:
            print(f"\n   Breakdown by term:")
            for term in sorted(entities_by_term.keys()):
                term_stats = entities_by_term[term]
                term_total = term_stats['total']
                term_wiki = term_stats['with_wiki']
                if term_total > 0:
                    term_pct = (term_wiki / term_total) * 100
                    print(f"      Term {term}: {term_wiki:,}/{term_total:,} ({term_pct:.1f}%)")
    
    except Exception as e:
        print(f"⚠️  Error getting detailed statistics: {e}")
    
    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"   Documents with NER entities: {total_with_ner:,}")
    print(f"   Documents with Wikipedia links: {total_with_wiki:,}")
    if total_with_ner > 0:
        doc_percentage = (total_with_wiki / total_with_ner) * 100
        print(f"   Percentage of documents with Wikipedia links: {doc_percentage:.1f}%")
    print("=" * 80)

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Count speeches with Wikipedia links")
    parser.add_argument("--term", type=int, help="Filter by term number (e.g., 27)")
    args = parser.parse_args()
    
    count_wiki_links(term_filter=args.term)

