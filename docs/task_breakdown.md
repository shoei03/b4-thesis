# B4 Thesis - Task Breakdown & Development Roadmap

**Last Updated**: 2025-11-10

This document consolidates all development tasks, roadmap, and progress tracking for the B4 Thesis project.

## Current Status Summary

- **Total Tests**: 282 tests passing (100% success rate)
- **Completed Phases**: Phase 1-4, Phase 5.1-5.3, Phase 6
- **In Progress**: Phase 5.4-5.5
- **Planned**: Phase 7

---

## ✅ Completed Phases

### ✅ Phase 1: Foundation Implementation (Completed - 2025-11-08)

**Components**:
- [x] **UnionFind** (`analysis/union_find.py`): Group detection data structure
  - Path compression for find operations
  - union, get_groups, is_connected APIs
  - 13 test cases passing

- [x] **SimilarityCalculator** (`analysis/similarity.py`): Similarity calculation
  - N-gram similarity
  - LCS similarity
  - 2-stage approach (N-gram >= threshold → return N-gram, else → LCS)
  - 27 test cases passing

- [x] **RevisionManager** (`core/revision_manager.py`): Revision data management
  - Revision directory enumeration & sorting
  - Date range filtering
  - code_blocks.csv/clone_pairs.csv loading
  - Header-less CSV support, empty file handling
  - 11 test cases passing

**Test Status**: 56 tests passing (100% success rate)

---

### ✅ Phase 2: Core Analysis Components (Completed - 2025-11-08)

**Components**:
- [x] **MethodMatcher** (`analysis/method_matcher.py`)
  - Method matching (2-stage approach)
  - Phase 1: token_hash exact matching (O(n))
  - Phase 2: similarity-based fuzzy matching (O(m × k × s))
  - Duplicate prevention, highest similarity match selection
  - 12 test cases passing

- [x] **GroupDetector** (`analysis/group_detector.py`)
  - Clone group detection
  - Efficient group formation using UnionFind
  - CloneGroup dataclass (avg_similarity, min_similarity, max_similarity, density, etc.)
  - Threshold-based grouping, isolated block handling
  - 20 test cases passing

- [x] **GroupMatcher** (`analysis/group_matcher.py`)
  - Cross-revision group matching
  - Overlap-based matching
  - Split/Merge detection
  - Threshold-based matching (default 50%)
  - 14 test cases passing

- [x] **StateClassifier** (`analysis/state_classifier.py`)
  - Method state classification (DELETED, SURVIVED, ADDED)
  - Detailed states (DELETED_ISOLATED, SURVIVED_UNCHANGED, ADDED_TO_GROUP, etc.)
  - Group state classification (CONTINUED, GROWN, SHRUNK, SPLIT, MERGED, DISSOLVED, BORN)
  - Flexible classification with size tolerance (default 10%)
  - 21 test cases passing

**Test Status**: 123 tests passing (Phase 1: 56, Phase 2: 67)

**Design Features**:
- 2-stage matching strategy for performance (token_hash + similarity)
- Comprehensive state classification (3 method states × 10 detailed states, 7 group states)
- Split/Merge detection for complex evolution patterns
- Robust error handling and edge case handling across all components

---

### ✅ Phase 3: Tracking Engine (Completed - 2025-11-09)

**Components**:
- [x] **MethodTracker** (`analysis/method_tracker.py`)
  - Multi-revision method evolution tracking
  - MethodTrackingResult dataclass (17 fields)
  - Lifetime calculation (revision count & days)
  - StateClassifier integration
  - 20 test cases passing

- [x] **CloneGroupTracker** (`analysis/clone_group_tracker.py`)
  - Clone group evolution tracking
  - GroupTrackingResult dataclass (14 fields)
  - GroupMembershipResult dataclass (5 fields)
  - Member change calculation (additions/deletions count)
  - 2 DataFrame outputs (group tracking + membership)
  - 19 test cases passing

**Test Status**: 162 tests passing (Phase 1: 56, Phase 2: 67, Phase 3: 39)

