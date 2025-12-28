"""
Test HDBSCAN parameters on sample data to find optimal clustering settings.

This script helps tune HDBSCAN parameters by testing different combinations
on a sample of the keyword embeddings.

Usage:
    python test_hdbscan_parameters.py [--sample-size N]
"""

import argparse
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from itertools import product
import hdbscan
from sklearn.metrics import silhouette_score
import warnings
warnings.filterwarnings('ignore')

def load_sample_data(csv_path: str, embeddings_path: str, sample_size: int = 5000):
    """Load sample of data for testing."""
    print(f"📥 Loading sample data (n={sample_size})...")
    
    # Load CSV
    df = pd.read_csv(csv_path)
    
    # Sample randomly
    if sample_size < len(df):
        df_sample = df.sample(n=sample_size, random_state=42)
        indices = df_sample.index.tolist()
    else:
        df_sample = df
        indices = list(range(len(df)))
    
    # Load embeddings (if they exist)
    try:
        embeddings = np.load(embeddings_path)
        embeddings_sample = embeddings[indices]
        print(f"✅ Loaded {len(df_sample):,} samples with embeddings")
        return df_sample, embeddings_sample
    except FileNotFoundError:
        print(f"⚠️  Embeddings file not found at {embeddings_path}")
        print(f"   Please run the main notebook first to generate embeddings.")
        return None, None


def test_hdbscan_params(
    embeddings: np.ndarray,
    min_cluster_sizes: list,
    min_samples_list: list,
    metrics: list = ['euclidean']
):
    """
    Test different HDBSCAN parameter combinations.
    
    Returns DataFrame with results for each combination.
    """
    results = []
    total_tests = len(min_cluster_sizes) * len(min_samples_list) * len(metrics)
    
    print(f"\n🔬 Testing {total_tests} parameter combinations...")
    print(f"   min_cluster_size: {min_cluster_sizes}")
    print(f"   min_samples: {min_samples_list}")
    print(f"   metrics: {metrics}\n")
    
    test_num = 0
    for min_cluster_size, min_samples, metric in product(min_cluster_sizes, min_samples_list, metrics):
        test_num += 1
        print(f"[{test_num}/{total_tests}] Testing: min_cluster_size={min_cluster_size}, min_samples={min_samples}, metric={metric}")
        
        try:
            # Run HDBSCAN
            clusterer = hdbscan.HDBSCAN(
                min_cluster_size=min_cluster_size,
                min_samples=min_samples,
                metric=metric
            )
            labels = clusterer.fit_predict(embeddings)
            
            # Calculate metrics
            n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
            n_outliers = np.sum(labels == -1)
            outlier_pct = n_outliers / len(labels) * 100
            
            # Silhouette score (only if we have at least 2 clusters and not all outliers)
            silhouette = None
            if n_clusters >= 2 and n_outliers < len(labels):
                # Only calculate on non-outliers
                mask = labels != -1
                if mask.sum() > 0:
                    try:
                        silhouette = silhouette_score(embeddings[mask], labels[mask])
                    except:
                        silhouette = None
            
            # Cluster sizes
            cluster_sizes = pd.Series(labels[labels != -1]).value_counts()
            avg_cluster_size = cluster_sizes.mean() if len(cluster_sizes) > 0 else 0
            min_cluster_size_actual = cluster_sizes.min() if len(cluster_sizes) > 0 else 0
            max_cluster_size_actual = cluster_sizes.max() if len(cluster_sizes) > 0 else 0
            
            results.append({
                'min_cluster_size': min_cluster_size,
                'min_samples': min_samples,
                'metric': metric,
                'n_clusters': n_clusters,
                'n_outliers': n_outliers,
                'outlier_pct': outlier_pct,
                'silhouette': silhouette,
                'avg_cluster_size': avg_cluster_size,
                'min_size': min_cluster_size_actual,
                'max_size': max_cluster_size_actual
            })
            
            print(f"    → {n_clusters} clusters, {n_outliers} outliers ({outlier_pct:.1f}%), silhouette={silhouette:.3f if silhouette else 'N/A'}")
            
        except Exception as e:
            print(f"    ❌ Error: {e}")
            continue
    
    return pd.DataFrame(results)


