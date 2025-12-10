# DBSCAN vs Affinity Propagation Comparison

## Quick Reference

| Aspect | Affinity Propagation (`widid.ipynb`) | DBSCAN (`dbscan.ipynb`) |
|--------|--------------------------------------|-------------------------|
| **Algorithm Type** | Message-passing clustering | Density-based clustering |
| **Cluster Count** | Automatic | Based on density |
| **Main Parameters** | `preference`, `damping` | `eps`, `min_samples` |
| **Handles Noise** | No (assigns all points) | Yes (explicit -1 label) |
| **Cluster Shapes** | Assumes convex | Arbitrary shapes |
| **Speed** | O(N²T) - Slower | O(N log N) - Faster |
| **Scalability** | Poor for >10K samples | Good for large datasets |
| **Deterministic** | No (random initialization) | Yes (with fixed parameters) |

## Detailed Comparison

### 1. Clustering Approach

#### Affinity Propagation
- **How it works**: Passes messages between data points to identify exemplars
- **Cluster definition**: Each cluster has one exemplar, all members are similar to it
- **Advantages**:
  - No need to specify number of clusters
  - Automatically finds representative exemplars
  - Good for finding natural groupings

- **Disadvantages**:
  - Slow convergence, especially on large datasets
  - Sensitive to initialization
  - All points must belong to a cluster (no noise handling)

#### DBSCAN
- **How it works**: Groups together points that are closely packed based on density
- **Cluster definition**: Regions of high density separated by low-density regions
- **Advantages**:
  - Fast and scalable
  - Explicitly handles outliers/noise
  - Can find clusters of arbitrary shape
  - Deterministic results

- **Disadvantages**:
  - Requires parameter tuning (`eps`, `min_samples`)
  - Struggles with varying density clusters
  - Number of clusters depends on parameters

### 2. Parameter Configuration

#### Affinity Propagation Parameters

```python
# widid.ipynb doesn't expose these explicitly
# Uses default parameters
ap = AffinityPropagation(random_state=42)
```

- **preference**: Controls how many clusters to create (not set = median similarity)
- **damping**: Damps message updates (0.5-1.0, default 0.5)
- **max_iter**: Maximum iterations (default 200)

#### DBSCAN Parameters

```python
# dbscan.ipynb - explicitly configurable
DBSCAN_EPS = 0.3  # Distance threshold
DBSCAN_MIN_SAMPLES = 3  # Minimum cluster size
DBSCAN_METRIC = 'cosine'  # Distance metric

dbscan = DBSCAN(
    eps=DBSCAN_EPS,
    min_samples=DBSCAN_MIN_SAMPLES,
    metric=DBSCAN_METRIC
)
```

- **eps**: Maximum distance for neighborhood (most important parameter)
- **min_samples**: Minimum points to form dense region
- **metric**: Distance measure ('cosine' for semantic similarity)

### 3. Output Differences

#### Cluster Labels

**Affinity Propagation**:
- Labels: 0, 1, 2, 3, ... (all non-negative)
- Every point belongs to a cluster
- No explicit noise/outlier detection

**DBSCAN**:
- Labels: -1, 0, 1, 2, 3, ...
- Label -1 indicates noise/outliers
- Core vs border points distinction

#### Example Output

```
Affinity Propagation:
  Raw clusters: 5, kept: 5 (cap=30)
  Global clusters represented: 3

DBSCAN:
  DBSCAN found: 15 clusters, 234 noise points
  Kept: 15 clusters (cap=50)
  Global clusters represented: 12
```

### 4. Visualization Differences

#### t-SNE Plots

**Affinity Propagation**:
- All points shown with cluster colors
- No distinction for problematic points
- Title: "'{word}' Term X Year Y (t-SNE - Unified Projection)"

**DBSCAN**:
- Cluster points shown with numeric labels
- Noise points shown as gray 'x' markers
- Clear visual distinction between clusters and noise
- Title: "'{word}' Term X Year Y (t-SNE - DBSCAN)"

### 5. Performance Comparison

#### Speed Benchmarks (Approximate)

