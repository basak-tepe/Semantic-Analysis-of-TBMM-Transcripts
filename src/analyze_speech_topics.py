"""
Topic Analysis for Parliament Speeches using BERTopic and Elasticsearch

This script:
1. Connects to Elasticsearch
2. Fetches all speeches using scroll API
3. Runs BERTopic modeling on speech content
4. Updates Elasticsearch documents with topic assignments
5. Optionally exports summary to CSV for backup
"""

import os
import sys
from typing import List, Dict, Tuple
from elasticsearch import Elasticsearch, helpers
from elasticsearch.exceptions import ConnectionError, NotFoundError
from bertopic import BERTopic
import pandas as pd
import plotly.express as px

# Configuration
ELASTICSEARCH_HOST = os.getenv("ELASTICSEARCH_HOST", "http://localhost:9200")
ELASTICSEARCH_INDEX = os.getenv("ELASTICSEARCH_INDEX", "parliament_speeches")
MODEL_SAVE_PATH = "../bertopic_model"
TOPIC_SUMMARY_FILE = "../data/topic_summary.csv"
BATCH_SIZE = 1000  # Batch size for scroll API


def connect_to_elasticsearch() -> Elasticsearch:
    """
    Connect to Elasticsearch and verify connection.
    
    Returns:
        Elasticsearch client instance
        
    Raises:
        Exception if connection fails
    """
    print(f"🔌 Connecting to Elasticsearch at {ELASTICSEARCH_HOST}...")
    
    try:
        es = Elasticsearch(hosts=[ELASTICSEARCH_HOST])
        
        if es.ping():
            # Get index info
            count = es.count(index=ELASTICSEARCH_INDEX)
            total_docs = count.get('count', 0)
            print(f"✅ Connected to Elasticsearch")
            print(f"📊 Index: {ELASTICSEARCH_INDEX}")
            print(f"📊 Total documents: {total_docs:,}")
            return es
        else:
            raise Exception("Ping failed")
            
    except Exception as e:
        print(f"❌ Failed to connect to Elasticsearch: {e}")
        print(f"   Make sure Elasticsearch is running on {ELASTICSEARCH_HOST}")
        sys.exit(1)


def fetch_all_speeches(es: Elasticsearch) -> List[Dict]:
    """
    Fetch all speeches from Elasticsearch using scroll API for efficient retrieval.
    
    The scroll API is used for retrieving large numbers of documents efficiently.
    It maintains a search context and returns batches of results.
    
    Args:
        es: Elasticsearch client instance
        
    Returns:
        List of speech dictionaries with id, content, and metadata
    """
    print(f"\n📥 Fetching speeches from Elasticsearch...")
    
    query = {
        "query": {
            "bool": {
                "must": [
                    {"exists": {"field": "content"}},  # Must have content
                ],
                "must_not": [
                    {"term": {"content": ""}},  # Exclude empty content
                ]
            }
        },
        "size": BATCH_SIZE,
        "_source": [
            "content", "speech_giver", "term", "year", 
            "session_date", "session_id", "speech_no",
            "province", "political_party", "speech_title"
        ]
    }
    
    speeches = []
    scroll_id = None
    batch_count = 0
    
    try:
        # Initial search with scroll
        response = es.search(
            index=ELASTICSEARCH_INDEX,
            body=query,
            scroll='5m'  # Keep scroll context alive for 5 minutes
        )
        
        scroll_id = response['_scroll_id']
        hits = response['hits']['hits']
        
        # Process batches
        while hits:
            batch_count += 1
            print(f"   Batch {batch_count}: Processing {len(hits)} speeches...")
            
            for hit in hits:
                source = hit['_source']
                
                # Only include speeches with non-empty content
                if source.get('content') and source['content'].strip():
                    speeches.append({
                        'id': hit['_id'],
                        'content': source['content'],
                        'speech_giver': source.get('speech_giver', ''),
                        'term': source.get('term'),
                        'year': source.get('year'),
                        'session_date': source.get('session_date'),
                        'session_id': source.get('session_id'),
                        'speech_no': source.get('speech_no'),
                        'province': source.get('province'),
                        'political_party': source.get('political_party'),
                        'speech_title': source.get('speech_title')
                    })
            
            # Get next batch
            response = es.scroll(scroll_id=scroll_id, scroll='5m')
            scroll_id = response['_scroll_id']
            hits = response['hits']['hits']
        
        print(f"✅ Successfully fetched {len(speeches):,} speeches with valid content")
        return speeches
        
    except Exception as e:
        print(f"❌ Error fetching speeches: {e}")
        return []
        
    finally:
        # Always clean up scroll context to free resources
        if scroll_id:
            try:
                es.clear_scroll(scroll_id=scroll_id)
            except:
                pass


