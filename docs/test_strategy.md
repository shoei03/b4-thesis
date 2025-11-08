# メソッド追跡分析 テスト戦略書

## 概要

このドキュメントでは、メソッド削除・クローングループ追跡分析のテスト戦略、テストケース、テストデータ設計を定義します。

**テスト駆動開発（TDD）アプローチ**を採用し、実装前にテストを作成します。

## テストピラミッド

```
        ┌─────────────────┐
        │   E2E Tests     │  ← 少数、実際のデータで統合テスト
        │   (5%)          │
        ├─────────────────┤
        │                 │
        │ Integration     │  ← 中程度、複数コンポーネント連携
        │ Tests (25%)     │
        │                 │
        ├─────────────────┤
        │                 │
        │                 │
        │  Unit Tests     │  ← 大多数、各関数・クラスの詳細テスト
        │  (70%)          │
        │                 │
        │                 │
        └─────────────────┘
```

## テストデータ設計

### フィクスチャ構造

```
tests/fixtures/sample_revisions/
├── 20250101_100000_hash1/
│   ├── clone_pairs.csv
│   └── code_blocks.csv
├── 20250101_110000_hash2/
│   ├── clone_pairs.csv
│   └── code_blocks.csv
├── 20250101_120000_hash3/
│   ├── clone_pairs.csv
│   └── code_blocks.csv
└── README.md  # フィクスチャの説明
```

### シナリオベーステストデータ

各シナリオは特定の追跡パターンをテストするために設計されます。

#### シナリオ1: 基本的なメソッド状態遷移

**Revision 1** (20250101_100000):
```csv
# code_blocks.csv
block_id,file_path,start_line,end_line,function_name,return_type,parameters,token_hash,token_sequence
block_a,src/util.py,10,20,calculate,int,x:int,hash_a,[1;2;3;4;5]
block_b,src/util.py,30,40,process,void,data:str,hash_b,[10;11;12;13]
block_c,src/math.py,50,60,compute,float,val:float,hash_c,[20;21;22]

# clone_pairs.csv (空 - クローンなし)
block_id_1,block_id_2,ngram_similarity,lcs_similarity
```

**Revision 2** (20250101_110000):
```csv
# code_blocks.csv
block_id,file_path,start_line,end_line,function_name,return_type,parameters,token_hash,token_sequence
block_a2,src/util.py,10,20,calculate,int,x:int,hash_a,[1;2;3;4;5]
block_b2,src/util.py,30,42,process_data,void,data:str,hash_b_mod,[10;11;12;13;14]
block_d,src/feature.py,100,110,new_func,int,n:int,hash_d,[30;31;32]

# clone_pairs.csv (空)
block_id_1,block_id_2,ngram_similarity,lcs_similarity
```

**期待される追跡結果**:
- `block_a` → `block_a2`: survived_unchanged (token_hash一致)
- `block_b` → `block_b2`: survived_modified (類似度マッチ、token_hash変更)
- `block_c` → なし: deleted_isolated (クローンなしで削除)
- `block_d`: added_isolated (新規追加、クローンなし)

#### シナリオ2: クローングループの形成と消滅

**Revision 1** (20250101_100000):
```csv
# code_blocks.csv
block_id,file_path,start_line,end_line,function_name,return_type,parameters,token_hash,token_sequence
block_x,src/a.py,10,20,func_x,int,n:int,hash_x,[100;101;102;103]
block_y,src/b.py,30,40,func_y,int,m:int,hash_y,[100;101;102;104]
block_z,src/c.py,50,60,func_z,int,p:int,hash_z,[100;101;102;105]

# clone_pairs.csv
block_id_1,block_id_2,ngram_similarity,lcs_similarity
block_x,block_y,85,
block_y,block_z,80,
block_x,block_z,82,
```

**期待されるグループ**:
- group_x: [block_x, block_y, block_z] (サイズ=3)