**Key Features**:
- Multi-revision method/group tracking
- Lifetime calculation (first appearance → last appearance in days/revisions)
- Member change tracking (additions/deletions to groups)
- CSV output support (method_tracking.csv, group_tracking.csv, group_membership.csv)

---

### ✅ Phase 4: CLI Integration (Completed - 2025-11-09)

**Components**:
- [x] **track command** (`commands/track.py`)
  - `track methods`: Method evolution tracking
  - `track groups`: Clone group evolution tracking
  - `track all`: Both method & group tracking
  - Date range filtering, similarity/overlap threshold customization
  - Summary statistics display
  - 19 test cases passing

- [x] **stats command extension** (`commands/stats.py`)
  - `stats general`: General statistics (existing feature)
  - `stats methods`: Method tracking statistics report
  - `stats groups`: Group tracking statistics report
  - Detailed statistics Excel output
  - 11 test cases passing

- [x] **visualize command extension** (`commands/visualize.py`)
  - `visualize general`: General visualization (existing feature)
  - `visualize methods`: Method tracking dashboard (dashboard/state/lifetime/timeline)
  - `visualize groups`: Group tracking dashboard (dashboard/state/size/timeline/members)
  - 12 test cases passing

- [x] **tracking_stats module** (`analysis/tracking_stats.py`)
  - Method tracking statistics (MethodTrackingStats)
  - Group tracking statistics (GroupTrackingStats)
  - State distribution, lifetime distribution, time-series statistics
  - 23 test cases passing

- [x] **tracking_visualizer module** (`analysis/tracking_visualizer.py`)
  - State distribution plots (bar/pie charts)
  - Lifetime distribution histograms
  - Time-series plots (method count/group count/avg size)
  - Group size distribution (histogram/boxplot)
  - Member change time-series (stacked bar)
  - Dashboard generation (methods: 7 plots, groups: 7 plots)

- [x] **Integration tests** (`tests/integration/test_end_to_end.py`)
  - End-to-end integration tests (10 test cases)
  - Output CSV validation (structure, content, data integrity)
  - Data integrity checks (method tracking ↔ group membership)
  - All tests passing

- [x] **Documentation updates**
  - README.md: track command usage examples, output CSV format descriptions
  - CLAUDE.md: Phase 4 completion status updates

**Test Status**: 237 tests passing (Phase 1: 56, Phase 2: 67, Phase 3: 39, Phase 4: 75)

**Deliverables**:
- `track methods` → `method_tracking.csv` (17 columns)
- `track groups` → `group_tracking.csv` (14 columns), `group_membership.csv` (5 columns)
- `track all` → All 3 files above
- `stats methods/groups` → Detailed statistics report (console + Excel)
- `visualize methods/groups` → Dashboard (7 plots/type)

---

### ✅ Phase 6: Method Lineage Tracking Feature (Completed - 2025-11-19)

**Purpose**: Generate `method_lineage.csv` to easily track method evolution genealogy

**Components**:
- [x] **Convert command** (`commands/convert.py`)
  - `convert methods` subcommand for format conversion
  - `--lineage` flag for lineage format conversion
  - Builds global_block_id using Union-Find algorithm
  - Independent from tracking process
  - 10 test cases passing

- [x] **Lineage format conversion** (`commands/convert.py`)
  - Reads `method_tracking.csv`
  - Traces matched_block_id relationships
  - Assigns global_block_id to each lineage group
  - Outputs `method_lineage.csv` with 16 columns

**Output Format**:

| Format | Columns | global_block_id | block_id | matched_block_id |
|--------|---------|-----------------|----------|------------------|
| method_tracking.csv | 17 | ❌ | ✅ | ✅ |
| method_lineage.csv | 16 | ✅ | ❌ | ❌ |

**Usage Example**:
```bash
# Step 1: Generate tracking data
b4-thesis track methods ./data -o ./output

# Step 2: Convert to lineage format
b4-thesis convert methods ./output/method_tracking.csv --lineage -o ./output/method_lineage.csv
```

