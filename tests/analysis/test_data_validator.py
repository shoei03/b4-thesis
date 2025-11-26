"""Tests for DataValidator."""

import pandas as pd
import pytest

from b4_thesis.analysis.validation import DataValidator


class TestDataValidatorCodeBlocks:
    """Test DataValidator.validate_code_blocks()."""

    @pytest.fixture
    def validator(self):
        """Create DataValidator instance."""
        return DataValidator()

    def test_validate_code_blocks_valid(self, validator):
        """Test validation with valid code_blocks DataFrame."""
        df = pd.DataFrame(
            {
                "block_id": ["block_a", "block_b"],
                "file_path": ["file1.py", "file2.py"],
                "start_line": [10, 20],
                "end_line": [20, 30],
                "function_name": ["func1", "func2"],
                "return_type": ["int", "str"],
                "parameters": ["x", "y"],
                "token_hash": ["hash1", "hash2"],
                "token_sequence": ["seq1", "seq2"],
            }
        )

        result = validator.validate_code_blocks(df)
        assert result is df  # Should return same DataFrame
        assert len(result) == 2

    def test_validate_code_blocks_missing_columns(self, validator, caplog):
        """Test validation with missing columns."""
        df = pd.DataFrame(
            {
                "block_id": ["block_a"],
                "file_path": ["file1.py"],
                # Missing start_line, end_line, etc.
            }
        )

        result = validator.validate_code_blocks(df, source="test.csv")
        assert len(result) == 1
        assert "missing required columns" in caplog.text

    def test_validate_code_blocks_invalid_line_range(self, validator, caplog):
        """Test validation with start_line > end_line."""
        df = pd.DataFrame(
            {
                "block_id": ["block_a"],
                "file_path": ["file1.py"],
                "start_line": [30],
                "end_line": [20],  # Invalid: end < start
                "function_name": ["func1"],
                "return_type": ["int"],
                "parameters": ["x"],
                "token_hash": ["hash1"],
                "token_sequence": ["seq1"],
            }
        )

        result = validator.validate_code_blocks(df)
        assert len(result) == 1
        assert "start_line > end_line" in caplog.text


class TestDataValidatorClonePairs:
    """Test DataValidator.validate_clone_pairs()."""

    @pytest.fixture
    def validator(self):
        """Create DataValidator instance."""
        return DataValidator()

    def test_validate_clone_pairs_valid(self, validator):
        """Test validation with valid clone_pairs DataFrame."""
        df = pd.DataFrame(
            {
                "block_id_1": ["block_a", "block_b"],
                "block_id_2": ["block_b", "block_c"],
                "ngram_similarity": [80, 75],
                "lcs_similarity": [85, 70],
            }
        )

        result = validator.validate_clone_pairs(df)
        assert result is df
        assert len(result) == 2

    def test_validate_clone_pairs_empty(self, validator):
        """Test validation with empty DataFrame."""
        df = pd.DataFrame(
            columns=["block_id_1", "block_id_2", "ngram_similarity", "lcs_similarity"]
        )

        result = validator.validate_clone_pairs(df)
        assert len(result) == 0

    def test_validate_clone_pairs_missing_lcs(self, validator, caplog):
        """Test validation with missing lcs_similarity (common case)."""
        df = pd.DataFrame(
            {
                "block_id_1": ["block_a"],
                "block_id_2": ["block_b"],
                "ngram_similarity": [80],
                "lcs_similarity": [None],  # Missing LCS
            }
        )

        result = validator.validate_clone_pairs(df, source="test.csv")
        assert len(result) == 1
        assert "missing values in 'lcs_similarity'" in caplog.text


