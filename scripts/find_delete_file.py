import pandas as pd

method_lineage_labeled = pd.read_csv("./output/versions/method_lineage_labeled.csv", usecols=["revision", "global_block_id", "file_path"])
ground_truth = pd.read_csv("./output/versions/method_lineage/ground_truth.csv", usecols=["global_block_id", "revision", "state_with_clone"])
deleted_file_path = pd.read_csv("./output/versions/method_lineage/deleted_files.csv", usecols=["File Name"])

print(f"method_lineage_labeled rows: {len(method_lineage_labeled)}")
print(f"ground_truth rows: {len(ground_truth)}")
print(f"deleted_file_path rows: {len(deleted_file_path)}")

df = method_lineage_labeled.merge(ground_truth, on=["revision", "global_block_id"], how="inner")

print(f"Total rows after merge: {len(df)}")

# file_pathから先頭の/app/Repos/pandasを削除
df["file_path"] = df["file_path"].str.replace("/app/Repos/pandas/", "", regex=False)

# deleted_file_pathのFile Nameをセットに変換（高速な検索のため）
deleted_files_set = set(deleted_file_path["File Name"])

# state_with_cloneがall_deletedの行で、file_pathがdeleted_file_pathに含まれているかを判定
df["file_deleted"] = (df["state_with_clone"] == "all_deleted") & (df["file_path"].isin(deleted_files_set))

# file_deletedがTrueの行数 / state_with_cloneがall_deletedの行数
file_deleted_count = df["file_deleted"].sum()
all_deleted_count = (df["state_with_clone"] == "all_deleted").sum()
ratio = file_deleted_count / all_deleted_count

print(f"file_deleted: {file_deleted_count}")
print(f"all_deleted: {all_deleted_count}")
print(f"ratio: {ratio:.4f}")