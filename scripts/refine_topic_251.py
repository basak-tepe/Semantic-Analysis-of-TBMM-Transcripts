"""
Refine Topic 251 - Filter Common Words & Redistribute Speeches

This script refines the large topic 251 cluster by:
1. Filtering common parliamentary words (Meclis, TBMM, party names, MP names) from keywords
2. Re-embedding filtered keywords
3. Redistributing speeches to other topics based on similarity
4. Re-clustering remaining speeches with filtered keywords
5. Updating Elasticsearch and embeddings file

Usage:
    python scripts/refine_topic_251.py [--embeddings data/keyword_embeddings.npy] [--topic-id 251]
"""

import os
import sys
import argparse
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional
from collections import Counter
from sklearn.metrics.pairwise import cosine_similarity
import umap
import hdbscan
from sentence_transformers import SentenceTransformer
from elasticsearch import Elasticsearch, helpers
from tqdm.auto import tqdm

# Configuration
DEFAULT_ES_HOST = os.getenv("ELASTICSEARCH_HOST", "http://localhost:9200")
DEFAULT_INDEX = os.getenv("ELASTICSEARCH_INDEX", "parliament_speeches")
DEFAULT_EMBEDDINGS_PATH = "data/keyword_embeddings.npy"
MODEL_NAME = "trmteb/turkish-embedding-model-fine-tuned"
TARGET_TOPIC_ID = 251

# UMAP parameters (matching original approach)
UMAP_N_COMPONENTS = 50
UMAP_N_NEIGHBORS = 5
UMAP_MIN_DIST = 0.0
UMAP_METRIC = 'cosine'
UMAP_RANDOM_STATE = 42

# HDBSCAN parameters (matching original approach)
HDBSCAN_MIN_CLUSTER_SIZE = 10
HDBSCAN_MIN_SAMPLES = 5
HDBSCAN_METRIC = 'euclidean'
HDBSCAN_EPSILON = 5.0

# Redistribution thresholds
SIMILARITY_THRESHOLD = 0.1  # How much better another topic must be to reassign
CORE_THRESHOLD = 0.7  # Minimum similarity to topic 251 to keep it


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
        sys.exit(1)


def load_data_from_elasticsearch(es: Elasticsearch, index: str, embeddings_path: str) -> Tuple[Dict, np.ndarray, Dict]:
    """
    Load speech data from ES and match with embeddings file.
    
    Returns:
        speeches_dict: {speech_id: {keywords, hdbscan_topic_id, embedding_index}}
        embeddings: numpy array of embeddings
        speech_id_to_index: mapping from speech_id to embedding index
    """
    print(f"\n📥 Loading data from Elasticsearch...")
    
    # Load embeddings
    if not os.path.exists(embeddings_path):
        print(f"❌ Embeddings file not found: {embeddings_path}")
        sys.exit(1)
    
    embeddings = np.load(embeddings_path)
    print(f"✅ Loaded embeddings: {embeddings.shape}")
    
    # Query all speeches with keywords and topic_id
    speeches_dict = {}
    speech_id_to_index = {}
    
    query = {
        "query": {
            "exists": {"field": "keywords"}
        },
        "_source": ["keywords", "keywords_str", "hdbscan_topic_id"],
        "size": 10000
    }
    
    index_counter = 0
    for hit in helpers.scan(es, query=query, index=index, scroll='5m'):
        speech_id = hit['_id']
        source = hit.get('_source', {})
        
        # Get keywords (prefer keywords_str, fallback to keywords array)
        keywords = source.get('keywords_str')
        if not keywords and source.get('keywords'):
            keywords = ', '.join(source['keywords']) if isinstance(source['keywords'], list) else str(source['keywords'])
        
        hdbscan_topic_id = source.get('hdbscan_topic_id')
        
        speeches_dict[speech_id] = {
            'keywords': keywords,
            'hdbscan_topic_id': hdbscan_topic_id,
            'embedding_index': index_counter
        }
        speech_id_to_index[speech_id] = index_counter
        index_counter += 1
    
    print(f"✅ Loaded {len(speeches_dict):,} speeches from Elasticsearch")
    print(f"   Embeddings shape: {embeddings.shape}")
    print(f"   Expected speeches: {embeddings.shape[0]:,}")
    
    if len(speeches_dict) != embeddings.shape[0]:
        print(f"⚠️  Warning: Number of speeches ({len(speeches_dict)}) doesn't match embeddings ({embeddings.shape[0]})")
        print(f"   This may cause issues. Ensure embeddings match ES document order.")
    
    return speeches_dict, embeddings, speech_id_to_index