| Dataset Size | Affinity Propagation | DBSCAN |
|-------------|---------------------|---------|
| 100 samples | ~1 second | ~0.1 seconds |
| 1,000 samples | ~30 seconds | ~1 second |
| 10,000 samples | ~15 minutes | ~10 seconds |
| 50,000 samples | Several hours | ~1 minute |

#### Memory Usage

Both algorithms have similar memory requirements (O(N²) for similarity matrix in AP, O(N) for DBSCAN with spatial indexing).

### 6. Use Case Recommendations

#### Use Affinity Propagation When:

1. **Dataset is small** (<5,000 samples)
2. **You want automatic cluster count** determination
3. **All points should belong to clusters** (no outliers expected)
4. **Cluster representatives (exemplars)** are important
5. **You prefer fewer parameters** to tune

**Example scenario**: Clustering parliamentary speech themes where every speech should have a theme, and you want representative examples.

#### Use DBSCAN When:

1. **Dataset is large** (>10,000 samples)
2. **Outliers/noise are expected** and should be identified
3. **Clusters have irregular shapes** or varying sizes
4. **Speed is important**
5. **You can invest time in parameter tuning**

**Example scenario**: Discovering semantic clusters in large-scale speech data where some contexts might be ambiguous or off-topic.

### 7. Practical Tuning Strategies

#### For Affinity Propagation (widid.ipynb)

```python
# If you want more clusters:
ap = AffinityPropagation(preference=higher_value)

# If you want fewer clusters:
ap = AffinityPropagation(preference=lower_value)

# If convergence is slow:
ap = AffinityPropagation(damping=0.9)  # Higher damping
```

#### For DBSCAN (dbscan.ipynb)

```python
# Start with these defaults:
DBSCAN_EPS = 0.3
DBSCAN_MIN_SAMPLES = 3

# Too many noise points? Make less strict:
DBSCAN_EPS = 0.4  # Increase
DBSCAN_MIN_SAMPLES = 2  # Decrease

# Too few clusters? Make more sensitive:
DBSCAN_EPS = 0.25  # Decrease
DBSCAN_MIN_SAMPLES = 2  # Decrease

# Too many small clusters? Merge more:
DBSCAN_EPS = 0.4  # Increase
DBSCAN_MIN_SAMPLES = 5  # Increase
```

### 8. Result Interpretation

#### Affinity Propagation Results

```python
# All contexts assigned to clusters
contexts_per_cluster = df.groupby('local_cluster').size()
# No noise points
# Exemplars represent each cluster
```

**Interpretation**: Every speech context has been assigned to a semantic cluster. The exemplar for each cluster represents the most typical usage.

#### DBSCAN Results

```python
# Separate clusters and noise
n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
n_noise = list(labels).count(-1)
noise_ratio = n_noise / len(labels)
```

**Interpretation**: 
- **Clusters**: Cohesive semantic groups
- **Noise** (-1): Ambiguous, rare, or off-topic contexts
- **High noise ratio** (>30%): Consider adjusting parameters or data quality

### 9. Code Modifications Required

To switch from widid.ipynb to dbscan.ipynb, the key changes are:

```python
# BEFORE (widid.ipynb):
from sklearn.cluster import AffinityPropagation

ap = AffinityPropagation(random_state=42)
ap.fit(embeddings)
local_labels = ap.labels_

# AFTER (dbscan.ipynb):
from sklearn.cluster import DBSCAN

dbscan = DBSCAN(
    eps=0.3,
    min_samples=3,
    metric='cosine'
)
dbscan.fit(embeddings)
local_labels = dbscan.labels_

# Additional: Count and report noise
n_clusters = len(set(local_labels)) - (1 if -1 in local_labels else 0)
n_noise = list(local_labels).count(-1)
print(f"DBSCAN found: {n_clusters} clusters, {n_noise} noise points")
```

## Conclusion

Both algorithms have their place in the WiDiD framework:

- **Use `widid.ipynb`** for smaller, cleaner datasets where you want automatic cluster discovery
- **Use `dbscan.ipynb`** for larger, noisier datasets where outlier detection and speed are important

The choice ultimately depends on:
1. Dataset size
2. Presence of noise/outliers
3. Need for speed
4. Willingness to tune parameters

Both implementations maintain the same overall workflow and produce comparable outputs, making it easy to experiment with both approaches on your data.