**Revision 2** (20250101_110000):
```csv
# code_blocks.csv
block_id,file_path,start_line,end_line,function_name,return_type,parameters,token_hash,token_sequence
block_x2,src/a.py,10,20,func_x,int,n:int,hash_x,[100;101;102;103]

# clone_pairs.csv (空 - クローンなし)
block_id_1,block_id_2,ngram_similarity,lcs_similarity
```

**期待される追跡結果**:
- `block_x` → `block_x2`: survived_clone_lost (グループから孤立)
- `block_y` → なし: deleted_from_group
- `block_z` → なし: deleted_last_member (グループ最後のメンバー)
- group_x: dissolved (グループ消滅)

#### シナリオ3: グループの成長

**Revision 1**:
```csv
# clone_pairs.csv
block_id_1,block_id_2,ngram_similarity,lcs_similarity
block_1,block_2,75,
```
グループ: [block_1, block_2]

**Revision 2**:
```csv
# clone_pairs.csv
block_id_1,block_id_2,ngram_similarity,lcs_similarity
block_1,block_2,75,
block_1,block_3,78,
block_2,block_3,76,
```
グループ: [block_1, block_2, block_3]

**期待される結果**:
- グループ状態: grown
- member_added: 1
- member_removed: 0

#### シナリオ4: グループの分裂

**Revision 1**:
```csv
# グループ: [A, B, C, D] (全て相互に類似)
```

**Revision 2**:
```csv
# グループ1: [A, B]
# グループ2: [C, D]
```

**期待される結果**:
- 元グループ: split
- 2つの新グループ: born

#### シナリオ5: グループの統合

**Revision 1**:
```csv
# グループ1: [A, B]
# グループ2: [C, D]
```

**Revision 2**:
```csv
# グループ: [A, B, C, D]
```

**期待される結果**:
- 2つの旧グループ: merged
- 新グループ: born

#### シナリオ6: 類似度マッチングのエッジケース

**Revision 1**:
```csv
block_m,src/test.py,10,20,method_m,void,,hash_m,[50;51;52;53;54;55]
```

**Revision 2**:
```csv
# 3つの候補（異なる類似度）
block_m1,src/test.py,10,20,method_m,void,,hash_m1,[50;51;52;53;54;99]    # 類似度: 85
block_m2,src/test.py,30,40,method_m_v2,void,,hash_m2,[50;51;52;53;99;99]  # 類似度: 72
block_m3,src/test2.py,50,60,method_m_copy,void,,hash_m3,[50;51;52;99;99;99] # 類似度: 65
```

**期待される結果**:
- `block_m` → `block_m1` (最高類似度=85を選択)
- `block_m2`, `block_m3` は候補から除外

## ユニットテスト詳細

### 1. UnionFind (test_union_find.py)

