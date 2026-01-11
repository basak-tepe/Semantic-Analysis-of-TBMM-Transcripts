#!/usr/bin/env python3
"""
Display the schema of a speech document from Elasticsearch.

Usage:
    python scripts/show_es_schema.py [OPTIONS]

Options:
    --host HOST          : Elasticsearch host (default: http://localhost:9200)
    --index INDEX        : Index name (default: parliament_speeches)
    --doc-id ID          : Specific document ID to show
    --with-all-fields    : Show document with all fields (keywords, embeddings, NER, topics)
"""
import os
import sys
import json
import argparse
from elasticsearch import Elasticsearch
from typing import Dict, Any

DEFAULT_HOST = os.getenv("ELASTICSEARCH_HOST", "http://localhost:9200")
DEFAULT_INDEX = os.getenv("ELASTICSEARCH_INDEX", "parliament_speeches")


def print_field(name: str, value: Any, indent: int = 0, max_str_length: int = 150):
    """Recursively print field structure."""
    prefix = "  " * indent
    
    if isinstance(value, dict):
        print(f"{prefix}{name} (object):")
        for k, v in sorted(value.items()):
            print_field(k, v, indent + 1, max_str_length)
    elif isinstance(value, list):
        if len(value) > 0:
            if isinstance(value[0], dict):
                print(f"{prefix}{name} (array[object]): {len(value)} items")
                print(f"{prefix}  Structure:")
                for k, v in sorted(value[0].items()):
                    print_field(k, v, indent + 2, max_str_length)
            else:
                t = type(value[0]).__name__
                print(f"{prefix}{name} (array[{t}]): {len(value)} items")
                if t == 'str' and len(value[0]) < 50:
                    print(f"{prefix}  Example: {value[0]}")
                elif t in ['float', 'int']:
                    print(f"{prefix}  Example: {value[0]}")
                elif t == 'str' and len(value[0]) >= 50:
                    print(f"{prefix}  Example: {value[0][:50]}...")
        else:
            print(f"{prefix}{name} (array): []")
    elif isinstance(value, str) and len(value) > max_str_length:
        print(f"{prefix}{name} (string): {value[:max_str_length]}... ({len(value)} chars)")
    else:
        print(f"{prefix}{name} ({type(value).__name__}): {value}")


def get_sample_document(es: Elasticsearch, index: str, doc_id: str = None, with_all_fields: bool = False) -> tuple:
    """Get a sample document from Elasticsearch. Returns (doc, doc_id)."""
    if doc_id:
        # Get specific document
        try:
            result = es.get(index=index, id=doc_id)
            return result['_source'], doc_id
        except Exception as e:
            print(f"❌ Error fetching document {doc_id}: {e}")
            sys.exit(1)
    else:
        # Try to find document with all fields, fallback to partial matches
        queries_to_try = []
        
        if with_all_fields:
            # Try queries in order of completeness
            queries_to_try = [
                ("All fields", {
                    "bool": {
                        "must": [
                            {"exists": {"field": "keywords"}},
                            {"exists": {"field": "keywords_embedding"}},
                            {"exists": {"field": "hdbscan_topic_id"}},
                            {"exists": {"field": "ner_entities"}}
                        ]
                    }
                }),
                ("Keywords + Embeddings + Topics", {
                    "bool": {
                        "must": [
                            {"exists": {"field": "keywords"}},
                            {"exists": {"field": "keywords_embedding"}},
                            {"exists": {"field": "hdbscan_topic_id"}}
                        ]
                    }
                }),
                ("Keywords + Embeddings", {
                    "bool": {
                        "must": [
                            {"exists": {"field": "keywords"}},
                            {"exists": {"field": "keywords_embedding"}}
                        ]
                    }
                }),
                ("Keywords only", {
                    "exists": {"field": "keywords"}
                }),
                ("Any document", {"match_all": {}})
            ]
        else:
            queries_to_try = [("Any document", {"match_all": {}})]
        
        for query_name, query in queries_to_try:
            try:
                result = es.search(
                    index=index,
                    body={"query": query, "size": 1}
                )
                
                if result['hits']['total']['value'] > 0:
                    hit = result['hits']['hits'][0]
                    if with_all_fields and query_name != "Any document":
                        print(f"   ✅ Found document with: {query_name}")
                    return hit['_source'], hit['_id']
            except Exception as e:
                print(f"   ⚠️  Error with query '{query_name}': {e}")
                continue
        
        print("❌ No documents found")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Display Elasticsearch document schema"
    )
    parser.add_argument(
        "--host",
        default=DEFAULT_HOST,
        help=f"Elasticsearch host (default: {DEFAULT_HOST})"
    )
    parser.add_argument(
        "--index",
        default=DEFAULT_INDEX,
        help=f"Index name (default: {DEFAULT_INDEX})"
    )
    parser.add_argument(
        "--doc-id",
        help="Specific document ID to show"
    )
    parser.add_argument(
        "--with-all-fields",
        action="store_true",
        help="Find document with all fields (keywords, embeddings, NER, topics)"
    )
    
    args = parser.parse_args()
    
    # Connect to Elasticsearch
    print(f"🔌 Connecting to Elasticsearch at {args.host}...")
    try:
        es = Elasticsearch(hosts=[args.host])
        if not es.ping():
            raise Exception("Ping failed")
        print(f"✅ Connected to Elasticsearch")
    except Exception as e:
        print(f"❌ Failed to connect: {e}")
        sys.exit(1)
    
    # Check index exists
    if not es.indices.exists(index=args.index):
        print(f"❌ Index '{args.index}' does not exist")
        sys.exit(1)
    
    # Get document
    print(f"\n📥 Fetching document from index '{args.index}'...")
    if args.doc_id:
        print(f"   Document ID: {args.doc_id}")
    elif args.with_all_fields:
        print(f"   Finding document with all fields populated...")
    else:
        print(f"   Fetching first available document...")
    
    doc, fetched_doc_id = get_sample_document(es, args.index, args.doc_id, args.with_all_fields)
    
    # Display schema
    print("\n" + "=" * 80)
    print("ELASTICSEARCH DOCUMENT SCHEMA")
    print("=" * 80)
    print(f"\nDocument ID: {fetched_doc_id}")
    
    print(f"\nAll Fields ({len(doc)} total):")
    print("-" * 80)
    
    for key, value in sorted(doc.items()):
        print_field(key, value)
    
    print("\n" + "=" * 80)
    print(f"Total fields: {len(doc)}")
    print("=" * 80)
    
    # Show field summary
    print("\n📊 Field Summary:")
    print("-" * 80)
    
    field_types = {}
    for key, value in doc.items():
        if isinstance(value, dict):
            field_types[key] = "object"
        elif isinstance(value, list):
            if len(value) > 0:
                field_types[key] = f"array[{type(value[0]).__name__}]"
            else:
                field_types[key] = "array"
        else:
            field_types[key] = type(value).__name__
    
    for field, ftype in sorted(field_types.items()):
        print(f"  {field:30s} : {ftype}")


if __name__ == "__main__":
    main()

