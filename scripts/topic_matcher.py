"""
Topic Matching Module for Incremental Topic Assignment

This module handles matching new speeches to existing topics using cosine similarity
to topic centroids, or creating new clusters for unmatched speeches.
"""
import numpy as np
from typing import Dict, List, Tuple, Optional
from elasticsearch import Elasticsearch
from elasticsearch.helpers import scan, bulk
from sklearn.metrics.pairwise import cosine_similarity
from tqdm import tqdm
import os

# Configuration
ELASTICSEARCH_HOST = os.getenv("ELASTICSEARCH_HOST", "http://localhost:9200")
ELASTICSEARCH_INDEX = os.getenv("ELASTICSEARCH_INDEX", "parliament_speeches")
SIMILARITY_THRESHOLD = 0.7  # Minimum cosine similarity to match to existing topic


def connect_elasticsearch(host: str = None) -> Elasticsearch:
    """Connect to Elasticsearch."""
    if host is None:
        host = ELASTICSEARCH_HOST
    
    es = Elasticsearch(hosts=[host])
    if not es.ping():
        raise Exception(f"Failed to connect to Elasticsearch at {host}")
    return es


def load_existing_topics(
    es: Elasticsearch,
    index_name: str = ELASTICSEARCH_INDEX
) -> Tuple[Dict[int, np.ndarray], Dict[str, int], Dict[int, str]]:
    """
    Load existing topics and their centroids from Elasticsearch.
    
    Args:
        es: Elasticsearch client
        index_name: Index name
        
    Returns:
        Tuple of:
        - topic_centroids: Dict mapping topic_id to centroid embedding
        - speech_to_topic: Dict mapping speech_id to topic_id
        - topic_labels: Dict mapping topic_id to topic_label
    """
    print("\n📥 Loading existing topics from Elasticsearch...")
    
    # Query all speeches with topics and embeddings
    query = {
        "query": {
            "bool": {
                "must": [
                    {"exists": {"field": "hdbscan_topic_id"}},
                    {"exists": {"field": "keywords_str"}}
                ],
                "must_not": [
                    {"term": {"hdbscan_topic_id": -1}},  # Exclude outliers
                    {"term": {"hdbscan_topic_id": 1}}    # Exclude extraction errors
                ]
            }
        },
        "_source": ["hdbscan_topic_id", "hdbscan_topic_label", "keywords_str"]
    }
    
    speeches_by_topic = {}
    speech_to_topic = {}
    topic_labels = {}
    total_speeches = 0
    
    for doc in scan(es, query=query, index=index_name, size=1000):
        speech_id = doc['_id']
        source = doc['_source']
        
        topic_id = source.get('hdbscan_topic_id')
        topic_label = source.get('hdbscan_topic_label', '')
        keywords_str = source.get('keywords_str', '')
        
        if topic_id is None or topic_id == -1 or topic_id == 1:
            continue
        
        if topic_id not in speeches_by_topic:
            speeches_by_topic[topic_id] = []
            topic_labels[topic_id] = topic_label
        
        speeches_by_topic[topic_id].append({
            'speech_id': speech_id,
            'keywords_str': keywords_str
        })
        speech_to_topic[speech_id] = topic_id
        total_speeches += 1
    
    print(f"   Found {len(speeches_by_topic)} existing topics")
    print(f"   Total speeches with topics: {total_speeches:,}")
    
    return speeches_by_topic, speech_to_topic, topic_labels


def load_embeddings_for_speeches(
    embeddings_file: str,
    speech_ids: List[str],
    speech_id_to_index: Optional[Dict[str, int]] = None
) -> Dict[str, np.ndarray]:
    """
    Load embeddings for specific speeches from embeddings file.
    
    Args:
        embeddings_file: Path to .npy file with embeddings
        speech_ids: List of speech IDs to load embeddings for
        speech_id_to_index: Optional mapping from speech_id to row index in embeddings file
        
    Returns:
        Dict mapping speech_id to embedding array
    """
    if not os.path.exists(embeddings_file):
        print(f"⚠️  Embeddings file not found: {embeddings_file}")
        return {}
    
    try:
        embeddings_array = np.load(embeddings_file)
        print(f"📂 Loaded embeddings file: {embeddings_array.shape}")
    except Exception as e:
        print(f"❌ Error loading embeddings: {e}")
        return {}
    
    # If we have a mapping, use it
    if speech_id_to_index:
        embeddings_dict = {}
        for speech_id in speech_ids:
            if speech_id in speech_id_to_index:
                idx = speech_id_to_index[speech_id]
                if idx < len(embeddings_array):
                    embeddings_dict[speech_id] = embeddings_array[idx]
        return embeddings_dict
    
    # Otherwise, we can't map speech_ids to embeddings without additional info
    print("⚠️  No speech_id_to_index mapping provided. Cannot load specific embeddings.")
    return {}


