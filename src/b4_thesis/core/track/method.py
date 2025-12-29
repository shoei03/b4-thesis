from pathlib import Path
import pandas as pd

from b4_thesis.utils.revision_manager import RevisionManager
from b4_thesis.core.track.validate import validate_code_block
from b4_thesis.core.track.similarity import NILCloneDetector


class MethodTracker:
    def __init__(self) -> None:
        self.revision_manager = RevisionManager()
        self.clone_detector = NILCloneDetector()

    def _parse_token_sequence(self, token_sequences: pd.Series) -> pd.Series:
        """token_sequenceをパースしてリストに変換（インプレース）"""
        return token_sequences.str[1:-1].str.split(";").apply(lambda x: [int(i) for i in x])

    def _calc_similarity_placeholder(self, seq1: list[int], seq2: list[int]) -> float:
        """類似度計算の仮実装"""
        return self.clone_detector._compute_lcs_length_hunt_szymanski(seq1, seq2)

    def track(self, data_dir: Path, similarity_threshold: float = 70.0) -> pd.DataFrame:
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

            # クロス結合で全ペアを生成
            prev_code_blocks["_merge_key"] = 1
            curr_code_blocks["_merge_key"] = 1

            pairs = prev_code_blocks.merge(
                curr_code_blocks, on="_merge_key", suffixes=("_prev", "_curr")
            )

            # 不要な列を削除
            pairs = pairs.drop("_merge_key", axis=1)

            print(
                f"Revision {prev_revision.timestamp} -> {curr_revision.timestamp}: "
                f"{len(pairs)} pairs to compare"
            )

            # 類似度を計算
            similarities: list[float] = []
            for _, row in pairs.iterrows():
                similarity: float = self._calc_similarity_placeholder(
                    row["token_sequence_prev"], row["token_sequence_curr"]
                )
                similarities.append(similarity)

            pairs["similarity"] = similarities

            # 閾値でフィルタリング
            matches: pd.DataFrame = pairs[pairs["similarity"] >= similarity_threshold].copy()

            print(f"  {len(matches)} matches found (similarity >= {similarity_threshold})")

            # 結果を整形
            if len(matches) > 0:
                result: pd.DataFrame = pd.DataFrame(
                    {
                        "prev_revision": matches["revision_prev"],
                        "curr_revision": matches["revision_curr"],
                        "prev_file_path": matches["file_path_prev"],
                        "prev_function_name": matches["function_name_prev"],
                        "prev_block_id": matches["block_id_prev"],
                        "curr_file_path": matches["file_path_curr"],
                        "curr_function_name": matches["function_name_curr"],
                        "curr_block_id": matches["block_id_curr"],
                        "similarity": matches["similarity"],
                    }
                )

                all_matches.append(result)

            # 次のイテレーションの準備
            prev_revision = curr_revision
            prev_code_blocks = curr_code_blocks.drop("revision", axis=1)

        if len(all_matches) == 0:
            return pd.DataFrame()

        return pd.concat(all_matches, ignore_index=True)
