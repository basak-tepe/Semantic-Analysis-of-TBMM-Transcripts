"""
Export HDBSCAN Topics to CSV

This script queries Elasticsearch to get all HDBSCAN topic statistics
(ID, label, speech count) and exports them to a CSV file.

Usage:
    python scripts/export_hdbscan_topics.py [--output data/hdbscan_topics.csv]
"""

import csv
import argparse
from pathlib import Path
from elasticsearch import Elasticsearch

# Default configuration
DEFAULT_ES_HOST = "http://localhost:9200"
DEFAULT_INDEX = "parliament_speeches"
DEFAULT_OUTPUT = "data/hdbscan_topics.csv"


def connect_elasticsearch(host: str) -> Elasticsearch:
    """Connect to Elasticsearch and verify connection."""
    es = Elasticsearch(hosts=[host])
    
    try:
        info = es.info()
        print(f"✅ Connected to Elasticsearch")
        print(f"   Version: {info['version']['number']}")
        return es
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        print(f"   Make sure Elasticsearch is running at {host}")
        exit(1)


def get_topic_statistics(es: Elasticsearch, index: str) -> list:
    """
    Query Elasticsearch for HDBSCAN topic statistics.
    
    Returns:
        List of dicts with keys: topic_id, topic_label, speech_count
    """
    query = {
        "size": 0,
        "query": {
            "bool": {
                "must": [
                    {"exists": {"field": "hdbscan_topic_id"}}
                ],
                "must_not": [
                    {"term": {"hdbscan_topic_id": -1}},  # Exclude outliers
                    {"term": {"hdbscan_topic_id": 1}}    # Exclude extraction errors
                ]
            }
        },
        "aggs": {
            "topics": {
                "terms": {
                    "field": "hdbscan_topic_id",
                    "size": 1000,
                    "order": {"_count": "desc"}
                },
                "aggs": {
                    "topic_label": {
                        "terms": {
                            "field": "hdbscan_topic_label.keyword",
                            "size": 1
                        }
                    }
                }
            }
        }
    }
    
    try:
        print(f"\n🔍 Querying Elasticsearch index '{index}'...")
        response = es.search(index=index, body=query)
        
        topics = []
        if 'aggregations' in response and 'topics' in response['aggregations']:
            buckets = response['aggregations']['topics']['buckets']
            
            for bucket in buckets:
                topic_id = bucket['key']
                count = bucket['doc_count']
                
                # Get topic label from nested aggregation
                label_buckets = bucket.get('topic_label', {}).get('buckets', [])
                topic_label = label_buckets[0]['key'] if label_buckets else f"Topic {topic_id}"
                
                topics.append({
                    'topic_id': topic_id,
                    'topic_label': topic_label,
                    'speech_count': count
                })
        
        return topics
        
    except Exception as e:
        print(f"❌ Error querying Elasticsearch: {e}")
        return []


def export_to_csv(topics: list, output_path: str) -> None:
    """Export topics to CSV file."""
    output_file = Path(output_path)
    
    # Create parent directory if it doesn't exist
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=['topic_id', 'topic_label', 'speech_count'])
            writer.writeheader()
            writer.writerows(topics)
        
        print(f"✅ Exported {len(topics)} topics to {output_file}")
        print(f"   Total speeches: {sum(t['speech_count'] for t in topics):,}")
        
    except Exception as e:
        print(f"❌ Error writing CSV file: {e}")
        exit(1)


def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(
        description="Export HDBSCAN topics from Elasticsearch to CSV"
    )
    parser.add_argument(
        '--host',
        default=DEFAULT_ES_HOST,
        help=f"Elasticsearch host URL (default: {DEFAULT_ES_HOST})"
    )
    parser.add_argument(
        '--index',
        default=DEFAULT_INDEX,
        help=f"Elasticsearch index name (default: {DEFAULT_INDEX})"
    )
    parser.add_argument(
        '--output',
        default=DEFAULT_OUTPUT,
        help=f"Output CSV file path (default: {DEFAULT_OUTPUT})"
    )
    
    args = parser.parse_args()
    
    # Connect to Elasticsearch
    es = connect_elasticsearch(args.host)
    
    # Get topic statistics
    topics = get_topic_statistics(es, args.index)
    
    if not topics:
        print("⚠️  No topics found. Make sure HDBSCAN topics are indexed in Elasticsearch.")
        exit(1)
    
    print(f"\n📊 Found {len(topics)} topics")
    
    # Export to CSV
    export_to_csv(topics, args.output)


if __name__ == "__main__":
    main()