class TestDataValidatorMethodTracking:
    """Test DataValidator.validate_method_tracking()."""

    @pytest.fixture
    def validator(self):
        """Create DataValidator instance."""
        return DataValidator()

    def test_validate_method_tracking_valid_survived(self, validator):
        """Test validation with valid survived method."""
        df = pd.DataFrame(
            {
                "revision": ["20250101_100000_hash1"],
                "block_id": ["block_a"],
                "function_name": ["func1"],
                "file_path": ["file1.py"],
                "start_line": [10],
                "end_line": [20],
                "loc": [11],
                "state": ["survived"],
                "state_detail": ["survived_in_clone"],
                "matched_block_id": ["block_x"],
                "match_type": ["exact"],
                "match_similarity": [100],
                "clone_count": [1],
                "clone_group_id": ["group_a"],
                "clone_group_size": [2],
                "avg_similarity_to_group": [85],
                "lifetime_revisions": [2],
                "lifetime_days": [7],
            }
        )

        result = validator.validate_method_tracking(df)
        assert result is df
        assert len(result) == 1

    def test_validate_method_tracking_valid_added(self, validator):
        """Test validation with valid added method (match fields are None)."""
        df = pd.DataFrame(
            {
                "revision": ["20250101_100000_hash1"],
                "block_id": ["block_a"],
                "function_name": ["func1"],
                "file_path": ["file1.py"],
                "start_line": [10],
                "end_line": [20],
                "loc": [11],
                "state": ["added"],
                "state_detail": ["added_as_clone"],
                "matched_block_id": [None],  # Expected to be None for added
                "match_type": [None],  # Expected to be None for added
                "match_similarity": [None],  # Expected to be None for added
                "clone_count": [1],
                "clone_group_id": ["group_a"],
                "clone_group_size": [2],
                "avg_similarity_to_group": [85],
                "lifetime_revisions": [1],
                "lifetime_days": [0],
            }
        )

        result = validator.validate_method_tracking(df)
        assert result is df
        assert len(result) == 1
        # Should NOT log warnings for match fields being None when state=added

    def test_validate_method_tracking_survived_missing_match(self, validator, caplog):
        """Test validation when survived method has missing match fields (unexpected)."""
        df = pd.DataFrame(
            {
                "revision": ["20250101_100000_hash1"],
                "block_id": ["block_a"],
                "function_name": ["func1"],
                "file_path": ["file1.py"],
                "start_line": [10],
                "end_line": [20],
                "loc": [11],
                "state": ["survived"],
                "state_detail": ["survived_in_clone"],
                "matched_block_id": [None],  # UNEXPECTED for survived
                "match_type": [None],  # UNEXPECTED for survived
                "match_similarity": [None],  # UNEXPECTED for survived
                "clone_count": [1],
                "clone_group_id": ["group_a"],
                "clone_group_size": [2],
                "avg_similarity_to_group": [85],
                "lifetime_revisions": [2],
                "lifetime_days": [7],
            }
        )

        result = validator.validate_method_tracking(df, source="test.csv")
        assert len(result) == 1
        assert "survived methods with missing matched_block_id" in caplog.text
        assert "survived methods with missing match_type" in caplog.text
        assert "survived methods with missing match_similarity" in caplog.text

    def test_validate_method_tracking_invalid_state(self, validator, caplog):
        """Test validation with invalid state value."""
        df = pd.DataFrame(
            {
                "revision": ["20250101_100000_hash1"],
                "block_id": ["block_a"],
                "function_name": ["func1"],
                "file_path": ["file1.py"],
                "start_line": [10],
                "end_line": [20],
                "loc": [11],
                "state": ["unknown_state"],  # Invalid state
                "state_detail": ["detail"],
                "matched_block_id": [None],
                "match_type": [None],
                "match_similarity": [None],
                "clone_count": [0],
                "clone_group_id": [None],
                "clone_group_size": [1],
                "avg_similarity_to_group": [None],
                "lifetime_revisions": [1],
                "lifetime_days": [0],
            }
        )

        result = validator.validate_method_tracking(df)
        assert len(result) == 1
        assert "invalid state values" in caplog.text

    def test_validate_method_tracking_similarity_out_of_range(self, validator, caplog):
        """Test validation with similarity values outside 0-100 range."""
        df = pd.DataFrame(
            {
                "revision": ["20250101_100000_hash1"],
                "block_id": ["block_a"],
                "function_name": ["func1"],
                "file_path": ["file1.py"],
                "start_line": [10],
                "end_line": [20],
                "loc": [11],
                "state": ["survived"],
                "state_detail": ["survived_in_clone"],
                "matched_block_id": ["block_x"],
                "match_type": ["exact"],
                "match_similarity": [150],  # Out of range
                "clone_count": [1],
                "clone_group_id": ["group_a"],
                "clone_group_size": [2],
                "avg_similarity_to_group": [110],  # Out of range
                "lifetime_revisions": [2],
                "lifetime_days": [7],
            }
        )

        result = validator.validate_method_tracking(df)
        assert len(result) == 1
        assert "'match_similarity' outside 0-100 range" in caplog.text
        assert "'avg_similarity_to_group' outside 0-100 range" in caplog.text
