from pathlib import Path

from b4_thesis.core.track.cross_revision_matcher import CrossRevisionMatcher
from b4_thesis.core.track.validate import validate_code_block
from b4_thesis.utils.revision_manager import RevisionManager
import pandas as pd


class MethodTracker:
    def __init__(self) -> None:
        self.revision_manager = RevisionManager()

    def _parse_token_sequence(self, token_sequences: pd.Series) -> pd.Series:
        """token_sequenceをパースしてリストに変換（インプレース）"""
        return token_sequences.str[1:-1].str.split(";").apply(lambda x: [int(i) for i in x])

    def track(
        self,
        data_dir: Path,
        similarity_threshold: float = 0.7,
        n_gram_size: int = 5,
        filter_threshold: float = 0.1,
    ) -> pd.DataFrame:
        """Track methods across revisions.

        Args:
            data_dir: Directory containing revision subdirectories
            similarity_threshold: LCS similarity threshold (0.0-1.0, default: 0.7)
            n_gram_size: Size of N-grams for indexing (default: 5)
            filter_threshold: N-gram overlap threshold for filtration (0.0-1.0, default: 0.1)

        Returns:
            DataFrame with method tracking results
        """
        # Initialize matcher with user-specified parameters
        cross_revision_matcher = CrossRevisionMatcher(
            n_gram_size=n_gram_size,
            filter_threshold=filter_threshold,
            verify_threshold=similarity_threshold,
        )

        revisions = self.revision_manager.get_revisions(data_dir)

        # 全結果を保存するリスト
        all_matches: list[pd.DataFrame] = []

        # 最初のリビジョンをロード
        prev_revision = revisions[0]
        prev_code_blocks, _ = self.revision_manager.load_revision_data(prev_revision)
        try:
            validate_code_block(prev_code_blocks)
        except Exception as e:
            print(f"Validation failed for revision {prev_revision.timestamp}: {e}")

        prev_code_blocks["token_sequence"] = self._parse_token_sequence(
            prev_code_blocks["token_sequence"]
        )

        # 2番目以降のリビジョンを順にずらして処理
        for curr_revision in revisions[1:]:
            curr_code_blocks, _ = self.revision_manager.load_revision_data(curr_revision)
            try:
                validate_code_block(curr_code_blocks)
            except Exception as e:
                print(f"Validation failed for revision {curr_revision.timestamp}: {e}")

            curr_code_blocks["token_sequence"] = self._parse_token_sequence(
                curr_code_blocks["token_sequence"]
            )

            prev_code_blocks["revision"] = prev_revision.timestamp
            curr_code_blocks["revision"] = curr_revision.timestamp

            # Convert DataFrames to list of dicts for NIL-based matching
            source_blocks = prev_code_blocks.to_dict("records")
            target_blocks = curr_code_blocks.to_dict("records")

            print(
                f"Revision {prev_revision.timestamp} -> {curr_revision.timestamp}: "
                f"{len(source_blocks)}×{len(target_blocks)} blocks to match"
            )

            # Use NIL-based cross-revision matching
            match_results = cross_revision_matcher.match_revisions(source_blocks, target_blocks)

            # Convert match results to DataFrame
            if match_results:
                matches = pd.DataFrame(match_results)
            else:
                matches = pd.DataFrame()

            # Append matches to results
            if len(matches) > 0:
                all_matches.append(matches)

            # 次のイテレーションの準備
            prev_revision = curr_revision
            prev_code_blocks = curr_code_blocks.drop("revision", axis=1)

        if len(all_matches) == 0:
            return pd.DataFrame()

        return pd.concat(all_matches, ignore_index=True)