def run_topic_modeling(speeches: List[Dict]) -> Tuple[List[int], List[float], BERTopic]:
    """
    Run BERTopic modeling on speech content.
    
    Args:
        speeches: List of speech dictionaries containing 'content' field
        
    Returns:
        Tuple of (topics, topic_model)
        - topics: List of topic IDs assigned to each speech
        - topic_model: Trained BERTopic model
    """
    print(f"\n⚙️  Training BERTopic model on {len(speeches):,} speeches...")
    print("   This may take several minutes depending on your hardware...")
    
    # Extract content
    contents = [speech['content'] for speech in speeches]
    
    # Initialize and train BERTopic
    # Using Turkish language model and automatic topic discovery
    topic_model = BERTopic(
        language="turkish",
        nr_topics=250,  # Automatically determine number of topics
        verbose=True,
        calculate_probabilities=False  # Calculate topic probabilities
        min_topic_size=3,
    )
    
    # Fit and transform
    topics, _ = topic_model.fit_transform(contents)
    
    # Save model for future use
    topic_model.save(MODEL_SAVE_PATH)
    print(f"✅ Model trained and saved to {MODEL_SAVE_PATH}")
    
    # Line 184, replace with:
    #outlier_count = (topics == -1).sum() #TODO: fix the way you count outliers
    #print(f"📊 Outliers: {outlier_count} speeches")
    
    return topics, topic_model


def update_elasticsearch_with_topics(
    es: Elasticsearch, 
    speeches: List[Dict], 
    topics: List[int],
    topic_model: BERTopic
) -> Tuple[int, int]:
    """
    Bulk update Elasticsearch documents with topic assignments.
    
    Args:
        es: Elasticsearch client
        speeches: List of speech dictionaries
        topics: List of topic IDs (same length as speeches)
        topic_model: Trained BERTopic model
        
    Returns:
        Tuple of (success_count, failure_count)
    """
    print(f"\n💾 Updating Elasticsearch with topic assignments...")
    
    # Get topic labels from model
    topic_info = topic_model.get_topic_info()
    topic_labels = {
        int(row['Topic']): row['Name'] 
        for _, row in topic_info.iterrows()
    }
    
    # Prepare bulk update actions
    actions = []
    for speech, topic_id in zip(speeches, topics):
        topic_label = topic_labels.get(topic_id, f"Topic_{topic_id}")
        
        actions.append({
            '_op_type': 'update',
            '_index': ELASTICSEARCH_INDEX,
            '_id': speech['id'],
            'doc': {
                'topic_id': int(topic_id),
                'topic_label': topic_label,
                'topic_analyzed': True
            }
        })
    
    # Bulk update in batches
    print(f"   Updating {len(actions):,} documents...")
    
    try:
        success, errors = helpers.bulk(
            es, 
            actions, 
            raise_on_error=False,
            chunk_size=500
        )
        
        failed_count = len(errors) if errors else 0
        
        print(f"✅ Successfully updated {success:,} documents")
        if failed_count > 0:
            print(f"⚠️  Failed to update {failed_count} documents")
            
        return success, failed_count
        
    except Exception as e:
        print(f"❌ Error during bulk update: {e}")
        return 0, len(actions)