def calculate_topic_centroids(
    speeches_by_topic: Dict[int, List[Dict]],
    embeddings_dict: Dict[str, np.ndarray]
) -> Dict[int, np.ndarray]:
    """
    Calculate centroid embeddings for each topic.
    
    Args:
        speeches_by_topic: Dict mapping topic_id to list of speech dicts
        embeddings_dict: Dict mapping speech_id to embedding array
        
    Returns:
        Dict mapping topic_id to centroid embedding
    """
    print("\n🔄 Calculating topic centroids...")
    
    topic_centroids = {}
    
    for topic_id, speeches in tqdm(speeches_by_topic.items(), desc="Computing centroids"):
        topic_embeddings = []
        
        for speech in speeches:
            speech_id = speech['speech_id']
            if speech_id in embeddings_dict:
                topic_embeddings.append(embeddings_dict[speech_id])
        
        if topic_embeddings:
            # Calculate mean embedding as centroid
            topic_centroids[topic_id] = np.mean(topic_embeddings, axis=0)
    
    print(f"   Calculated centroids for {len(topic_centroids)} topics")
    return topic_centroids


def match_speech_to_topic(
    speech_embedding: np.ndarray,
    topic_centroids: Dict[int, np.ndarray],
    threshold: float = SIMILARITY_THRESHOLD
) -> Optional[Tuple[int, float]]:
    """
    Match a speech embedding to an existing topic using cosine similarity.
    
    Args:
        speech_embedding: Embedding vector for the speech
        topic_centroids: Dict mapping topic_id to centroid embedding
        threshold: Minimum similarity threshold to match
        
    Returns:
        Tuple of (topic_id, similarity_score) if match found, None otherwise
    """
    if not topic_centroids:
        return None
    
    # Calculate cosine similarity to all centroids
    similarities = {}
    for topic_id, centroid in topic_centroids.items():
        # Reshape for cosine_similarity (needs 2D arrays)
        similarity = cosine_similarity(
            speech_embedding.reshape(1, -1),
            centroid.reshape(1, -1)
        )[0][0]
        similarities[topic_id] = similarity
    
    # Find best match
    if similarities:
        best_topic_id = max(similarities, key=similarities.get)
        best_similarity = similarities[best_topic_id]
        
        if best_similarity >= threshold:
            return (best_topic_id, best_similarity)
    
    return None


def get_max_topic_id(
    es: Elasticsearch,
    index_name: str = ELASTICSEARCH_INDEX
) -> int:
    """Get the maximum existing topic ID from Elasticsearch."""
    query = {
        "size": 0,
        "aggs": {
            "max_topic_id": {
                "max": {"field": "hdbscan_topic_id"}
            }
        }
    }
    
    try:
        response = es.search(index=index_name, body=query)
        max_id = response['aggregations']['max_topic_id']['value']
        return int(max_id) if max_id is not None else 0
    except Exception as e:
        print(f"⚠️  Error getting max topic ID: {e}")
        return 0


def create_new_cluster(
    es: Elasticsearch,
    index_name: str = ELASTICSEARCH_INDEX
) -> int:
    """
    Create a new cluster by assigning the next available topic ID.
    
    Args:
        es: Elasticsearch client
        index_name: Index name
        
    Returns:
        New topic ID
    """
    max_id = get_max_topic_id(es, index_name)
    return max_id + 1


def generate_topic_label(
    keywords_str: str,
    topic_id: int
) -> str:
    """
    Generate a topic label from keywords.
    
    Args:
        keywords_str: Comma-separated keywords
        topic_id: Topic ID
        
    Returns:
        Topic label (top 5 keywords)
    """
    if not keywords_str:
        return f"Topic {topic_id}"
    
    keywords = [k.strip() for k in keywords_str.split(',')]
    # Take top 5 keywords
    top_keywords = keywords[:5]
    return ', '.join(top_keywords)