```python
import pytest
from b4_thesis.analysis.union_find import UnionFind

class TestUnionFind:
    """Test UnionFind data structure."""

    def test_initialization(self):
        """Test empty UnionFind creation."""
        uf = UnionFind()
        assert uf.size() == 0
        assert uf.num_groups() == 0

    def test_single_element(self):
        """Test single element behavior."""
        uf = UnionFind()
        root = uf.find("A")
        assert root == "A"
        assert uf.size() == 1
        assert uf.num_groups() == 1

    def test_union_two_elements(self):
        """Test union of two elements."""
        uf = UnionFind()
        uf.union("A", "B")
        assert uf.is_connected("A", "B")
        assert uf.num_groups() == 1

    def test_multiple_groups(self):
        """Test formation of multiple groups."""
        uf = UnionFind()
        uf.union("A", "B")
        uf.union("C", "D")
        uf.union("E", "F")

        assert uf.is_connected("A", "B")
        assert uf.is_connected("C", "D")
        assert uf.is_connected("E", "F")
        assert not uf.is_connected("A", "C")
        assert uf.num_groups() == 3

    def test_transitive_union(self):
        """Test transitive property: union(A,B), union(B,C) -> A~C."""
        uf = UnionFind()
        uf.union("A", "B")
        uf.union("B", "C")
        assert uf.is_connected("A", "C")

    def test_path_compression(self):
        """Test path compression optimization."""
        uf = UnionFind()
        # Create chain: A -> B -> C -> D
        uf.union("A", "B")
        uf.union("B", "C")
        uf.union("C", "D")

        # After find(A), path should be compressed
        root = uf.find("A")
        # All should point to same root
        assert uf.find("B") == root
        assert uf.find("C") == root
        assert uf.find("D") == root

    def test_get_groups(self):
        """Test get_groups method returns correct structure."""
        uf = UnionFind()
        uf.union("A", "B")
        uf.union("C", "D")
        uf.union("B", "E")  # A-B-E group

        groups = uf.get_groups()
        assert len(groups) == 2

        # Find group with A
        a_root = uf.find("A")
        assert set(groups[a_root]) == {"A", "B", "E"}

        # Find group with C
        c_root = uf.find("C")
        assert set(groups[c_root]) == {"C", "D"}

    def test_large_group(self):
        """Test with larger number of elements."""
        uf = UnionFind()
        # Create group of 100 elements
        for i in range(1, 100):
            uf.union(f"elem_{0}", f"elem_{i}")

        assert uf.num_groups() == 1
        assert uf.size() == 100

        groups = uf.get_groups()
        assert len(groups) == 1
        group_members = list(groups.values())[0]
        assert len(group_members) == 100
```

### 2. SimilarityCalculator (test_similarity.py への追加)

```python
import pytest
from b4_thesis.analysis.similarity import (
    calculate_similarity,
    parse_token_sequence
)

class TestCalculateSimilarity:
    """Test cross-revision similarity calculation."""

    def test_identical_sequences(self):
        """Test 100% similarity for identical sequences."""
        seq1 = "[1;2;3;4;5]"
        seq2 = "[1;2;3;4;5]"
        assert calculate_similarity(seq1, seq2) == 100

    def test_high_similarity_ngram_only(self):
        """Test N-gram ≥ 70 (LCS should be skipped)."""
        # Create sequences with high N-gram similarity
        seq1 = "[1;2;3;4;5;6;7;8;9;10]"
        seq2 = "[1;2;3;4;5;6;7;8;9;99]"  # Only last token different

        similarity = calculate_similarity(seq1, seq2)
        assert similarity >= 70
        # Verify LCS was not called (by checking performance)

    def test_low_similarity_uses_lcs(self):
        """Test N-gram < 70 triggers LCS calculation."""
        seq1 = "[1;2;3;4;5]"
        seq2 = "[10;20;30;4;5]"  # Low N-gram similarity

        similarity = calculate_similarity(seq1, seq2)
        assert 0 <= similarity < 70

    def test_completely_different(self):
        """Test 0% similarity for completely different sequences."""
        seq1 = "[1;2;3;4;5]"
        seq2 = "[10;20;30;40;50]"
        similarity = calculate_similarity(seq1, seq2)
        assert similarity == 0 or similarity < 50  # Very low

    def test_empty_sequences(self):
        """Test handling of empty sequences."""
        with pytest.raises(ValueError):
            calculate_similarity("[]", "[1;2;3]")

    def test_malformed_sequence(self):
        """Test handling of malformed token sequences."""
        with pytest.raises(ValueError):
            calculate_similarity("invalid", "[1;2;3]")

    def test_partial_overlap(self):
        """Test sequences with partial overlap."""
        seq1 = "[1;2;3;4;5]"
        seq2 = "[3;4;5;6;7]"  # 3 tokens overlap
        similarity = calculate_similarity(seq1, seq2)
        assert 40 <= similarity <= 80
```

### 3. MethodMatcher (test_method_matcher.py)

