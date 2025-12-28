#!/usr/bin/env python3
"""
Update Elasticsearch Topic Labels

This script updates topic labels in Elasticsearch with LLM-generated readable names
WITHOUT re-running BERTopic analysis. It uses existing topic_details.csv.

Use this when:
- You want to regenerate topic names with different prompts
- You want to improve existing topic labels
- Your ES documents already have topic_id but need better labels
"""

import os
import sys
import argparse
from pathlib import Path

# Try to load .env file if dotenv is available (optional)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv not installed, will use system environment variables

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from llm_topic_namer import GroqTopicNamer, process_all_topics, update_elasticsearch_topic_labels
from elasticsearch import Elasticsearch


def connect_to_elasticsearch(host: str = "http://localhost:9200") -> Elasticsearch:
    """
    Connect to Elasticsearch and verify connection.
    
    Args:
        host: Elasticsearch host URL
        
    Returns:
        Elasticsearch client instance
    """
    print(f"🔌 Connecting to Elasticsearch at {host}...")
    
    try:
        es = Elasticsearch(hosts=[host])
        
        if es.ping():
            print(f"✅ Connected to Elasticsearch")
            return es
        else:
            raise Exception("Ping failed")
            
    except Exception as e:
        print(f"❌ Failed to connect to Elasticsearch: {e}")
        print(f"   Make sure Elasticsearch is running on {host}")
        sys.exit(1)


def verify_topic_details_exists(csv_path: str) -> bool:
    """
    Verify that topic_details.csv exists.
    
    Args:
        csv_path: Path to topic_details.csv
        
    Returns:
        True if file exists, False otherwise
    """
    if not os.path.exists(csv_path):
        print(f"❌ Error: {csv_path} not found!")
        print("\n   This file is created by analyze_speech_topics.py")
        print("   You need to run topic analysis first:")
        print("   cd src && python analyze_speech_topics.py")
        return False
    
    print(f"✅ Found topic_details.csv at {csv_path}")
    return True


def verify_es_has_topics(es: Elasticsearch, index: str) -> bool:
    """
    Verify that Elasticsearch has documents with topic_id field.
    
    Args:
        es: Elasticsearch client
        index: Index name
        
    Returns:
        True if topics exist, False otherwise
    """
    print(f"\n📊 Checking if {index} has topic assignments...")
    
    try:
        # Count documents with topic_id
        response = es.count(
            index=index,
            body={
                "query": {
                    "exists": {"field": "topic_id"}
                }
            }
        )
        
        count = response.get('count', 0)
        
        if count == 0:
            print(f"❌ No documents with topic_id found in {index}")
            print("\n   Run topic analysis first:")
            print("   cd src && python analyze_speech_topics.py")
            return False
        
        print(f"✅ Found {count:,} documents with topic assignments")
        
        # Get a sample to show current labels
        sample = es.search(
            index=index,
            body={"query": {"exists": {"field": "topic_id"}}, "size": 1}
        )
        
        if sample['hits']['total']['value'] > 0:
            doc = sample['hits']['hits'][0]['_source']
            print(f"\n   Sample document:")
            print(f"   • topic_id: {doc.get('topic_id')}")
            print(f"   • current topic_label: {doc.get('topic_label')}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error checking topics: {e}")
        return False


def preview_changes(topic_mapping: dict, limit: int = 10):
    """
    Preview the topic name changes.
    
    Args:
        topic_mapping: Dictionary of topic_id -> new_name
        limit: Number of examples to show
    """
    print(f"\n📋 Preview of {len(topic_mapping)} topic name changes:")
    print("=" * 80)
    
    for idx, (topic_id, new_name) in enumerate(sorted(topic_mapping.items())[:limit], 1):
        print(f"{idx:3d}. Topic {topic_id:3d}: {new_name}")
    
    if len(topic_mapping) > limit:
        print(f"     ... and {len(topic_mapping) - limit} more topics")
    
    print("=" * 80)