def get_common_parliamentary_words(es: Elasticsearch, index: str) -> Set[str]:
    """Extract common words: party names, institution names, frequent MP names."""
    print(f"\n🔍 Extracting common parliamentary words...")
    
    common_words = set()
    
    # Institution names
    institution_names = {
        "Meclis", "TBMM", "parlamento", "Meclis Başkanı", "Başkan", 
        "Milletvekili", "Komisyon", "Bakan", "Bakanlık", "Genel Kurul"
    }
    common_words.update(institution_names)
    
    # Extract party names from aggregations
    try:
        query = {
            "size": 0,
            "aggs": {
                "parties": {
                    "terms": {
                        "field": "political_party_at_time.keyword",
                        "size": 50
                    }
                }
            }
        }
        response = es.search(index=index, body=query)
        parties = [bucket['key'] for bucket in response['aggregations']['parties']['buckets']]
        # Clean party names (remove term prefixes if any)
        for party in parties:
            # Remove patterns like "XX.dönem " prefix
            cleaned = party.split('.dönem ')[-1] if '.dönem ' in party else party
            common_words.add(cleaned)
        print(f"   Found {len(parties)} party names")
    except Exception as e:
        print(f"   ⚠️  Could not extract party names: {e}")
    
    # Extract frequent MP names
    try:
        query = {
            "size": 0,
            "aggs": {
                "speakers": {
                    "terms": {
                        "field": "speech_giver.keyword",
                        "size": 100
                    }
                }
            }
        }
        response = es.search(index=index, body=query)
        mp_names = [bucket['key'] for bucket in response['aggregations']['speakers']['buckets']]
        common_words.update(mp_names)
        print(f"   Found {len(mp_names)} frequent MP names")
    except Exception as e:
        print(f"   ⚠️  Could not extract MP names: {e}")
    
    print(f"✅ Total common words: {len(common_words)}")
    return common_words


def filter_keywords(keywords_str: str, common_words: Set[str]) -> str:
    """Remove common words from comma-separated keyword string."""
    if not keywords_str:
        return ""
    
    # Split keywords
    keywords = [k.strip() for k in str(keywords_str).split(',')]
    
    # Filter out common words (case-insensitive)
    filtered = []
    for kw in keywords:
        kw_lower = kw.lower().strip()
        # Check if keyword contains any common word
        is_common = False
        for common in common_words:
            if common.lower() in kw_lower or kw_lower in common.lower():
                is_common = True
                break
        
        if not is_common and kw.strip():
            filtered.append(kw.strip())
    
    return ', '.join(filtered) if filtered else keywords_str  # Return original if all filtered


def apply_umap_reduction(
    all_embeddings: np.ndarray,
    n_components: int = UMAP_N_COMPONENTS,
    n_neighbors: int = UMAP_N_NEIGHBORS,
    min_dist: float = UMAP_MIN_DIST,
    metric: str = UMAP_METRIC,
    random_state: int = UMAP_RANDOM_STATE
) -> Tuple[np.ndarray, umap.UMAP]:
    """Apply UMAP dimensionality reduction (768 → 50 dims)."""
    print(f"\n🔄 Applying UMAP reduction: {all_embeddings.shape[1]} → {n_components} dims...")
    
    reducer = umap.UMAP(
        n_components=n_components,
        n_neighbors=n_neighbors,
        min_dist=min_dist,
        metric=metric,
        random_state=random_state
    )
    
    reduced_embeddings = reducer.fit_transform(all_embeddings)
    
    print(f"✅ UMAP reduction complete: {reduced_embeddings.shape}")
    return reduced_embeddings, reducer