```python
import pytest
import pandas as pd
from b4_thesis.analysis.method_matcher import (
    MethodMatcher,
    MatchType,
    MethodMatch
)

class TestMethodMatcher:
    """Test method matching between revisions."""

    @pytest.fixture
    def sample_code_blocks_old(self):
        """Sample code blocks from old revision."""
        return pd.DataFrame({
            'block_id': ['block_a', 'block_b', 'block_c'],
            'token_hash': ['hash_1', 'hash_2', 'hash_3'],
            'token_sequence': ['[1;2;3]', '[10;11;12]', '[20;21;22]'],
            'function_name': ['func_a', 'func_b', 'func_c']
        })

    @pytest.fixture
    def sample_code_blocks_new_unchanged(self):
        """Sample code blocks with one unchanged method."""
        return pd.DataFrame({
            'block_id': ['block_a2', 'block_d'],
            'token_hash': ['hash_1', 'hash_4'],  # block_a2 has same hash
            'token_sequence': ['[1;2;3]', '[30;31;32]'],
            'function_name': ['func_a', 'func_d']
        })

    def test_phase1_token_hash_match(self, sample_code_blocks_old,
                                     sample_code_blocks_new_unchanged):
        """Test Phase 1: token_hash matching."""
        matcher = MethodMatcher(similarity_threshold=70)
        matches = matcher.match_revisions(
            sample_code_blocks_old,
            sample_code_blocks_new_unchanged
        )

        # block_a should match block_a2 via token_hash
        assert 'block_a' in matches
        match = matches['block_a']
        assert match.target_block_id == 'block_a2'
        assert match.match_type == MatchType.TOKEN_HASH
        assert match.similarity is None

    def test_phase2_similarity_match(self):
        """Test Phase 2: similarity-based matching."""
        code_blocks_old = pd.DataFrame({
            'block_id': ['block_x'],
            'token_hash': ['hash_x'],
            'token_sequence': ['[1;2;3;4;5]'],
            'function_name': ['func_x']
        })

        code_blocks_new = pd.DataFrame({
            'block_id': ['block_y'],
            'token_hash': ['hash_y'],  # Different hash
            'token_sequence': ['[1;2;3;4;99]'],  # High similarity
            'function_name': ['func_x']
        })

        matcher = MethodMatcher(similarity_threshold=70)
        matches = matcher.match_revisions(code_blocks_old, code_blocks_new)

        assert 'block_x' in matches
        match = matches['block_x']
        assert match.target_block_id == 'block_y'
        assert match.match_type == MatchType.SIMILARITY
        assert match.similarity >= 70

    def test_no_match_below_threshold(self):
        """Test no match when similarity is below threshold."""
        code_blocks_old = pd.DataFrame({
            'block_id': ['block_x'],
            'token_hash': ['hash_x'],
            'token_sequence': ['[1;2;3;4;5]'],
            'function_name': ['func_x']
        })

        code_blocks_new = pd.DataFrame({
            'block_id': ['block_y'],
            'token_hash': ['hash_y'],
            'token_sequence': ['[10;20;30;40;50]'],  # Completely different
            'function_name': ['func_y']
        })

        matcher = MethodMatcher(similarity_threshold=70)
        matches = matcher.match_revisions(code_blocks_old, code_blocks_new)

        assert 'block_x' in matches
        match = matches['block_x']
        assert match.target_block_id is None
        assert match.match_type == MatchType.NONE

    def test_multiple_candidates_selects_best(self):
        """Test selection of highest similarity when multiple candidates."""
        code_blocks_old = pd.DataFrame({
            'block_id': ['block_m'],
            'token_hash': ['hash_m'],
            'token_sequence': ['[1;2;3;4;5]'],
            'function_name': ['method_m']
        })

        code_blocks_new = pd.DataFrame({
            'block_id': ['block_m1', 'block_m2', 'block_m3'],
            'token_hash': ['hash_m1', 'hash_m2', 'hash_m3'],
            'token_sequence': [
                '[1;2;3;4;99]',   # High similarity (80%)
                '[1;2;3;99;99]',  # Medium similarity (60%)
                '[1;2;99;99;99]'  # Low similarity (40%)
            ],
            'function_name': ['method_m1', 'method_m2', 'method_m3']
        })

        matcher = MethodMatcher(similarity_threshold=70)
        matches = matcher.match_revisions(code_blocks_old, code_blocks_new)

        # Should select block_m1 (highest similarity)
        assert matches['block_m'].target_block_id == 'block_m1'

    def test_bidirectional_consistency(self):
        """Test bidirectional matching consistency."""
        # This test verifies that forward and backward matches are consistent
        # Implementation details to be defined during implementation
        pass
```