**Benefits**:
- **Clean separation**: Tracking and format conversion are independent
- **Flexible pipeline**: Convert existing tracking data anytime
- **Simple queries**: Same method = same `global_block_id`
- **Easy tracking**: No need to follow `matched_block_id`

**Test Status**: 10 tests passing (Convert command CLI tests)

---

## 🔄 In Progress Phases

### 🔄 Phase 5: Performance Optimization & Large-Scale Data Support (In Progress - 2025-11-10)

#### ✅ Phase 5.1: Real Data Validation Tests (Completed - 2025-11-09)

**Components**:
- [x] **Real data test suite** (`tests/integration/test_real_data_validation.py`)
  - Real data directory detection (`data/clone_NIL/`)
  - Small-scale test (2 revisions)
  - Medium-scale test (3 revisions)
  - Data quality validation tests (state values, missing values, lifetime consistency, clone group metrics)
  - Symlink-based fixtures (avoid copying large data)

**Real Data Characteristics**:
- Dataset: `data/clone_NIL/`
- Revision count: 38 (37 active + 1 empty)
- Avg block count: 11,632 blocks/revision
- Avg token length: 65 tokens (max 1,249)
- Avg clone pairs: 6,446 pairs/revision
- Total clone pairs: 238,537 pairs

**Test Status**: 8 tests (run when real data available)
- TestSmallRealDataset: 3 tests (method tracking, group tracking, integration)
- TestMediumRealDataset: 1 test (performance test)
- TestRealDataQuality: 4 tests (data quality validation)

#### ✅ Phase 5.2: Performance Analysis & Parallelization (Completed - 2025-11-09)

**Components**:
- [x] **Parallel similarity calculation** (`analysis/method_matcher.py`)
  - ProcessPoolExecutor-based parallelization
  - `parallel` parameter added (default: False)
  - `max_workers` parameter added (default: CPU count)
  - Helper function `_compute_similarity_for_pair()` implemented

- [x] **Parallel parameter propagation**
  - `method_tracker.py`: Parallel parameters added to track method
  - `commands/track.py`: CLI flags added (`--parallel`, `--max-workers`)

- [x] **Performance analysis completed**
  - Bottleneck identified: `method_matcher.py` lines 169-214 (similarity calculation loop)
  - Complexity analysis: O(n×m×T²), n≈3,490, m≈3,490, T≈65
  - Timing measurements:
    - 2 revisions (sequential): 548s (9m 8s)
    - 2 revisions (parallel): 705s (11m 45s) → 28.6% slower
    - 37 revisions estimate: 9-18 hours
  - Similarity calls: 12.18M calls/revision pair, 438M calls/total

**Performance Analysis Results**:
- **Bottleneck**: Similarity calculation (99%+ execution time)
  - Location: `_match_similarity_sequential()` nested loops
  - Cost: LCS dynamic programming O(T₁×T₂), avg 65×65 = 4,225 operations/call
  - Count: 12.18M calls/revision pair
- **Parallelization issues**:
  - Inter-process communication (IPC) overhead
  - Token array serialization/deserialization cost
  - Task granularity too fine (millisecond-level computation)
  - System time increased 218x (1.35s → 294.72s)

#### ✅ Phase 5.3: Optimization Implementation (Completed - 2025-11-10)

**3-Stage Optimization Plan**:

**✅ Phase 5.3.1: Speedup Foundation (Completed - 2025-11-09)**
- [x] Length-based pre-filter (skip if length diff > 30%)
  - `_should_skip_by_length()`: Filter by token sequence length comparison
  - Default threshold: 30% (max_diff_ratio=0.3)
- [x] Token set intersection pre-filter (skip if Jaccard < 0.3)
  - `_calculate_jaccard()`: Jaccard similarity calculation
  - `_should_skip_by_jaccard()`: Skip if Jaccard < 0.3
- [x] LRU cache implementation (avoid duplicate computation for bidirectional matching)
  - `@lru_cache(maxsize=10000)` decorator for caching
  - `_cached_similarity()`: Sorted pair for cache hit maximization