def calculate_topic_centroids(
    speeches_dict: Dict,
    speech_id_to_index: Dict,
    reduced_embeddings: np.ndarray,
    exclude_topic_id: int = TARGET_TOPIC_ID
) -> Dict[int, np.ndarray]:
    """Calculate centroid embeddings for each topic using reduced embeddings."""
    print(f"\n📊 Calculating topic centroids...")
    
    topic_embeddings = {}
    
    # Group speeches by topic
    for speech_id, speech_data in speeches_dict.items():
        topic_id = speech_data.get('hdbscan_topic_id')
        if topic_id is None or topic_id == exclude_topic_id:
            continue
        
        embedding_idx = speech_data.get('embedding_index')
        if embedding_idx is None or embedding_idx >= len(reduced_embeddings):
            continue
        
        if topic_id not in topic_embeddings:
            topic_embeddings[topic_id] = []
        topic_embeddings[topic_id].append(reduced_embeddings[embedding_idx])
    
    # Calculate centroids
    centroids = {}
    for topic_id, embeddings_list in topic_embeddings.items():
        if embeddings_list:
            centroids[topic_id] = np.mean(embeddings_list, axis=0)
    
    print(f"✅ Calculated centroids for {len(centroids)} topics")
    return centroids


def redistribute_speeches(
    topic_251_speech_ids: List[str],
    speeches_dict: Dict,
    speech_id_to_index: Dict,
    original_reduced_embeddings: np.ndarray,
    filtered_reduced_embeddings: np.ndarray,
    topic_centroids: Dict[int, np.ndarray],
    topic_251_centroid: np.ndarray,
    threshold: float = SIMILARITY_THRESHOLD,
    core_threshold: float = CORE_THRESHOLD
) -> Tuple[Dict[str, int], List[str]]:
    """
    Find best matching topic for each speech.
    
    Returns:
        Tuple of (redistributions_dict, to_recluster_list)
        redistributions_dict: {speech_id: new_topic_id} mapping
        to_recluster_list: List of speech_ids that need re-clustering
    """
    print(f"\n🔄 Redistributing {len(topic_251_speech_ids):,} speeches...")
    
    redistributions = {}
    kept_in_251 = 0
    reassigned = 0
    to_recluster = []
    
    for speech_id in tqdm(topic_251_speech_ids, desc="Redistributing"):
        speech_data = speeches_dict[speech_id]
        embedding_idx = speech_data.get('embedding_index')
        
        if embedding_idx is None or embedding_idx >= len(filtered_reduced_embeddings):
            continue
        
        # Get filtered embedding for this speech
        filtered_emb = filtered_reduced_embeddings[embedding_idx].reshape(1, -1)
        original_emb = original_reduced_embeddings[embedding_idx].reshape(1, -1)
        
        # Calculate similarity to topic 251 (using original embedding)
        topic_251_sim = cosine_similarity(original_emb, topic_251_centroid.reshape(1, -1))[0][0]
        
        # Calculate similarity to all other topics (using filtered embedding)
        best_topic = None
        best_sim = -1
        
        for topic_id, centroid in topic_centroids.items():
            sim = cosine_similarity(filtered_emb, centroid.reshape(1, -1))[0][0]
            if sim > best_sim:
                best_sim = sim
                best_topic = topic_id
        
        # Decision logic
        if best_topic and best_sim > topic_251_sim + threshold:
            # Reassign to better topic
            redistributions[speech_id] = best_topic
            reassigned += 1
        elif topic_251_sim >= core_threshold:
            # Keep in topic 251 (core speech)
            redistributions[speech_id] = TARGET_TOPIC_ID
            kept_in_251 += 1
        else:
            # Mark for re-clustering
            to_recluster.append(speech_id)
    
    print(f"✅ Redistribution complete:")
    print(f"   Kept in topic {TARGET_TOPIC_ID}: {kept_in_251:,}")
    print(f"   Reassigned to other topics: {reassigned:,}")
    print(f"   To be re-clustered: {len(to_recluster):,}")
    
    return redistributions, to_recluster