### 4. GroupDetector (test_group_detector.py)

```python
import pytest
import pandas as pd
from b4_thesis.analysis.group_detector import GroupDetector, CloneGroup

class TestGroupDetector:
    """Test clone group detection."""

    def test_single_group_detection(self):
        """Test detection of a single clone group."""
        code_blocks = pd.DataFrame({
            'block_id': ['A', 'B', 'C']
        })

        clone_pairs = pd.DataFrame({
            'block_id_1': ['A', 'B', 'A'],
            'block_id_2': ['B', 'C', 'C'],
            'ngram_similarity': [80, 85, 75],
            'lcs_similarity': [None, None, None]
        })

        detector = GroupDetector(similarity_threshold=70)
        groups = detector.detect_groups(code_blocks, clone_pairs)

        assert len(groups) == 1
        group = list(groups.values())[0]
        assert set(group.members) == {'A', 'B', 'C'}
        assert group.size == 3
        assert group.is_clone is True

    def test_multiple_groups(self):
        """Test detection of multiple separate groups."""
        code_blocks = pd.DataFrame({
            'block_id': ['A', 'B', 'C', 'D', 'E']
        })

        clone_pairs = pd.DataFrame({
            'block_id_1': ['A', 'C'],
            'block_id_2': ['B', 'D'],
            'ngram_similarity': [80, 85],
            'lcs_similarity': [None, None]
        })

        detector = GroupDetector(similarity_threshold=70)
        groups = detector.detect_groups(code_blocks, clone_pairs)

        assert len(groups) == 3  # [A,B], [C,D], [E]

        # Find groups
        group_sizes = sorted([g.size for g in groups.values()])
        assert group_sizes == [1, 2, 2]

    def test_isolated_methods(self):
        """Test methods with no clones (isolated)."""
        code_blocks = pd.DataFrame({
            'block_id': ['A', 'B', 'C']
        })

        clone_pairs = pd.DataFrame({
            'block_id_1': [],
            'block_id_2': [],
            'ngram_similarity': [],
            'lcs_similarity': []
        })

        detector = GroupDetector(similarity_threshold=70)
        groups = detector.detect_groups(code_blocks, clone_pairs)

        assert len(groups) == 3
        for group in groups.values():
            assert group.size == 1
            assert group.is_clone is False

    def test_threshold_boundary(self):
        """Test similarity threshold boundary."""
        code_blocks = pd.DataFrame({
            'block_id': ['A', 'B', 'C']
        })

        clone_pairs = pd.DataFrame({
            'block_id_1': ['A', 'B'],
            'block_id_2': ['B', 'C'],
            'ngram_similarity': [70, 69],  # One at threshold, one below
            'lcs_similarity': [None, None]
        })

        detector = GroupDetector(similarity_threshold=70)
        groups = detector.detect_groups(code_blocks, clone_pairs)

        # A-B should be grouped, C should be isolated
        assert len(groups) == 2

    def test_group_metrics(self):
        """Test calculation of group metrics."""
        code_blocks = pd.DataFrame({
            'block_id': ['A', 'B', 'C']
        })

        clone_pairs = pd.DataFrame({
            'block_id_1': ['A', 'B', 'A'],
            'block_id_2': ['B', 'C', 'C'],
            'ngram_similarity': [80, 90, 70],
            'lcs_similarity': [None, None, None]
        })

        detector = GroupDetector(similarity_threshold=70)
        groups = detector.detect_groups(code_blocks, clone_pairs)

        group = list(groups.values())[0]
        assert group.avg_similarity == 80.0  # (80+90+70)/3
        assert group.min_similarity == 70
        assert group.max_similarity == 90
        assert group.density == 1.0  # Fully connected (3 edges for 3 nodes)
```