def assign_topics_to_speeches(
    es: Elasticsearch,
    speech_embeddings: Dict[str, np.ndarray],
    topic_centroids: Dict[int, np.ndarray],
    topic_labels: Dict[int, str],
    threshold: float = SIMILARITY_THRESHOLD,
    index_name: str = ELASTICSEARCH_INDEX
) -> Dict[str, Tuple[int, str]]:
    """
    Assign topics to new speeches using cosine similarity matching.
    
    Args:
        es: Elasticsearch client
        speech_embeddings: Dict mapping speech_id to embedding
        topic_centroids: Dict mapping topic_id to centroid embedding
        topic_labels: Dict mapping topic_id to topic_label
        threshold: Similarity threshold for matching
        index_name: Index name
        
    Returns:
        Dict mapping speech_id to (topic_id, topic_label)
    """
    print(f"\n🔄 Assigning topics to {len(speech_embeddings)} speeches...")
    print(f"   Similarity threshold: {threshold}")
    
    assignments = {}
    matched_count = 0
    new_cluster_count = 0
    
    # Get keywords for speeches that need topic assignment
    speech_keywords = {}
    for speech_id in speech_embeddings.keys():
        try:
            doc = es.get(index=index_name, id=speech_id)
            keywords_str = doc['_source'].get('keywords_str', '')
            speech_keywords[speech_id] = keywords_str
        except Exception:
            speech_keywords[speech_id] = ''
    
    for speech_id, embedding in tqdm(speech_embeddings.items(), desc="Matching topics"):
        # Try to match to existing topic
        match_result = match_speech_to_topic(embedding, topic_centroids, threshold)
        
        if match_result:
            topic_id, similarity = match_result
            topic_label = topic_labels.get(topic_id, f"Topic {topic_id}")
            assignments[speech_id] = (topic_id, topic_label)
            matched_count += 1
        else:
            # Create new cluster
            new_topic_id = create_new_cluster(es, index_name)
            keywords_str = speech_keywords.get(speech_id, '')
            topic_label = generate_topic_label(keywords_str, new_topic_id)
            assignments[speech_id] = (new_topic_id, topic_label)
            new_cluster_count += 1
    
    print(f"\n✅ Topic assignment complete!")
    print(f"   Matched to existing topics: {matched_count}")
    print(f"   Created new clusters: {new_cluster_count}")
    
    return assignments


def update_elasticsearch_topics(
    es: Elasticsearch,
    topic_assignments: Dict[str, Tuple[int, str]],
    index_name: str = ELASTICSEARCH_INDEX,
    batch_size: int = 500
) -> Tuple[int, int]:
    """
    Bulk update Elasticsearch with topic assignments.
    
    Args:
        es: Elasticsearch client
        topic_assignments: Dict mapping speech_id to (topic_id, topic_label)
        index_name: Index name
        batch_size: Batch size for bulk updates
        
    Returns:
        Tuple of (success_count, failed_count)
    """
    print(f"\n💾 Updating Elasticsearch with {len(topic_assignments)} topic assignments...")
    
    actions = []
    for speech_id, (topic_id, topic_label) in topic_assignments.items():
        actions.append({
            '_op_type': 'update',
            '_index': index_name,
            '_id': speech_id,
            'doc': {
                'hdbscan_topic_id': topic_id,
                'hdbscan_topic_label': topic_label
            }
        })
    
    success_count = 0
    failed_count = 0
    
    # Process in batches
    for i in range(0, len(actions), batch_size):
        batch = actions[i:i + batch_size]
        try:
            success, failed = bulk(es, batch, stats_only=False, raise_on_error=False)
            success_count += len(batch) - (len(failed) if failed else 0)
            failed_count += len(failed) if failed else 0
            
            if failed:
                print(f"⚠️  Failed to update {len(failed)} documents in batch")
        except Exception as e:
            print(f"❌ Error updating batch: {e}")
            failed_count += len(batch)
    
    print(f"✅ Updated {success_count} documents")
    if failed_count > 0:
        print(f"⚠️  Failed to update {failed_count} documents")
    
    return success_count, failed_count

