#!/usr/bin/env python3
"""
Wave-3 Module W3.4: Clustering Regimes Analysis
Identify market regimes through unsupervised clustering.
"""

import pandas as pd
import numpy as np
import os
from datetime import datetime
from pathlib import Path
import sys
from typing import Dict, List, Optional, Tuple
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score, calinski_harabasz_score
import json

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent.parent))


class Wave3ClusteringExecutor:
    """Execute clustering analysis for Wave-3."""

    def __init__(self):
        self.wave3_dir = "data/derived/btc_usd/wave3"
        self.analysis_dir = "analysis/wave3/btc_usd/clustering"
        self.venues = ["binance", "coinbase", "kraken", "okx", "bybit"]

        os.makedirs(self.analysis_dir, exist_ok=True)

    def run_clustering_analysis(self):
        """Run clustering analysis module."""
        print("🔧 Wave-3 Module W3.4: Clustering Regimes Analysis")
        print("=" * 50)

        # Load clustering features
        print("📥 Loading clustering features...")
        clustering_data = pd.read_parquet(f"{self.wave3_dir}/clustering_features.parquet")
        print(f"  📊 Clustering data: {clustering_data.shape}")

        # Prepare features for clustering
        print("🔄 Preparing features for clustering...")
        features_data = self._prepare_clustering_features(clustering_data)

        if features_data is None:
            print("❌ Failed to prepare clustering features")
            return False

        # Evaluate different numbers of clusters
        print("🔄 Evaluating cluster numbers...")
        cluster_results = self._evaluate_cluster_numbers(features_data)

        # Perform final clustering
        print("🔄 Performing final clustering...")
        final_clustering = self._perform_final_clustering(features_data, cluster_results)

        # Characterize clusters
        print("🔄 Characterizing clusters...")
        cluster_profiles = self._characterize_clusters(features_data, final_clustering)

        # Generate outputs
        print("📊 Generating clustering outputs...")
        self._generate_clustering_outputs(cluster_results, final_clustering, cluster_profiles)

        print("✅ Clustering analysis completed successfully!")
        return True

    def _prepare_clustering_features(self, clustering_data: pd.DataFrame) -> Optional[pd.DataFrame]:
        """Prepare features for clustering."""
        # Select numeric features (exclude window info and session label)
        exclude_cols = ["window_start", "window_end", "session_label"]
        feature_cols = [col for col in clustering_data.columns if col not in exclude_cols]

        # Filter to numeric columns only
        numeric_cols = clustering_data[feature_cols].select_dtypes(include=[np.number]).columns
        features_data = clustering_data[numeric_cols].copy()

        # Handle missing values
        features_data = features_data.fillna(0)

        print(f"  📊 Using {len(numeric_cols)} features for clustering")
        print(f"  📊 Features shape: {features_data.shape}")

        return features_data if len(features_data) > 0 else None

    def _evaluate_cluster_numbers(self, features_data: pd.DataFrame) -> Dict:
        """Evaluate different numbers of clusters."""
        cluster_results = {}

        # Test k ∈ {2, 3, 4}
        k_values = [2, 3, 4]

        for k in k_values:
            print(f"  🔄 Testing k={k}...")

            # Perform k-means clustering
            kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
            cluster_labels = kmeans.fit_predict(features_data)

            # Calculate metrics
            silhouette = silhouette_score(features_data, cluster_labels)
            calinski_harabasz = calinski_harabasz_score(features_data, cluster_labels)

            cluster_results[k] = {
                "silhouette_score": silhouette,
                "calinski_harabasz_score": calinski_harabasz,
                "inertia": kmeans.inertia_,
                "n_clusters": k,
                "cluster_labels": cluster_labels.tolist(),
            }

            print(f"    ✅ k={k}: Silhouette={silhouette:.4f}, CH={calinski_harabasz:.4f}")

        # Select best k based on silhouette score
        best_k = max(cluster_results.keys(), key=lambda k: cluster_results[k]["silhouette_score"])
        print(
            f"  📊 Best k: {best_k} (Silhouette: {cluster_results[best_k]['silhouette_score']:.4f})"
        )

        return cluster_results

    def _perform_final_clustering(self, features_data: pd.DataFrame, cluster_results: Dict) -> Dict:
        """Perform final clustering with best k."""
        # Get best k
        best_k = max(cluster_results.keys(), key=lambda k: cluster_results[k]["silhouette_score"])

        # Perform final clustering
        kmeans = KMeans(n_clusters=best_k, random_state=42, n_init=10)
        cluster_labels = kmeans.fit_predict(features_data)

        return {
            "best_k": best_k,
            "cluster_labels": cluster_labels.tolist(),
            "cluster_centers": kmeans.cluster_centers_.tolist(),
            "inertia": kmeans.inertia_,
            "silhouette_score": cluster_results[best_k]["silhouette_score"],
            "calinski_harabasz_score": cluster_results[best_k]["calinski_harabasz_score"],
        }

    def _characterize_clusters(self, features_data: pd.DataFrame, final_clustering: Dict) -> Dict:
        """Characterize clusters by their features."""
        cluster_profiles = {}

        cluster_labels = np.array(final_clustering["cluster_labels"])
        n_clusters = final_clustering["best_k"]

        for cluster_id in range(n_clusters):
            cluster_mask = cluster_labels == cluster_id
            cluster_data = features_data[cluster_mask]

            if len(cluster_data) == 0:
                continue

            # Calculate cluster statistics
            cluster_stats = {
                "cluster_id": cluster_id,
                "n_windows": len(cluster_data),
                "size_pct": len(cluster_data) / len(features_data) * 100,
                "mean_features": cluster_data.mean().to_dict(),
                "std_features": cluster_data.std().to_dict(),
                "feature_ranges": {
                    "min": cluster_data.min().to_dict(),
                    "max": cluster_data.max().to_dict(),
                },
            }

            # Identify key features (highest variance)
            feature_vars = cluster_data.var().sort_values(ascending=False)
            cluster_stats["top_features"] = feature_vars.head(5).to_dict()

            # Calculate coordination-like score
            # Low variance + low dispersion = coordination-like
            mean_variance = cluster_data.var().mean()
            mean_dispersion = cluster_data.mean().std()  # Cross-feature dispersion

            coordination_score = 1.0 / (1.0 + mean_variance + mean_dispersion)
            cluster_stats["coordination_score"] = coordination_score

            cluster_profiles[cluster_id] = cluster_stats

        return cluster_profiles

    def _generate_clustering_outputs(
        self, cluster_results: Dict, final_clustering: Dict, cluster_profiles: Dict
    ):
        """Generate clustering analysis outputs."""
        # Save cluster labels
        labels_data = pd.DataFrame(
            {
                "window_index": range(len(final_clustering["cluster_labels"])),
                "cluster_label": final_clustering["cluster_labels"],
            }
        )
        labels_file = f"{self.analysis_dir}/labels.csv"
        labels_data.to_csv(labels_file, index=False)
        print(f"  💾 Cluster labels saved to {labels_file}")

        # Save cluster profiles
        profiles_data = []
        for cluster_id, profile in cluster_profiles.items():
            profiles_data.append(
                {
                    "cluster_id": profile["cluster_id"],
                    "n_windows": profile["n_windows"],
                    "size_pct": profile["size_pct"],
                    "coordination_score": profile["coordination_score"],
                    "mean_variance": (
                        np.mean(list(profile["mean_features"].values()))
                        if profile["mean_features"]
                        else 0
                    ),
                    "feature_dispersion": (
                        np.std(list(profile["mean_features"].values()))
                        if profile["mean_features"]
                        else 0
                    ),
                }
            )

        profiles_df = pd.DataFrame(profiles_data)
        profiles_file = f"{self.analysis_dir}/cluster_profiles.csv"
        profiles_df.to_csv(profiles_file, index=False)
        print(f"  💾 Cluster profiles saved to {profiles_file}")

        # Generate summary report
        self._generate_clustering_summary(cluster_results, final_clustering, cluster_profiles)

    def _generate_clustering_summary(
        self, cluster_results: Dict, final_clustering: Dict, cluster_profiles: Dict
    ):
        """Generate clustering summary report."""
        summary_file = f"{self.analysis_dir}/W3_CLUSTERING_SUMMARY.md"

        with open(summary_file, "w") as f:
            f.write("# Wave-3 Clustering Analysis Summary\n\n")
            f.write(f"**Analysis Date**: {datetime.now().isoformat()}\n")
            f.write("**Method**: Unsupervised Clustering (k-means)\n")
            f.write(
                "**Hypothesis**: Competitive markets show environment-aligned clusters; coordination shows suppressed variance clusters\n\n"
            )

            # Cluster evaluation results
            f.write("## Cluster Evaluation Results\n\n")
            f.write("| k | Silhouette Score | Calinski-Harabasz | Inertia |\n")
            f.write("|---|------------------|-------------------|----------|\n")

            for k, results in cluster_results.items():
                f.write(
                    f"| {k} | {results['silhouette_score']:.4f} | {results['calinski_harabasz_score']:.2f} | {results['inertia']:.2f} |\n"
                )

            f.write(
                f"\n**Best k**: {final_clustering['best_k']} (Silhouette: {final_clustering['silhouette_score']:.4f})\n\n"
            )

            # Final clustering results
            f.write("## Final Clustering Results\n\n")
            f.write(f"- **Number of clusters**: {final_clustering['best_k']}\n")
            f.write(f"- **Silhouette score**: {final_clustering['silhouette_score']:.4f}\n")
            f.write(
                f"- **Calinski-Harabasz score**: {final_clustering['calinski_harabasz_score']:.2f}\n"
            )
            f.write(f"- **Inertia**: {final_clustering['inertia']:.2f}\n\n")

            # Cluster profiles
            f.write("## Cluster Profiles\n\n")
            f.write(
                "| Cluster | Windows | Size % | Coordination Score | Mean Variance | Feature Dispersion |\n"
            )
            f.write(
                "|---------|---------|--------|-------------------|---------------|-------------------|\n"
            )

            for cluster_id, profile in cluster_profiles.items():
                mean_variance = (
                    np.mean(list(profile["mean_features"].values()))
                    if profile["mean_features"]
                    else 0
                )
                feature_dispersion = (
                    np.std(list(profile["mean_features"].values()))
                    if profile["mean_features"]
                    else 0
                )

                f.write(
                    f"| {cluster_id} | {profile['n_windows']} | {profile['size_pct']:.1f}% | {profile['coordination_score']:.4f} | {mean_variance:.4f} | {feature_dispersion:.4f} |\n"
                )

            # Red flag analysis
            f.write("\n## Red Flag Analysis\n\n")

            # Look for coordination-like clusters
            coordination_clusters = []
            for cluster_id, profile in cluster_profiles.items():
                if profile["coordination_score"] > 0.5:  # High coordination score
                    coordination_clusters.append(cluster_id)

            if coordination_clusters:
                f.write("### ⚠️ COORDINATION-LIKE CLUSTERS DETECTED\n\n")
                f.write(
                    "The following clusters show characteristics consistent with coordination:\n\n"
                )

                for cluster_id in coordination_clusters:
                    profile = cluster_profiles[cluster_id]
                    f.write(
                        f"- **Cluster {cluster_id}**: {profile['n_windows']} windows ({profile['size_pct']:.1f}% of data)\n"
                    )
                    f.write(f"  - Coordination score: {profile['coordination_score']:.4f}\n")
                    f.write(f"  - Low variance and dispersion suggest coordinated behavior\n\n")

                f.write(
                    "**Interpretation**: These clusters show suppressed variance and low dispersion across venues, which is consistent with coordinated market making rather than competitive dynamics.\n\n"
                )
            else:
                f.write("### ✅ NO COORDINATION-LIKE CLUSTERS DETECTED\n\n")
                f.write("All clusters show characteristics consistent with competitive behavior:\n")
                f.write("- Moderate to high variance across features\n")
                f.write("- Reasonable dispersion between venues\n")
                f.write("- No evidence of suppressed competition\n\n")

            # Interpretation
            f.write("## Interpretation\n\n")
            f.write("### Competitive Markets\n")
            f.write("- Clusters align with market environments/sessions\n")
            f.write("- High variance and dispersion within clusters\n")
            f.write("- No clusters with suppressed competition\n\n")

            f.write("### Coordinated Markets\n")
            f.write("- Clusters with low variance and dispersion\n")
            f.write("- Suppressed competition across venues\n")
            f.write("- Environment-invariant behavior patterns\n\n")

            # Limitations
            f.write("## Limitations\n\n")
            f.write("- Single-day analysis limits generalizability\n")
            f.write("- k-means assumes spherical clusters\n")
            f.write("- Feature selection may miss important patterns\n")
            f.write("- No temporal dynamics in clustering\n")
            f.write("- Coordination score is heuristic-based\n")

        print(f"  💾 Summary saved to {summary_file}")


if __name__ == "__main__":
    executor = Wave3ClusteringExecutor()
    success = executor.run_clustering_analysis()

    if success:
        print("\n🎉 Wave-3 Clustering analysis completed successfully!")
    else:
        print("\n❌ Wave-3 Clustering analysis failed!")
        sys.exit(1)