### 5. StateClassifier (test_state_classifier.py)

```python
import pytest
from b4_thesis.analysis.state_classifier import (
    StateClassifier,
    MethodState,
    MethodStateDetail,
    GroupState
)
from b4_thesis.analysis.method_matcher import MethodMatch, MatchType
from b4_thesis.analysis.group_detector import CloneGroup

class TestStateClassifier:
    """Test method and group state classification."""

    @pytest.fixture
    def classifier(self):
        return StateClassifier()

    # Method State Tests
    def test_deleted_isolated(self, classifier):
        """Test deleted_isolated classification."""
        match = MethodMatch("block_a", None, MatchType.NONE, None)
        state, detail = classifier.classify_method_state(
            "block_a", match, group_old=None, group_new=None
        )
        assert state == MethodState.DELETED
        assert detail == MethodStateDetail.DELETED_ISOLATED

    def test_deleted_from_group(self, classifier):
        """Test deleted_from_group classification."""
        group_old = CloneGroup("group_1", ["block_a", "block_b"], {})
        match = MethodMatch("block_a", None, MatchType.NONE, None)
        state, detail = classifier.classify_method_state(
            "block_a", match, group_old=group_old, group_new=None
        )
        assert state == MethodState.DELETED
        assert detail == MethodStateDetail.DELETED_FROM_GROUP

    def test_survived_unchanged(self, classifier):
        """Test survived_unchanged classification."""
        match = MethodMatch("block_a", "block_a2", MatchType.TOKEN_HASH, None)
        state, detail = classifier.classify_method_state(
            "block_a", match, group_old=None, group_new=None
        )
        assert state == MethodState.SURVIVED
        assert detail == MethodStateDetail.SURVIVED_UNCHANGED

    def test_survived_modified(self, classifier):
        """Test survived_modified classification."""
        match = MethodMatch("block_a", "block_a2", MatchType.SIMILARITY, 85)
        state, detail = classifier.classify_method_state(
            "block_a", match, group_old=None, group_new=None
        )
        assert state == MethodState.SURVIVED
        assert detail == MethodStateDetail.SURVIVED_MODIFIED

    def test_survived_clone_gained(self, classifier):
        """Test survived_clone_gained classification."""
        match = MethodMatch("block_a", "block_a2", MatchType.TOKEN_HASH, None)
        group_new = CloneGroup("group_1", ["block_a2", "block_b"], {})
        state, detail = classifier.classify_method_state(
            "block_a", match, group_old=None, group_new=group_new
        )
        assert state == MethodState.SURVIVED
        assert detail == MethodStateDetail.SURVIVED_CLONE_GAINED

    def test_added_isolated(self, classifier):
        """Test added_isolated classification."""
        # New method in new revision (no match from old revision)
        # This is tested from the new revision perspective
        pass  # Details during implementation

    # Group State Tests
    def test_group_continued(self, classifier):
        """Test continued group state."""
        from b4_thesis.analysis.group_matcher import GroupMatch
        match = GroupMatch("group_old", "group_new", 5, 0.8, 6, 6)
        state = classifier.classify_group_state(match)
        assert state == GroupState.CONTINUED

    def test_group_grown(self, classifier):
        """Test grown group state (>10% increase)."""
        from b4_thesis.analysis.group_matcher import GroupMatch
        match = GroupMatch("group_old", "group_new", 8, 0.8, 10, 12)
        state = classifier.classify_group_state(match)
        assert state == GroupState.GROWN

    def test_group_shrunk(self, classifier):
        """Test shrunk group state (>10% decrease)."""
        from b4_thesis.analysis.group_matcher import GroupMatch
        match = GroupMatch("group_old", "group_new", 5, 0.8, 10, 8)
        state = classifier.classify_group_state(match)
        assert state == GroupState.SHRUNK

    def test_group_dissolved(self, classifier):
        """Test dissolved group state (no match)."""
        from b4_thesis.analysis.group_matcher import GroupMatch
        match = GroupMatch("group_old", None, 0, 0.0, 5, None)
        state = classifier.classify_group_state(match)
        assert state == GroupState.DISSOLVED

    def test_group_split(self, classifier):
        """Test split group state."""
        from b4_thesis.analysis.group_matcher import GroupMatch
        match = GroupMatch("group_old", "group_new", 3, 0.5, 6, 3)
        state = classifier.classify_group_state(match, is_split=True)
        assert state == GroupState.SPLIT

    def test_group_merged(self, classifier):
        """Test merged group state."""
        from b4_thesis.analysis.group_matcher import GroupMatch
        match = GroupMatch("group_old", "group_new", 3, 0.5, 3, 6)
        state = classifier.classify_group_state(match, is_merged=True)
        assert state == GroupState.MERGED
```

