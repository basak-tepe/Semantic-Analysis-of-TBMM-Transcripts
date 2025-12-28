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
from typing import List, Dict, Tuple, Optional
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
TOPIC_DETAILS_FILE = "../data/data_secret/topic_details.csv"
BATCH_SIZE = 1000  # Batch size for scroll API

# LLM Configuration
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL")
USE_LLM_NAMING = os.getenv("USE_LLM_NAMING", "true").lower() == "true"


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
            print(f"Batch {batch_count}: Processing {len(hits)} speeches...")
            
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
        calculate_probabilities=False, # Calculate topic probabilities
        min_topic_size=3,
    )
    
    # Fit and transform
    topics, _ = topic_model.fit_transform(contents)
    
    # Save model for future use
    topic_model.save(MODEL_SAVE_PATH)
    print(f"✅ Model trained and saved to {MODEL_SAVE_PATH}")
    
    # Print topic statistics
    topic_info = topic_model.get_topic_info()
    num_topics = len(topic_info[topic_info['Topic'] != -1])
    outlier_count = (topics == -1).sum()
    print(f"📊 Discovered {num_topics} topics (excluding outliers)")
    print(f"📊 Outliers: {outlier_count} speeches")
    
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
    exclude_outliers: bool = True,
    groq_topic_mapping: Optional[Dict[int, str]] = None
) -> pd.DataFrame:
    """
    Create and export topic summary CSV for backup/analysis.
    
    Args:
        speeches: List of speech dictionaries
        topics: List of topic IDs
        topic_model: Trained BERTopic model
        exclude_outliers: If True, exclude topic_id -1 (outliers) from the summary
        groq_topic_mapping: Optional dictionary mapping topic_id to Groq-generated readable names
        
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
    
    # Add Groq-generated topic names if available
    if groq_topic_mapping:
        df['groq_topic_label'] = df['topic_id'].map(groq_topic_mapping)
        print(f"   Added Groq-generated topic names for {df['groq_topic_label'].notna().sum():,} speeches")
    
    # Create summary by MP and topic
    groupby_cols = ['speech_giver', 'topic_id', 'topic_label']
    if groq_topic_mapping:
        groupby_cols.append('groq_topic_label')
    
    summary = df.groupby(groupby_cols).agg({
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


def save_topic_details(topic_model: BERTopic, output_file: str = TOPIC_DETAILS_FILE):
    """
    Save detailed topic information to CSV including keywords and representative docs.
    
    This file is used by the LLM to generate human-readable topic names.
    
    Args:
        topic_model: Trained BERTopic model
        output_file: Path to save topic details CSV
    """
    print(f"\n📊 Saving topic details for LLM processing...")
    
    try:
        # Get topic info
        topic_info = topic_model.get_topic_info()
        
        # Add detailed keywords and representative docs
        detailed_keywords = []
        representative_docs_list = []
        
        for topic_id in topic_info['Topic']:
            if topic_id == -1:
                detailed_keywords.append("Outliers")
                representative_docs_list.append("[]")
            else:
                # Get top 10 words
                words = topic_model.get_topic(topic_id)
                keywords = ', '.join([word for word, _ in words[:10]])
                detailed_keywords.append(keywords)
                
                # Get representative documents
                try:
                    rep_docs = topic_model.get_representative_docs(topic_id)
                    # Store as string representation of list
                    representative_docs_list.append(str(rep_docs))
                except:
                    representative_docs_list.append("[]")
        
        topic_info['Keywords'] = detailed_keywords
        topic_info['Representative_Docs'] = representative_docs_list
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
        # Save to CSV
        topic_info.to_csv(output_file, index=False, encoding='utf-8')
        print(f"✅ Topic details saved to {output_file}")
        print(f"   Total topics: {len(topic_info)} (including outliers)")
        
    except Exception as e:
        print(f"⚠️  Error saving topic details: {e}")


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
    
    # Step 5: Save detailed topic information for LLM
    save_topic_details(topic_model, TOPIC_DETAILS_FILE)
    
    # Step 6: Generate readable topic names with LLM (optional)
    topic_mapping = None  # Initialize to None
    if USE_LLM_NAMING and GROQ_API_KEY:
        try:
            print("\n" + "=" * 80)
            print("🤖 LLM TOPIC NAME GENERATION")
            print("=" * 80)
            
            from llm_topic_namer import process_all_topics, update_elasticsearch_topic_labels
            
            # Generate readable names
            topic_mapping = process_all_topics(TOPIC_DETAILS_FILE, api_key=GROQ_API_KEY)
            
            if topic_mapping:
                # Update Elasticsearch with readable names
                updated_count = update_elasticsearch_topic_labels(es, topic_mapping, ELASTICSEARCH_INDEX)
                
                print("\n✅ LLM naming complete!")
                print(f"📊 Generated names for {len(topic_mapping)} topics")
                print(f"📊 Updated {updated_count:,} documents in Elasticsearch")
            else:
                print("⚠️  No topic mappings generated, skipping ES update")
                topic_mapping = None  # Ensure it's None if empty
                
        except ImportError as e:
            print(f"⚠️  Could not import llm_topic_namer: {e}")
            print("   Install groq package: pip install groq")
            topic_mapping = None
        except Exception as e:
            print(f"⚠️  LLM naming failed: {e}")
            print("   Continuing with keyword-based labels")
            topic_mapping = None
    elif not GROQ_API_KEY:
        print("\n⚠️  Skipping LLM naming: GROQ_API_KEY not set")
        print("   Set environment variable GROQ_API_KEY to enable")
    else:
        print("\n⚠️  Skipping LLM naming: USE_LLM_NAMING=false")
    
    # Step 7: Export summary to CSV (backup) - after LLM naming if enabled
    summary = export_topic_summary(speeches, topics, topic_model, groq_topic_mapping=topic_mapping)
    
    # Step 8: Show top topics
    visualize_top_topics(topic_model, n_topics=10)
    
    print("\n" + "=" * 80)
    print("✅ TOPIC ANALYSIS COMPLETE!")
    print("=" * 80)
    print(f"📊 Total speeches analyzed: {len(speeches):,}")
    print(f"📊 Documents updated in ES: {success:,}")
    print(f"📊 Model saved to: {MODEL_SAVE_PATH}")
    print(f"📊 Topic details saved to: {TOPIC_DETAILS_FILE}")
    print(f"📊 Summary saved to: {TOPIC_SUMMARY_FILE}")
    if USE_LLM_NAMING and GROQ_API_KEY:
        print(f"🤖 LLM-generated names: Enabled")
    print("=" * 80)


if __name__ == "__main__":
    main()