def export_topic_summary(
    speeches: List[Dict],
    topics: List[int],
    topic_model: BERTopic,
    exclude_outliers: bool = True
) -> pd.DataFrame:
    """
    Create and export topic summary CSV for backup/analysis.
    
    Args:
        speeches: List of speech dictionaries
        topics: List of topic IDs
        topic_model: Trained BERTopic model
        exclude_outliers: If True, exclude topic_id -1 (outliers) from the summary
        
    Returns:
        DataFrame with topic summary
    """
    print(f"\n📊 Creating topic summary...")
    
    # Create DataFrame
    df = pd.DataFrame(speeches)
    df['topic_id'] = topics
    
    # Exclude outliers if requested
    if exclude_outliers:
        original_count = len(df)
        df = df[df['topic_id'] != -1].copy()
        excluded_count = original_count - len(df)
        if excluded_count > 0:
            print(f"   Excluding {excluded_count:,} outlier speeches (topic_id -1)")
    
    # Get topic info
    topic_info = topic_model.get_topic_info()
    topic_labels = {
        int(row['Topic']): row['Name'] 
        for _, row in topic_info.iterrows()
    }
    df['topic_label'] = df['topic_id'].map(topic_labels)
    
    # Create summary by MP and topic
    summary = df.groupby(['speech_giver', 'topic_id', 'topic_label']).agg({
        'id': 'count',
        'term': lambda x: list(set(x.dropna())),
        'year': lambda x: list(set(x.dropna()))
    }).reset_index()
    
    summary.rename(columns={'id': 'speech_count'}, inplace=True)
    
    # Sort by speech count
    summary = summary.sort_values('speech_count', ascending=False)
    
    # Save to CSV
    summary.to_csv(TOPIC_SUMMARY_FILE, index=False)
    print(f"✅ Topic summary saved to {TOPIC_SUMMARY_FILE}")
    print(f"   Total rows: {len(summary):,}")
    print(f"   Unique topics: {summary['topic_id'].nunique()}")
    print(f"   Unique MPs: {summary['speech_giver'].nunique()}")
    
    return summary


def visualize_top_topics(topic_model: BERTopic, n_topics: int = 10):
    """
    Visualize the top topics discovered.
    
    Args:
        topic_model: Trained BERTopic model
        n_topics: Number of top topics to show
    """
    print(f"\n📈 Generating topic visualization...")
    
    try:
        # Get topic info
        topic_info = topic_model.get_topic_info()
        
        # Remove outlier topic (-1)
        topic_info = topic_info[topic_info['Topic'] != -1]
        
        # Get top N topics
        top_topics = topic_info.nlargest(n_topics, 'Count')
        
        print(f"\n🏆 Top {n_topics} Topics:")
        print("=" * 80)
        for idx, row in top_topics.iterrows():
            print(f"Topic {row['Topic']}: {row['Name']}")
            print(f"   Count: {row['Count']:,} speeches")
            print()
        
    except Exception as e:
        print(f"⚠️  Could not generate visualization: {e}")


def main():
    """Main execution flow."""
    print("=" * 80)
    print("PARLIAMENT SPEECH TOPIC ANALYSIS")
    print("=" * 80)
    
    # Step 1: Connect to Elasticsearch
    es = connect_to_elasticsearch()
    
    # Step 2: Fetch all speeches
    speeches = fetch_all_speeches(es)
    
    if not speeches:
        print("❌ No speeches found. Exiting.")
        return
    
    # Step 3: Run topic modeling
    topics, topic_model = run_topic_modeling(speeches)
    
    # Step 4: Update Elasticsearch with results
    success, failed = update_elasticsearch_with_topics(
        es, speeches, topics, topic_model
    )
    
    # Step 5: Export summary to CSV (backup)
    summary = export_topic_summary(speeches, topics, topic_model)
    
    # Step 6: Show top topics
    visualize_top_topics(topic_model, n_topics=10)
    
    print("\n" + "=" * 80)
    print("✅ TOPIC ANALYSIS COMPLETE!")
    print("=" * 80)
    print(f"📊 Total speeches analyzed: {len(speeches):,}")
    print(f"📊 Documents updated in ES: {success:,}")
    print(f"📊 Model saved to: {MODEL_SAVE_PATH}")
    print(f"📊 Summary saved to: {TOPIC_SUMMARY_FILE}")
    print("=" * 80)


if __name__ == "__main__":
    main()