def re_cluster_remaining(
    to_recluster: List[str],
    speeches_dict: Dict,
    speech_id_to_index: Dict,
    filtered_reduced_embeddings: np.ndarray,
    min_cluster_size: int = HDBSCAN_MIN_CLUSTER_SIZE,
    min_samples: int = HDBSCAN_MIN_SAMPLES,
    metric: str = HDBSCAN_METRIC,
    cluster_selection_epsilon: float = HDBSCAN_EPSILON,
    start_topic_id: int = None
) -> Dict[str, int]:
    """Re-cluster speeches that weren't redistributed using HDBSCAN."""
    if not to_recluster:
        return {}
    
    print(f"\n🔄 Re-clustering {len(to_recluster):,} speeches...")
    
    # Get embeddings for speeches to re-cluster
    embeddings_to_cluster = []
    speech_id_mapping = []  # Map cluster index back to speech_id
    
    for speech_id in to_recluster:
        speech_data = speeches_dict[speech_id]
        embedding_idx = speech_data.get('embedding_index')
        
        if embedding_idx is not None and embedding_idx < len(filtered_reduced_embeddings):
            embeddings_to_cluster.append(filtered_reduced_embeddings[embedding_idx])
            speech_id_mapping.append(speech_id)
    
    if not embeddings_to_cluster:
        return {}
    
    embeddings_array = np.array(embeddings_to_cluster)
    
    # Run HDBSCAN
    clusterer = hdbscan.HDBSCAN(
        min_cluster_size=min_cluster_size,
        min_samples=min_samples,
        metric=metric,
        cluster_selection_epsilon=cluster_selection_epsilon,
        prediction_data=True
    )
    
    cluster_labels = clusterer.fit_predict(embeddings_array)
    
    # Map cluster labels to new topic IDs
    if start_topic_id is None:
        # Find max existing topic ID
        max_topic_id = max([s.get('hdbscan_topic_id', 0) for s in speeches_dict.values() if s.get('hdbscan_topic_id')])
        start_topic_id = max_topic_id + 1
    
    # Create mapping: cluster_label -> new_topic_id
    unique_clusters = sorted(set(cluster_labels))
    cluster_to_topic = {}
    next_topic_id = start_topic_id
    
    for cluster_label in unique_clusters:
        if cluster_label == -1:
            # Outliers - assign to a special topic or keep as -1
            cluster_to_topic[cluster_label] = -1
        else:
            cluster_to_topic[cluster_label] = next_topic_id
            next_topic_id += 1
    
    # Create result mapping
    result = {}
    for idx, cluster_label in enumerate(cluster_labels):
        speech_id = speech_id_mapping[idx]
        new_topic_id = cluster_to_topic[cluster_label]
        result[speech_id] = new_topic_id
    
    n_clusters = len([c for c in unique_clusters if c != -1])
    n_outliers = sum(1 for c in cluster_labels if c == -1)
    
    print(f"✅ Re-clustering complete:")
    print(f"   Created {n_clusters} new topics (IDs: {start_topic_id} to {next_topic_id - 1})")
    print(f"   Outliers: {n_outliers}")
    
    return result


def generate_topic_labels(
    speeches_dict: Dict,
    topic_assignments: Dict[str, int],
    n_keywords: int = 5
) -> Dict[int, str]:
    """Generate topic labels from top keywords."""
    print(f"\n🏷️  Generating topic labels...")
    
    # Group speeches by topic
    topic_speeches = {}
    for speech_id, topic_id in topic_assignments.items():
        if topic_id not in topic_speeches:
            topic_speeches[topic_id] = []
        topic_speeches[topic_id].append(speeches_dict[speech_id].get('keywords', ''))
    
    topic_labels = {}
    
    for topic_id, keywords_list in topic_speeches.items():
        # Extract all keywords
        all_keywords = []
        for keywords_str in keywords_list:
            if keywords_str:
                keywords = [k.strip() for k in str(keywords_str).split(',')]
                all_keywords.extend([k for k in keywords if k.strip()])
        
        # Count keyword frequencies
        keyword_counts = Counter(all_keywords)
        
        # Get top N keywords
        top_keywords = [kw for kw, count in keyword_counts.most_common(n_keywords)]
        
        # Create label
        if topic_id == -1:
            topic_labels[topic_id] = "Outliers"
        elif top_keywords:
            topic_labels[topic_id] = ", ".join(top_keywords)
        else:
            topic_labels[topic_id] = f"Topic {topic_id}"
    
    print(f"✅ Generated labels for {len(topic_labels)} topics")
    return topic_labels