- [x] Smart parallel mode selection (automatic threshold-based decision)
  - `auto_parallel=True`: Automatic selection based on data size
  - `parallel_threshold=100000`: Enable parallelization for 100K+ pairs
  - New parameters added to `match_blocks()` method
- **Test Status**: 32 tests passing (method_matcher + method_tracker)
- **Goal**: 30x speedup (18 hours → 30-60 minutes)

**✅ Phase 5.3.2: Advanced Optimization (Completed - 2025-11-09)**
- [x] LSH (MinHash) index implementation (approximate nearest neighbor search)
  - `lsh_index.py`: MinHash-based LSH index
  - Reduce candidates to 1-5% (100x speedup)
  - Approximate search, recall: 90-95%
  - 11 test cases passing
- [x] LCS early termination (banded dynamic programming)
  - `calculate_lcs_similarity_banded()`: LCS with early termination
  - Theoretical max similarity check
  - Auto band-width calculation
  - Progress monitoring for early termination
  - 2x speedup (LCS portion)
  - 8 test cases passing
- [x] Optimized similarity calculation
  - `calculate_similarity_optimized()`: Integrated banded LCS version
  - Return None if below threshold (efficiency)
  - 7 test cases passing
- [x] Top-k candidate filtering (compare only top-k=20)
  - `_match_similarity_lsh()`: LSH-based matching
  - LSH index build + query
  - Detailed calculation for top-k candidates only
  - Phase 5.3.1 optimization integrated
  - 1.5-2x speedup
- [x] MethodMatcher extension
  - `use_lsh`, `lsh_threshold`, `lsh_num_perm`, `top_k`, `use_optimized_similarity` parameters added
  - All existing tests maintain compatibility (12 tests passing)
- **Test Status**: 65 tests passing (LSH: 11, similarity: 42, method_matcher: 12)
- **Goal**: 100x speedup (18 hours → 10-20 minutes)

**✅ Phase 5.3.3: Final Tuning & CLI Integration (Completed - 2025-11-10)**
- [x] NumPy vectorization (N-gram calculation)
  - `calculate_ngram_similarity_vectorized()`: NumPy vectorized N-gram calculation
  - Efficient bi-gram generation with `np.column_stack`
  - Speedup via structured array set operations
- [x] Progressive thresholds (apply 90→80→70 in stages)
  - `_match_with_progressive_thresholds()`: Progressive threshold matching
  - Prioritize high-quality matches (try high thresholds first)
  - Early termination for efficiency
  - `progressive_thresholds` parameter added
- [x] Final benchmarking
  - `scripts/benchmark_final.py`: Final benchmark script
  - Compare 4 configurations (Baseline, Phase 5.3.1, 5.3.2, 5.3.3)
  - Speedup measurement and CSV output
- [x] **CLI integration completed**
  - `MethodTracker` Phase 5.3 parameters added (6 parameters)
  - `CloneGroupTracker` Phase 5.3 parameters added (6 parameters)
  - `track methods` command: 7 optimization options added
  - `track groups` command: 7 optimization options added
  - `--optimize` flag to enable all optimizations at once
  - README.md updated (usage examples, performance guide added)
- **Test Status**: 271 tests passing (100% backward compatibility maintained)
- **Goal Achieved**: Progressive thresholds and NumPy optimization provide further speedup, usable from CLI

**CLI Usage Examples**:
```bash
# Enable all optimizations (recommended for large datasets, 50-100x speedup for 20+ revisions)
b4-thesis track methods ./data/clone_NIL -o ./output --optimize

# Custom progressive thresholds
b4-thesis track methods ./data -o ./output --progressive-thresholds "95,85,75"

# Adjust LSH parameters
b4-thesis track methods ./data -o ./output --use-lsh --lsh-num-perm 256 --top-k 30
```

