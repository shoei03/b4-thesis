import uuid

import pandas as pd


class LineageConverter:
    def __init__(self):
        pass

    def convert(self, df: pd.DataFrame) -> pd.DataFrame:
        """Convert tracking data to lineage format.

        Returns:
            DataFrame in lineage format with global_block_id assigned.
        """
        # 入力データをソートしてコピー
        df = df.sort_values(by=["revision", "block_id", "matched_block_id"]).copy()

        # 同一リビジョン内の同一block_id重複を削除（最初の行を保持）
        # TODO: そもそもmethod_tracking生成時に重複を防ぐべき
        df = df.drop_duplicates(subset=["revision", "block_id"], keep="first")

        df["global_block_id"] = None

        # リビジョンごとに処理するための準備
        unique_revisions = df["revision"].unique()

        # 前リビジョンのblock_id -> global_block_idマッピングを保持
        prev_mapping = {}

        for revision in unique_revisions:
            # 現在のリビジョンのデータを抽出
            current_mask = df["revision"] == revision
            current_indices = df[current_mask].index

            # 現リビジョンの新しいマッピングを準備
            current_mapping = {}

            for idx in current_indices:
                matched_id = df.at[idx, "matched_block_id"]
                block_id = df.at[idx, "block_id"]

                if pd.notna(matched_id) and matched_id in prev_mapping:
                    # 前リビジョンから継承
                    global_id = prev_mapping[matched_id]
                else:
                    # 新規ブロックIDを生成
                    global_id = uuid.uuid4().hex

                # global_block_idを設定
                df.at[idx, "global_block_id"] = global_id

                # 次のリビジョンのために現在のマッピングを保存
                current_mapping[block_id] = global_id

            # 次のイテレーションのためにマッピングを更新
            prev_mapping = current_mapping

        return df