def update_elasticsearch(
    es: Elasticsearch,
    index: str,
    redistributions: Dict[str, int],
    recluster_assignments: Dict[str, int],
    topic_labels: Dict[int, str]
):
    """Bulk update Elasticsearch with new topic assignments."""
    print(f"\n💾 Updating Elasticsearch...")
    
    # Combine all assignments
    all_assignments = {**redistributions, **recluster_assignments}
    
    if not all_assignments:
        print("   No assignments to update")
        return
    
    # Prepare bulk update actions
    actions = []
    for speech_id, new_topic_id in all_assignments.items():
        new_label = topic_labels.get(new_topic_id, f"Topic {new_topic_id}")
        
        actions.append({
            '_op_type': 'update',
            '_index': index,
            '_id': speech_id,
            'doc': {
                'hdbscan_topic_id': int(new_topic_id),
                'hdbscan_topic_label': new_label
            }
        })
    
    # Bulk update
    success_count = 0
    error_count = 0
    
    for i in tqdm(range(0, len(actions), 500), desc="Updating ES"):
        batch = actions[i:i+500]
        try:
            success, errors = helpers.bulk(es, batch, raise_on_error=False)
            success_count += success
            if errors:
                error_count += len(errors)
        except Exception as e:
            print(f"   ⚠️  Error in batch {i}: {e}")
            error_count += len(batch)
    
    print(f"✅ Elasticsearch update complete:")
    print(f"   Successfully updated: {success_count:,}")
    if error_count > 0:
        print(f"   Errors: {error_count:,}")


def update_embeddings_file(
    embeddings_path: str,
    topic_251_indices: List[int],
    filtered_embeddings: np.ndarray,
    backup: bool = True
):
    """Update embeddings file with filtered embeddings for topic 251 speeches."""
    print(f"\n💾 Updating embeddings file...")
    
    # Load original embeddings
    original_embeddings = np.load(embeddings_path)
    
    # Backup if requested
    if backup:
        backup_path = embeddings_path.replace('.npy', '_backup.npy')
        print(f"   Creating backup: {backup_path}")
        np.save(backup_path, original_embeddings)
    
    # Replace embeddings for topic 251 speeches
    updated_embeddings = original_embeddings.copy()
    
    for idx, emb_idx in enumerate(topic_251_indices):
        if emb_idx < len(updated_embeddings) and idx < len(filtered_embeddings):
            updated_embeddings[emb_idx] = filtered_embeddings[idx]
    
    # Save updated file
    np.save(embeddings_path, updated_embeddings)
    print(f"✅ Updated embeddings file: {embeddings_path}")


def upload_to_google_drive(file_path: str, drive_folder_id: str = None):
    """Upload embeddings file to Google Drive."""
    print(f"\n☁️  Uploading to Google Drive...")
    
    try:
        from google.colab import drive
        import shutil
        
        # Mount drive if not already mounted
        try:
            drive.mount('/content/drive', force_remount=False)
        except:
            pass  # Already mounted
        
        # Determine destination path
        if drive_folder_id:
            dest_path = f"/content/drive/MyDrive/{drive_folder_id}/{Path(file_path).name}"
        else:
            dest_path = f"/content/drive/MyDrive/{Path(file_path).name}"
        
        # Copy file
        shutil.copy(file_path, dest_path)
        print(f"✅ Uploaded to: {dest_path}")
        
    except ImportError:
        print("⚠️  Google Drive API not available (not running in Colab)")
        print(f"   Please manually upload {file_path} to Google Drive")
    except Exception as e:
        print(f"⚠️  Error uploading to Google Drive: {e}")
        print(f"   Please manually upload {file_path} to Google Drive")


