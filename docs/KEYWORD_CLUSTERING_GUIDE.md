# Keyword Clustering with HDBSCAN Guide

## Overview

This guide explains how to use the keyword embedding and HDBSCAN clustering system to create topic assignments based on speech keywords.

## Prerequisites

1. **Keywords extracted**: You should have `data/speech_keywords.csv` with extracted keywords
2. **Dependencies installed**: Run `pip install -r requirements.txt`
3. **Elasticsearch running**: Local instance at http://localhost:9200 (for uploading results)

## Quick Start

### Option 1: Use the Jupyter Notebook (Recommended)

1. **Open the notebook**:
   ```bash
   jupyter notebook src/keyword_clustering_hdbscan.ipynb
   ```

2. **Run all cells** in order:
   - Cell 1-3: Setup and load model
   - Cell 4: Generate embeddings (saved to `data/keyword_embeddings.npy`)
   - Cell 5: Run HDBSCAN clustering
   - Cell 6-9: Analyze and visualize results
   - Cell 10-11: Save results and upload to Elasticsearch
   - Cell 12: View summary

3. **Output files**:
   - `data/keyword_embeddings.npy` - 768-dim embeddings (27,318 × 768)
   - `data/speech_keywords_with_topics.csv` - Keywords + HDBSCAN topics

### Option 2: Test Parameters First

Before running the full clustering, test different HDBSCAN parameters on a sample:

```bash
cd scripts
python test_hdbscan_parameters.py --sample-size 5000
```

This will:
- Test various `min_cluster_size` and `min_samples` combinations
- Show which parameters give best results
- Create visualizations in `data/hdbscan_parameter_test.png`
- Save detailed results to `data/hdbscan_parameter_results.csv`

**Then** use the recommended parameters in the main notebook.

## Understanding HDBSCAN Parameters

### `min_cluster_size`
- **What it does**: Minimum number of speeches required to form a cluster
- **Lower values (30-50)**: More fine-grained topics, more clusters
- **Higher values (100-150)**: Fewer, larger, more general topics
- **Recommended**: Start with 50

### `min_samples`
- **What it does**: Number of neighbors required to form a core point
- **Lower values (5-10)**: More speeches get clustered, fewer outliers
- **Higher values (15-25)**: Stricter clustering, more outliers
- **Recommended**: Start with 15

### `metric`
- **Options**: 'euclidean', 'cosine', 'manhattan'
- **Recommended**: 'euclidean' (works well with sentence embeddings)

## Workflow

```
┌─────────────────────────┐
│ speech_keywords.csv     │
│ (27,318 speeches)       │
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│ Turkish Embedding Model │
│ (768-dimensional)       │
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│ keyword_embeddings.npy  │
│ (27,318 × 768)          │
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│ HDBSCAN Clustering      │
└───────────┬─────────────┘
            │
            ├──────────────────────┐
            ▼                      ▼
┌─────────────────────────┐  ┌──────────────────┐
│ CSV with Topics         │  │ Elasticsearch    │
│ - hdbscan_topic_id      │  │ - New fields     │
│ - hdbscan_topic_label   │  │   added to docs  │
└─────────────────────────┘  └──────────────────┘
```

## Tips for Good Results

1. **Start with default parameters**:
   - `min_cluster_size=50`
   - `min_samples=15`
   - `metric='euclidean'`

2. **Adjust based on results**:
   - Too many outliers? → Decrease `min_cluster_size` or `min_samples`
   - Too many tiny clusters? → Increase `min_cluster_size`
   - Clusters too broad? → Decrease `min_cluster_size`

3. **Use visualizations**:
   - UMAP plot shows cluster separation
   - Cluster size histogram shows distribution
   - Sample speeches show topic coherence

4. **Compare with BERTopic**:
   - You already have BERTopic topics in Elasticsearch
   - HDBSCAN on keywords may find different groupings
   - Use both for complementary insights

## Output Fields in Elasticsearch

After running, each speech will have:
- `keywords` (array) - Extracted keywords
- `keywords_str` (string) - Comma-separated keywords
- `hdbscan_topic_id` (int) - New topic ID from clustering
- `hdbscan_topic_label` (string) - Top 5 keywords representing the topic
- `topic_id` (int) - Original BERTopic ID (preserved)
- `topic_label` (string) - Original BERTopic label (preserved)

## Troubleshooting

### "Model loading takes forever"
- First download is large (~1GB)
- Subsequent runs use cached model
- Consider using a machine with good internet connection

### "Out of memory during embedding"
- Reduce batch_size in `generate_embeddings()` function
- Process in smaller chunks
- Use a machine with more RAM

### "Too many outliers"
- Decrease `min_cluster_size` (e.g., 30 instead of 50)
- Decrease `min_samples` (e.g., 10 instead of 15)
- Consider using `cluster_selection_epsilon` parameter

### "Elasticsearch upload fails"
- Check if Elasticsearch is running: `curl http://localhost:9200`
- Verify index name matches your configuration
- Check if speeches exist in the index

## Advanced Options

### Save Embeddings Without Clustering
If you just want embeddings for other use cases:
```python
# In notebook, after Cell 4:
# Embeddings are saved to keyword_embeddings.npy
# Load them later:
embeddings = np.load('data/keyword_embeddings.npy')
```

### Use Custom Topic Labels
Instead of auto-generated labels from top keywords:
```python
# After clustering, manually create labels:
custom_labels = {
    0: "Economic Policy",
    1: "Education Reform",
    # ... etc
}
df['hdbscan_topic_label'] = df['hdbscan_topic_id'].map(custom_labels)
```

### Hierarchical Topic Analysis
HDBSCAN can detect hierarchy:
```python
# Access cluster hierarchy:
clusterer.condensed_tree_
clusterer.single_linkage_tree_

# Plot dendrogram:
clusterer.condensed_tree_.plot()
```

## Next Steps

After clustering:
1. **Analyze results**: Compare keyword-based topics with BERTopic topics
2. **Validate**: Review sample speeches from each cluster
3. **Refine**: Adjust parameters and re-run if needed
4. **Use topics**: Query Elasticsearch by `hdbscan_topic_id` for analysis
5. **Build visualizations**: Create dashboards showing topic distributions over time

## References

- HDBSCAN documentation: https://hdbscan.readthedocs.io/
- Sentence Transformers: https://www.sbert.net/
- Turkish embedding model: https://huggingface.co/trmteb/turkish-embedding-model-fine-tuned