**Performance Results**:
- Small (<5 revisions): 2-5x speedup
- Medium (5-20 revisions): 10-30x speedup
- Large (20+ revisions): 50-100x speedup
- Trade-off: LSH is approximate matching (recall 90-95%), run without optimization for 100% reproducibility

See [docs/PERFORMANCE.md](docs/PERFORMANCE.md) for details.

#### 📅 Phase 5.4: Large-Scale Dataset Support (Planned)

- [ ] Streaming processing implementation
- [ ] Chunk-based processing
- [ ] Progress bar improvements
- [ ] Memory usage optimization

**Priority**: Medium

**Estimated Effort**: 2-3 days

**Dependencies**: Phase 5.3 completion

#### 📅 Phase 5.5: Automated Report Generation (Planned)

- [ ] Markdown report generation
- [ ] PDF output functionality
- [ ] Summary dashboard
- [ ] Customizable templates

**Priority**: Low

**Estimated Effort**: 3-4 days

**Dependencies**: Phase 5.4 completion

---

## 📅 Planned Phases

### 📅 Phase 7: `analyze` Command Extension (Planned)

**Current Status**: Basic implementation only (displays basic file/directory info)

**Planned Features**:

#### Phase 7.1: Revision Data Analysis
- [ ] Comprehensive revision directory analysis
  - Revision count, date range, average block count
  - Data quality checks (missing values, outlier detection)
  - CSV file structure validation (required column existence check)
- [ ] Block statistics summary
  - Average token length, LOC distribution
  - Function name statistics (most frequent, unique count)
  - File path distribution
- [ ] Clone pair statistics
  - Clone pair count time-series changes
  - Similarity distribution (min/max/avg)

**Estimated Effort**: 2-3 days

**Priority**: Low (track, stats, visualize are main features)

#### Phase 7.2: Data Quality Report
- [ ] Data integrity checks
  - `code_blocks.csv` and `clone_pairs.csv` integrity validation
  - block_id consistency check
  - Date continuity check
- [ ] Anomaly detection
  - Detect sudden block count changes
  - Detect blocks with abnormal token length
  - Detect abnormal clone pair count changes
- [ ] Report output (JSON/CSV/TXT)

**Estimated Effort**: 2-3 days

**Priority**: Low

**Dependencies**: Phase 7.1 completion

#### Phase 7.3: Git Repository Analysis (Optional)
- [ ] Git repository metadata analysis
  - Commit count, branch count, contributor count
  - Commit frequency time-series analysis
  - File change history statistics
- [ ] Dependency: Requires adding `gitpython` library

**Estimated Effort**: 3-4 days

**Priority**: Very Low

**Dependencies**: Phase 7.2 completion

---

## Test Status Summary

**Current Total**: 282 tests passing (100% success rate)

- Phase 1: 56 tests
- Phase 2: 67 tests (cumulative: 123)
- Phase 3: 39 tests (cumulative: 162)
- Phase 4: 75 tests (cumulative: 237)
  - track CLI: 19 tests
  - stats CLI: 11 tests
  - visualize CLI: 12 tests
  - tracking_stats: 23 tests
  - integration: 10 tests
- Phase 5.1: 8 tests (run when real data available)
- Phase 5.3: Existing tests maintained (backward compatibility 100%)
- Phase 6: 11 tests (lineage feature)

---

## Code Quality Standards

- **Ruff**: 0 errors, all checks passing
- **Test Coverage**: 80%+ (target)
- **Type Hints**: Used wherever possible (Python 3.10+ syntax)
- **Documentation**: All public APIs documented
- **Backward Compatibility**: 100% maintained across all phases

---

## Performance Optimization Details

See [docs/PERFORMANCE.md](docs/PERFORMANCE.md) for comprehensive performance analysis, benchmarks, and optimization details.

---

## Notes

- **Priority System**: High (essential features) → Medium (important improvements) → Low (nice-to-have) → Very Low (optional)
- **Estimated Effort**: Based on developer-days for a single developer
- **Test-Driven Development**: All new features must have corresponding tests before merging
- **Documentation First**: README.md and CLAUDE.md must be updated alongside code changes
