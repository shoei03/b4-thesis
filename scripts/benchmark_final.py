#!/usr/bin/env python3
"""Final benchmark for Phase 5.3.3 optimizations.

This script benchmarks the complete optimization suite:
- Baseline (no optimizations)
- Phase 5.3.1 (pre-filters, cache, smart parallel)
- Phase 5.3.2 (LSH, banded LCS, top-k)
- Phase 5.3.3 (NumPy vectorization, progressive thresholds)
"""

from pathlib import Path
import sys
import time

import pandas as pd

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from b4_thesis.analysis.method_matcher import MethodMatcher
from b4_thesis.core.revision_manager import RevisionManager


def load_test_data(data_dir: Path, num_revisions: int = 2):
    """Load test data from clone_NIL dataset.

    Args:
        data_dir: Path to data directory
        num_revisions: Number of revisions to load (default: 2)

    Returns:
        List of (blocks_df, revision_name) tuples
    """
    rev_manager = RevisionManager(data_dir)
    revisions = rev_manager.get_revisions()[:num_revisions]

    data = []
    for rev_info in revisions:
        blocks, _ = rev_manager.load_revision_data(rev_info)
        data.append((blocks, rev_info.revision_id))

    return data


def benchmark_configuration(
    config_name: str,
    source_blocks: pd.DataFrame,
    target_blocks: pd.DataFrame,
    matcher_kwargs: dict,
) -> dict:
    """Benchmark a single configuration.

    Args:
        config_name: Name of the configuration
        source_blocks: Source blocks DataFrame
        target_blocks: Target blocks DataFrame
        matcher_kwargs: Keyword arguments for MethodMatcher

    Returns:
        Dictionary with benchmark results
    """
    print(f"\n{'=' * 60}")
    print(f"Benchmarking: {config_name}")
    print(f"{'=' * 60}")

    matcher = MethodMatcher(**matcher_kwargs)

    start_time = time.time()
    result = matcher.match_blocks(source_blocks, target_blocks)
    elapsed_time = time.time() - start_time

    num_matches = len(result.forward_matches)
    num_token_hash = sum(1 for t in result.match_types.values() if t == "token_hash")
    num_similarity = sum(1 for t in result.match_types.values() if t == "similarity")

    print(f"  Time: {elapsed_time:.2f}s")
    print(f"  Total matches: {num_matches:,}")
    print(f"  - Token hash: {num_token_hash:,}")
    print(f"  - Similarity: {num_similarity:,}")

    return {
        "config": config_name,
        "time_seconds": elapsed_time,
        "total_matches": num_matches,
        "token_hash_matches": num_token_hash,
        "similarity_matches": num_similarity,
    }


def main():
    """Run final benchmark."""
    # Check if data exists
    data_dir = Path("data/clone_NIL")
    if not data_dir.exists():
        print("Error: Data directory not found:", data_dir)
        print("Skipping benchmark (requires real data)")
        return

    print("Loading test data...")
    data = load_test_data(data_dir, num_revisions=2)

    if len(data) < 2:
        print("Error: Not enough revisions in dataset")
        return

    source_blocks, source_name = data[0]
    target_blocks, target_name = data[1]

    print(f"Source: {source_name} ({len(source_blocks):,} blocks)")
    print(f"Target: {target_name} ({len(target_blocks):,} blocks)")

    results = []

    # Configuration 1: Baseline (no optimizations)
    results.append(
        benchmark_configuration(
            config_name="Baseline (no optimizations)",
            source_blocks=source_blocks,
            target_blocks=target_blocks,
            matcher_kwargs={
                "similarity_threshold": 70,
                "use_lsh": False,
                "use_optimized_similarity": False,
                "progressive_thresholds": None,
            },
        )
    )

    # Configuration 2: Phase 5.3.1 optimizations
    results.append(
        benchmark_configuration(
            config_name="Phase 5.3.1 (pre-filters + cache)",
            source_blocks=source_blocks,
            target_blocks=target_blocks,
            matcher_kwargs={
                "similarity_threshold": 70,
                "use_lsh": False,
                "use_optimized_similarity": False,
                "progressive_thresholds": None,
            },
        )
    )

    # Configuration 3: Phase 5.3.2 optimizations (LSH + banded LCS)
    results.append(
        benchmark_configuration(
            config_name="Phase 5.3.2 (LSH + banded LCS)",
            source_blocks=source_blocks,
            target_blocks=target_blocks,
            matcher_kwargs={
                "similarity_threshold": 70,
                "use_lsh": True,
                "lsh_threshold": 0.7,
                "lsh_num_perm": 128,
                "top_k": 20,
                "use_optimized_similarity": True,
                "progressive_thresholds": None,
            },
        )
    )

    # Configuration 4: Phase 5.3.3 (progressive thresholds)
    results.append(
        benchmark_configuration(
            config_name="Phase 5.3.3 (progressive thresholds)",
            source_blocks=source_blocks,
            target_blocks=target_blocks,
            matcher_kwargs={
                "similarity_threshold": 70,
                "use_lsh": True,
                "lsh_threshold": 0.7,
                "lsh_num_perm": 128,
                "top_k": 20,
                "use_optimized_similarity": True,
                "progressive_thresholds": [90, 80, 70],
            },
        )
    )

    # Print summary
    print(f"\n{'=' * 60}")
    print("BENCHMARK SUMMARY")
    print(f"{'=' * 60}")

    df_results = pd.DataFrame(results)
    print("\nPerformance comparison:")
    print(df_results.to_string(index=False))

    # Calculate speedup
    baseline_time = results[0]["time_seconds"]
    print("\nSpeedup vs Baseline:")
    for r in results[1:]:
        speedup = baseline_time / r["time_seconds"]
        print(f"  {r['config']}: {speedup:.2f}x")

    # Save results
    output_path = Path("benchmark_results_phase_5.3.3.csv")
    df_results.to_csv(output_path, index=False)
    print(f"\nResults saved to: {output_path}")


if __name__ == "__main__":
    main()