## 統合テスト

### Integration Test 1: End-to-End Method Tracking

```python
import pytest
from pathlib import Path
from datetime import datetime
from b4_thesis.analysis.method_tracker import MethodTracker

class TestMethodTrackerIntegration:
    """Integration tests for MethodTracker."""

    @pytest.fixture
    def sample_data_dir(self):
        """Path to sample test data."""
        return Path("tests/fixtures/sample_revisions")

    def test_track_across_two_revisions(self, sample_data_dir):
        """Test tracking methods across two consecutive revisions."""
        tracker = MethodTracker(sample_data_dir, similarity_threshold=70)
        results = tracker.track(
            start_date=datetime(2025, 1, 1, 10, 0, 0),
            end_date=datetime(2025, 1, 1, 11, 0, 0)
        )

        # Verify DataFrame structure
        expected_columns = [
            'revision', 'block_id', 'function_name', 'file_path',
            'start_line', 'end_line', 'loc', 'state', 'state_detail',
            'matched_block_id', 'match_type', 'match_similarity',
            'clone_count', 'clone_group_id', 'clone_group_size',
            'lifetime_revisions', 'lifetime_days'
        ]
        assert list(results.columns) == expected_columns

        # Verify expected state transitions (based on fixture data)
        deleted = results[results['state'] == 'deleted']
        survived = results[results['state'] == 'survived']
        added = results[results['state'] == 'added']

        assert len(deleted) > 0
        assert len(survived) > 0
        assert len(added) > 0

    def test_lifetime_calculation(self, sample_data_dir):
        """Test lifetime calculation across multiple revisions."""
        tracker = MethodTracker(sample_data_dir, similarity_threshold=70)
        results = tracker.track(
            start_date=datetime(2025, 1, 1, 10, 0, 0),
            end_date=datetime(2025, 1, 1, 12, 0, 0)
        )

        # Find a method that survived across all revisions
        survived = results[
            (results['state'] == 'survived') &
            (results['lifetime_revisions'] >= 2)
        ]

        assert len(survived) > 0
        # Verify lifetime_days is reasonable
        assert survived.iloc[0]['lifetime_days'] >= 0
```

### Integration Test 2: End-to-End Group Tracking

