# DBSCAN Implementation for WiDiD

## Overview

`dbscan.ipynb` is an alternative implementation of the WiDiD (Incremental Word Sense Discovery) approach that uses **DBSCAN** (Density-Based Spatial Clustering of Applications with Noise) instead of Affinity Propagation for clustering.

## Key Differences from widid.ipynb

### Clustering Algorithm

| Feature | widid.ipynb (Affinity Propagation) | dbscan.ipynb (DBSCAN) |
|---------|-----------------------------------|----------------------|
| **Cluster Count** | Automatically determined | Determined by density parameters |
| **Parameters** | Preference, damping | eps, min_samples |
| **Noise Handling** | All points assigned to clusters | Explicit noise detection (label -1) |
| **Speed** | Slower for large datasets | Faster, more scalable |
| **Cluster Shape** | Assumes convex clusters | Can find arbitrary shapes |

### DBSCAN Parameters

The notebook uses three key parameters:

1. **`DBSCAN_EPS`** (default: 0.3)
   - Maximum distance between two samples to be considered neighbors
   - **Lower values** → Tighter clusters, more noise
   - **Higher values** → Looser clusters, less noise

2. **`DBSCAN_MIN_SAMPLES`** (default: 3)
   - Minimum number of samples in a neighborhood for a point to be considered a core point
   - **Lower values** → More sensitive, more small clusters
   - **Higher values** → More conservative, larger clusters

3. **`DBSCAN_METRIC`** (default: 'cosine')
   - Distance metric for clustering
   - **'cosine'**: Best for semantic similarity (recommended)
   - **'euclidean'**: Standard Euclidean distance

## Output Structure

The notebook produces the same output structure as `widid.ipynb`:

```
dbscan_results/
├── widid_term{term}_year{year}_{word}.csv    # Cluster assignments per term-year
├── tsne_term{term}_year{year}_{word}.png     # t-SNE visualizations
├── cluster_guide_{word}_summary.csv          # Cluster statistics
├── cluster_guide_{word}_contexts.txt         # Representative contexts
├── cluster_colors_{word}.csv                 # Color mapping
└── color_reference_{word}.png                # Visual color reference
```

## Usage

1. **Configure Elasticsearch connection**:
   ```python
   ES_URL = "http://localhost:9200"
   INDEX_NAME = "parliament_speeches"
   ```

2. **Set target words**:
   ```python
   TARGET_WORDS = ["vergi", "eğitim", "sağlık"]
   ```

3. **Tune DBSCAN parameters** (if needed):
   ```python
   DBSCAN_EPS = 0.3  # Start with 0.3, adjust based on results
   DBSCAN_MIN_SAMPLES = 3  # Start with 3, increase for larger clusters
   ```

4. **Run all cells** to execute the analysis

## Parameter Tuning Guide

### Problem: Too Many Noise Points

**Solution**: Make clustering less strict
- Decrease `min_samples` (e.g., from 3 to 2)
- Increase `eps` (e.g., from 0.3 to 0.4)

### Problem: Too Few Clusters

**Solution**: Make clustering more sensitive
- Decrease `eps` (e.g., from 0.3 to 0.25)
- Decrease `min_samples` (e.g., from 3 to 2)

### Problem: Too Many Small Clusters

**Solution**: Merge clusters more aggressively
- Increase `eps` (e.g., from 0.3 to 0.4)
- Increase `min_samples` (e.g., from 3 to 5)

## When to Use DBSCAN vs Affinity Propagation

### Use DBSCAN when:
- ✅ You have large datasets (faster)
- ✅ You want explicit noise detection
- ✅ Clusters have irregular shapes
- ✅ You can tune parameters based on data exploration

### Use Affinity Propagation when:
- ✅ You want automatic cluster count determination
- ✅ Dataset is small to medium-sized
- ✅ You prefer fewer hyperparameters
- ✅ All data points should belong to clusters

## Example Output

### Console Output

```
--- Term 26, Year 3 ---
  Contexts: 3052
  DBSCAN found: 15 clusters, 234 noise points
  Kept: 15 clusters (cap=50)
  Global clusters represented: 12
```

### CSV Format

The output CSV files have the same structure:

| Column | Description |
|--------|-------------|
| `term` | Parliamentary term |
| `year` | Year within term |
| `context` | Text context window around target word |
| `local_cluster` | Cluster ID within this term-year |
| `global_cluster` | Aligned cluster ID across all term-years |

### Visualization Differences

- **Noise points** are shown as gray 'x' markers
- **Cluster points** are shown with numeric labels and colors
- Title includes "(DBSCAN)" to distinguish from AP results

## Comparison with Original Results

To compare DBSCAN and Affinity Propagation results:

1. Run both notebooks on the same data
2. Compare cluster counts and noise levels
3. Examine cluster quality using the context files
4. Visualize differences in t-SNE plots

## Performance Notes

- **Speed**: DBSCAN is typically 2-3x faster than Affinity Propagation
- **Memory**: Both algorithms have similar memory requirements
- **Scalability**: DBSCAN scales better for large datasets (>10,000 samples)

## References

- Ester, M., et al. (1996). "A density-based algorithm for discovering clusters in large spatial databases with noise." KDD-96.
- scikit-learn DBSCAN documentation: https://scikit-learn.org/stable/modules/generated/sklearn.cluster.DBSCAN.html