def main():
    """Main execution function."""
    parser = argparse.ArgumentParser(
        description="Refine topic 251 by filtering common words and redistributing speeches"
    )
    parser.add_argument(
        '--embeddings',
        default=DEFAULT_EMBEDDINGS_PATH,
        help=f"Path to embeddings .npy file (default: {DEFAULT_EMBEDDINGS_PATH})"
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
        '--topic-id',
        type=int,
        default=TARGET_TOPIC_ID,
        help=f"Target topic ID to refine (default: {TARGET_TOPIC_ID})"
    )
    parser.add_argument(
        '--no-backup',
        action='store_true',
        help="Don't create backup of embeddings file"
    )
    parser.add_argument(
        '--no-drive-upload',
        action='store_true',
        help="Don't upload to Google Drive"
    )
    
    args = parser.parse_args()
    
    # Connect to Elasticsearch
    es = connect_elasticsearch(args.host)
    
    # Load data
    speeches_dict, embeddings, speech_id_to_index = load_data_from_elasticsearch(
        es, args.index, args.embeddings
    )
    
    # Extract topic 251 speeches
    topic_251_speech_ids = [
        sid for sid, data in speeches_dict.items()
        if data.get('hdbscan_topic_id') == args.topic_id
    ]
    
    print(f"\n📊 Found {len(topic_251_speech_ids):,} speeches in topic {args.topic_id}")
    
    if not topic_251_speech_ids:
        print(f"⚠️  No speeches found in topic {args.topic_id}")
        sys.exit(0)
    
    # Get common words
    common_words = get_common_parliamentary_words(es, args.index)
    
    # Filter keywords for topic 251 speeches
    print(f"\n🔍 Filtering keywords for topic {args.topic_id} speeches...")
    filtered_keywords_list = []
    topic_251_indices = []
    
    for speech_id in topic_251_speech_ids:
        speech_data = speeches_dict[speech_id]
        original_keywords = speech_data.get('keywords', '')
        filtered_keywords = filter_keywords(original_keywords, common_words)
        filtered_keywords_list.append(filtered_keywords)
        topic_251_indices.append(speech_data.get('embedding_index'))
    
    print(f"✅ Filtered keywords for {len(filtered_keywords_list):,} speeches")
    
    # Re-embed filtered keywords
    print(f"\n🔄 Re-embedding filtered keywords...")
    model = SentenceTransformer(MODEL_NAME)
    filtered_embeddings_768 = model.encode(
        filtered_keywords_list,
        batch_size=32,
        show_progress_bar=True,
        convert_to_numpy=True
    )
    print(f"✅ Generated {filtered_embeddings_768.shape[0]} filtered embeddings")
    
    # Apply UMAP reduction on original embeddings (fit once on all data)
    print(f"\n🔄 Fitting UMAP on all original embeddings...")
    original_reduced_embeddings, reducer = apply_umap_reduction(embeddings)
    
    # Transform filtered embeddings using the same reducer
    print(f"\n🔄 Transforming filtered embeddings...")
    filtered_reduced_embeddings_all = reducer.transform(filtered_embeddings_768)
    
    # Create combined reduced embeddings (original + filtered for topic 251)
    reduced_embeddings = original_reduced_embeddings.copy()
    for idx, emb_idx in enumerate(topic_251_indices):
        if emb_idx < len(reduced_embeddings):
            reduced_embeddings[emb_idx] = filtered_reduced_embeddings_all[idx]
    
    # Calculate topic centroids
    topic_centroids = calculate_topic_centroids(
        speeches_dict, speech_id_to_index, original_reduced_embeddings, exclude_topic_id=args.topic_id
    )
    
    # Calculate topic 251 centroid (using original embeddings)
    topic_251_indices_list = [speeches_dict[sid].get('embedding_index') for sid in topic_251_speech_ids]
    topic_251_original_embs = original_reduced_embeddings[topic_251_indices_list]
    topic_251_centroid = np.mean(topic_251_original_embs, axis=0)
    
    # Redistribute speeches
    redistributions, to_recluster = redistribute_speeches(
        topic_251_speech_ids,
        speeches_dict,
        speech_id_to_index,
        original_reduced_embeddings,
        reduced_embeddings,  # Use combined reduced embeddings
        topic_centroids,
        topic_251_centroid
    )
    
    # Re-cluster remaining speeches
    recluster_assignments = {}
    if to_recluster:
        recluster_assignments = re_cluster_remaining(
            to_recluster,
            speeches_dict,
            speech_id_to_index,
            reduced_embeddings  # Use combined reduced embeddings
        )
    
    # Generate topic labels for new/reassigned topics
    all_assignments = {**redistributions, **recluster_assignments}
    new_topic_ids = set(all_assignments.values())
    
    # Get keywords for new topics
    topic_keywords_map = {}
    for speech_id, topic_id in all_assignments.items():
        if topic_id not in topic_keywords_map:
            topic_keywords_map[topic_id] = []
        topic_keywords_map[topic_id].append(speeches_dict[speech_id].get('keywords', ''))
    
    topic_labels = generate_topic_labels(speeches_dict, all_assignments)
    
    # Update Elasticsearch
    update_elasticsearch(es, args.index, redistributions, recluster_assignments, topic_labels)
    
    # Update embeddings file
    update_embeddings_file(
        args.embeddings,
        topic_251_indices,
        filtered_embeddings_768,
        backup=not args.no_backup
    )
    
    # Upload to Google Drive
    if not args.no_drive_upload:
        upload_to_google_drive(args.embeddings)
    
    print(f"\n✅ Refinement complete!")


if __name__ == "__main__":
    main()