```python
class TestCloneGroupTrackerIntegration:
    """Integration tests for CloneGroupTracker."""

    def test_track_group_evolution(self, sample_data_dir):
        """Test tracking clone group evolution."""
        from b4_thesis.analysis.clone_group_tracker import CloneGroupTracker

        tracker = CloneGroupTracker(
            sample_data_dir,
            similarity_threshold=70,
            overlap_threshold=0.5
        )

        group_results, membership_results = tracker.track(
            start_date=datetime(2025, 1, 1, 10, 0, 0),
            end_date=datetime(2025, 1, 1, 12, 0, 0)
        )

        # Verify group_tracking structure
        assert 'state' in group_results.columns
        assert 'member_count' in group_results.columns
        assert 'avg_similarity' in group_results.columns

        # Verify membership structure
        assert 'is_clone' in membership_results.columns
        assert 'block_id' in membership_results.columns

        # Verify group states
        states = group_results['state'].unique()
        possible_states = {'continued', 'grown', 'shrunk', 'split',
                          'merged', 'dissolved', 'born'}
        assert set(states).issubset(possible_states)
```

## CLIテスト

```python
from click.testing import CliRunner
from b4_thesis.commands.track import track

class TestTrackCommands:
    """Test CLI commands for tracking."""

    def test_track_methods_command(self, tmp_path):
        """Test track methods CLI command."""
        runner = CliRunner()
        output_file = tmp_path / "method_tracking.csv"

        result = runner.invoke(track, [
            'methods',
            'tests/fixtures/sample_revisions',
            '--start-date', '20250101',
            '--end-date', '20250101',
            '--output', str(output_file)
        ])

        assert result.exit_code == 0
        assert output_file.exists()

    def test_track_all_command_with_summary(self, tmp_path):
        """Test track all command with summary display."""
        runner = CliRunner()
        output_dir = tmp_path / "results"

        result = runner.invoke(track, [
            'all',
            'tests/fixtures/sample_revisions',
            '--output-dir', str(output_dir),
            '--show-summary'
        ])

        assert result.exit_code == 0
        assert "Method Tracking Summary" in result.output
        assert "Clone Group Summary" in result.output
```

## テスト実行計画

### フェーズ1: ユニットテスト（実装前）

```bash
# 各モジュールのテストを作成（実装前）
# TDD: テストを先に書く

# 実装なしでテストを実行（すべて失敗することを確認）
pytest tests/analysis/test_union_find.py -v  # All FAIL (expected)
```

### フェーズ2: 実装とテスト（反復）

```bash
# UnionFind実装 → テスト通過
pytest tests/analysis/test_union_find.py -v  # All PASS

# SimilarityCalculator拡張 → テスト通過
pytest tests/analysis/test_similarity.py -v

# 以降、各モジュールで同様に反復
```

### フェーズ3: 統合テスト

```bash
# 統合テスト実行
pytest tests/analysis/test_method_tracker.py -v
pytest tests/analysis/test_clone_group_tracker.py -v
```

### フェーズ4: E2Eテスト

```bash
# CLIテスト
pytest tests/commands/test_track.py -v

# 全テストスイート実行
pytest tests/ -v --cov=b4_thesis --cov-report=html
```

## カバレッジ目標

- **ユニットテスト**: 90%以上
- **統合テスト**: 80%以上
- **全体**: 85%以上

```bash
# カバレッジレポート生成
pytest tests/ --cov=b4_thesis --cov-report=term-missing --cov-report=html

# HTMLレポート閲覧
open htmlcov/index.html
```

## CI/CD統合

GitHubアクションで自動テスト実行（既存のworkflowに追加）:

```yaml
# .github/workflows/test.yml (既存ファイルへの追加)
- name: Run tracking analysis tests
  run: |
    pytest tests/analysis/test_union_find.py -v
    pytest tests/analysis/test_method_matcher.py -v
    pytest tests/analysis/test_group_detector.py -v
    pytest tests/commands/test_track.py -v
```

---

**作成日**: 2025-11-08
**バージョン**: 1.0.0