def main():
    """Main execution flow."""
    # Get the project root directory (parent of scripts directory)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    default_csv_path = os.path.join(project_root, 'data', 'data_secret', 'topic_details.csv')
    
    parser = argparse.ArgumentParser(
        description="Update Elasticsearch topic labels with LLM-generated names",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Update with default settings
  python update_topic_labels.py
  
  # Specify custom paths
  python update_topic_labels.py --csv /path/to/topic_details.csv --index my_index
  
  # Dry run (preview only, no updates)
  python update_topic_labels.py --dry-run
  
  # Use different Groq model
  export GROQ_MODEL="mixtral-8x7b-32768"
  python update_topic_labels.py
        """
    )
    
    parser.add_argument(
        '--csv',
        default=default_csv_path,
        help=f'Path to topic_details.csv (default: {default_csv_path})'
    )
    
    parser.add_argument(
        '--index',
        default='parliament_speeches',
        help='Elasticsearch index name (default: parliament_speeches)'
    )
    
    parser.add_argument(
        '--host',
        default='http://localhost:9200',
        help='Elasticsearch host (default: http://localhost:9200)'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Preview changes without updating Elasticsearch'
    )
    
    parser.add_argument(
        '--api-key',
        default=None,
        help='Groq API key (or set GROQ_API_KEY env var)'
    )
    
    args = parser.parse_args()
    
    # Resolve CSV path to absolute path
    csv_path = os.path.abspath(args.csv)
    
    # Print header
    print("=" * 80)
    print("ELASTICSEARCH TOPIC LABEL UPDATER")
    print("=" * 80)
    print("\nThis script updates topic labels in Elasticsearch with LLM-generated")
    print("readable names WITHOUT re-running BERTopic analysis.\n")
    print(f"📁 Looking for CSV at: {csv_path}\n")
    
    # Check API key
    api_key = args.api_key or os.getenv("GROQ_API_KEY", "")
    if not api_key:
        print("❌ Error: GROQ_API_KEY not set!")
        print("\n   Set it with:")
        print("   export GROQ_API_KEY='your-api-key'")
        print("\n   Or use --api-key flag:")
        print("   python update_topic_labels.py --api-key 'your-key'")
        print("\n   Get free API key at: https://console.groq.com/keys")
        sys.exit(1)
    
    print(f"✅ Groq API key found")
    print(f"✅ Model: {os.getenv('GROQ_MODEL')}")
    
    # Step 1: Verify topic_details.csv exists
    if not verify_topic_details_exists(csv_path):
        sys.exit(1)
    
    # Step 2: Connect to Elasticsearch
    es = connect_to_elasticsearch(args.host)
    
    # Step 3: Verify ES has topics
    if not verify_es_has_topics(es, args.index):
        sys.exit(1)
    
    # Step 4: Generate new topic names with LLM
    print("\n" + "=" * 80)
    print("🤖 GENERATING READABLE TOPIC NAMES")
    print("=" * 80)
    
    try:
        topic_mapping = process_all_topics(csv_path, api_key=api_key)
        
        if not topic_mapping:
            print("❌ No topic mappings generated!")
            sys.exit(1)
        
        print(f"\n✅ Successfully generated {len(topic_mapping)} topic names")
        
    except Exception as e:
        print(f"❌ Error generating topic names: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    # Step 5: Preview changes
    preview_changes(topic_mapping)
    
    # Step 6: Update Elasticsearch (or dry run)
    if args.dry_run:
        print("\n⚠️  DRY RUN MODE: No changes will be made to Elasticsearch")
        print("\n   To apply these changes, run without --dry-run flag:")
        print(f"   python update_topic_labels.py")
        
    else:
        print("\n" + "=" * 80)
        print("💾 UPDATING ELASTICSEARCH")
        print("=" * 80)
        
        # Confirm with user
        print("\n⚠️  This will update topic_label for all documents in Elasticsearch.")
        response = input("\nProceed with update? [y/N]: ")
        
        if response.lower() not in ['y', 'yes']:
            print("\n❌ Update cancelled by user")
            sys.exit(0)
        
        try:
            updated_count = update_elasticsearch_topic_labels(
                es, 
                topic_mapping, 
                args.index
            )
            
            print("\n" + "=" * 80)
            print("✅ UPDATE COMPLETE!")
            print("=" * 80)
            print(f"📊 Total documents updated: {updated_count:,}")
            print(f"📊 Topics processed: {len(topic_mapping)}")
            print("\n✨ Your API will now serve readable topic names!")
            print("=" * 80)
            
        except Exception as e:
            print(f"\n❌ Error updating Elasticsearch: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)


if __name__ == "__main__":
    main()