def visualize_results(results_df: pd.DataFrame):
    """Create visualizations of parameter test results."""
    
    fig, axes = plt.subplots(2, 2, figsize=(15, 12))
    
    # 1. Number of clusters vs parameters
    ax = axes[0, 0]
    for min_samples in results_df['min_samples'].unique():
        data = results_df[results_df['min_samples'] == min_samples]
        ax.plot(data['min_cluster_size'], data['n_clusters'], marker='o', label=f'min_samples={min_samples}')
    ax.set_xlabel('min_cluster_size')
    ax.set_ylabel('Number of Clusters')
    ax.set_title('Number of Clusters vs min_cluster_size')
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    # 2. Outlier percentage vs parameters
    ax = axes[0, 1]
    for min_samples in results_df['min_samples'].unique():
        data = results_df[results_df['min_samples'] == min_samples]
        ax.plot(data['min_cluster_size'], data['outlier_pct'], marker='o', label=f'min_samples={min_samples}')
    ax.set_xlabel('min_cluster_size')
    ax.set_ylabel('Outlier Percentage (%)')
    ax.set_title('Outlier Percentage vs min_cluster_size')
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    # 3. Silhouette score vs parameters
    ax = axes[1, 0]
    valid_silhouette = results_df[results_df['silhouette'].notna()]
    for min_samples in valid_silhouette['min_samples'].unique():
        data = valid_silhouette[valid_silhouette['min_samples'] == min_samples]
        ax.plot(data['min_cluster_size'], data['silhouette'], marker='o', label=f'min_samples={min_samples}')
    ax.set_xlabel('min_cluster_size')
    ax.set_ylabel('Silhouette Score')
    ax.set_title('Silhouette Score vs min_cluster_size')
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    # 4. Average cluster size vs parameters
    ax = axes[1, 1]
    for min_samples in results_df['min_samples'].unique():
        data = results_df[results_df['min_samples'] == min_samples]
        ax.plot(data['min_cluster_size'], data['avg_cluster_size'], marker='o', label=f'min_samples={min_samples}')
    ax.set_xlabel('min_cluster_size')
    ax.set_ylabel('Average Cluster Size')
    ax.set_title('Average Cluster Size vs min_cluster_size')
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig('../data/hdbscan_parameter_test.png', dpi=150, bbox_inches='tight')
    print(f"\n💾 Saved visualization to: ../data/hdbscan_parameter_test.png")
    plt.show()


def main():
    parser = argparse.ArgumentParser(description="Test HDBSCAN parameters")
    parser.add_argument('--sample-size', type=int, default=5000, help='Number of samples to test on')
    parser.add_argument('--csv', type=str, default='../data/speech_keywords.csv', help='Path to keywords CSV')
    parser.add_argument('--embeddings', type=str, default='../data/keyword_embeddings.npy', help='Path to embeddings file')
    
    args = parser.parse_args()
    
    print("=" * 80)
    print("HDBSCAN Parameter Testing")
    print("=" * 80)
    
    # Load data
    df, embeddings = load_sample_data(args.csv, args.embeddings, args.sample_size)
    
    if embeddings is None:
        print("\n❌ Cannot proceed without embeddings.")
        print("   Run the main notebook first to generate embeddings.")
        return
    
    # Define parameter ranges to test
    min_cluster_sizes = [30, 50, 75, 100, 150]
    min_samples_list = [5, 10, 15, 20]
    metrics = ['euclidean']
    
    # Test parameters
    results = test_hdbscan_params(
        embeddings,
        min_cluster_sizes,
        min_samples_list,
        metrics
    )
    
    # Display results
    print("\n" + "=" * 80)
    print("RESULTS SUMMARY")
    print("=" * 80)
    print("\nTop 5 configurations by silhouette score:")
    top_results = results.nlargest(5, 'silhouette')[['min_cluster_size', 'min_samples', 'n_clusters', 'outlier_pct', 'silhouette', 'avg_cluster_size']]
    print(top_results.to_string(index=False))
    
    print("\n\nTop 5 configurations by number of clusters:")
    top_clusters = results.nlargest(5, 'n_clusters')[['min_cluster_size', 'min_samples', 'n_clusters', 'outlier_pct', 'silhouette', 'avg_cluster_size']]
    print(top_clusters.to_string(index=False))
    
    print("\n\nConfigurations with lowest outlier percentage:")
    low_outliers = results.nsmallest(5, 'outlier_pct')[['min_cluster_size', 'min_samples', 'n_clusters', 'outlier_pct', 'silhouette', 'avg_cluster_size']]
    print(low_outliers.to_string(index=False))
    
    # Save results
    results_file = '../data/hdbscan_parameter_results.csv'
    results.to_csv(results_file, index=False)
    print(f"\n💾 Saved detailed results to: {results_file}")
    
    # Visualize
    visualize_results(results)
    
    print("\n" + "=" * 80)
    print("✅ PARAMETER TESTING COMPLETE!")
    print("=" * 80)
    print("\nRecommendations:")
    print("- For more fine-grained topics: Use lower min_cluster_size (30-50)")
    print("- For fewer, larger topics: Use higher min_cluster_size (100-150)")
    print("- For fewer outliers: Use lower min_cluster_size and lower min_samples")
    print("- For better cluster quality: Choose parameters with higher silhouette score")


if __name__ == "__main__":
    main()
