import click
import pandas as pd
import pingouin as pg
from rich.console import Console
from rich.table import Table

console = Console()


@click.group()
def test_analysis():
    pass


@test_analysis.command()
@click.option(
    "--input-file",
    type=click.Path(exists=True, file_okay=True, dir_okay=False),
    default="./output/versions/nil/6_class_delete.csv",
    help="Input CSV file containing test analysis data",
)
def deleted_rate(input_file):
    df = pd.read_csv(input_file)

    df = df.loc[1:, :]
    df_renamed = df.rename(
        columns={
            "is_status": "rev_id",
            "absorbed": "absorbed_without_clone",
            "absorbed.1": "absorbed_with_clone",
            "deleted": "deleted_without_clone",
            "deleted.1": "deleted_with_clone",
            "survived": "survived_without_clone",
            "survived.1": "survived_with_clone",
            "clone_deleted_rate(%)": "deletion_rate_with_clone",
            "no_clone_deleted_rate(%)": "deletion_rate_without_clone",
            "clone_absorbed_rate(%)": "absorption_rate_with_clone",
            "no_clone_absorbed_rate(%)": "absorption_rate_without_clone",
        }
    )

    # 数値型に変換
    numeric_columns = [
        "absorbed_without_clone",
        "absorbed_with_clone",
        "deleted_without_clone",
        "deleted_with_clone",
        "survived_without_clone",
        "survived_with_clone",
        "deletion_rate_with_clone",
        "deletion_rate_without_clone",
        "absorption_rate_with_clone",
        "absorption_rate_without_clone",
    ]
    for col in numeric_columns:
        df_renamed[col] = pd.to_numeric(df_renamed[col], errors="coerce")

    # 最後の行を除外
    df_renamed = df_renamed.iloc[:-1]
    
    # 結果を格納するリスト
    results = []
    
    # 生存数
    res = pg.wilcoxon(df_renamed["survived_without_clone"], df_renamed["survived_with_clone"])
    results.append({
        "指標": "平均生存数",
        "類似なし": f"{df_renamed['survived_without_clone'].mean():,.0f}",
        "類似あり": f"{df_renamed['survived_with_clone'].mean():,.0f}",
        "p値": f"{res.loc['Wilcoxon', 'p-val']:.2f}",
        "r_rb": f"{res.loc['Wilcoxon', 'RBC']:.2f}",
    })

    # 統合数
    res = pg.wilcoxon(df_renamed["absorbed_without_clone"], df_renamed["absorbed_with_clone"])
    results.append({
        "指標": "平均統合数",
        "類似なし": f"{df_renamed['absorbed_without_clone'].mean():,.0f}",
        "類似あり": f"{df_renamed['absorbed_with_clone'].mean():,.0f}",
        "p値": f"{res.loc['Wilcoxon', 'p-val']:.2f}",
        "r_rb": f"{res.loc['Wilcoxon', 'RBC']:.2f}",
    })

    # 削除数
    res = pg.wilcoxon(df_renamed["deleted_without_clone"], df_renamed["deleted_with_clone"])
    results.append({
        "指標": "平均削除数",
        "類似なし": f"{df_renamed['deleted_without_clone'].mean():,.0f}",
        "類似あり": f"{df_renamed['deleted_with_clone'].mean():,.0f}",
        "p値": f"{res.loc['Wilcoxon', 'p-val']:.2f}",
        "r_rb": f"{res.loc['Wilcoxon', 'RBC']:.2f}",
    })

    # 統合率
    res = pg.wilcoxon(df_renamed["absorption_rate_without_clone"], df_renamed["absorption_rate_with_clone"])
    results.append({
        "指標": "平均統合率",
        "類似なし": f"{df_renamed['absorption_rate_without_clone'].mean() / 100:.3f}",
        "類似あり": f"{df_renamed['absorption_rate_with_clone'].mean() / 100:.2f}",
        "p値": f"{res.loc['Wilcoxon', 'p-val']:.2f}",
        "r_rb": f"{res.loc['Wilcoxon', 'RBC']:.2f}",
    })
    
    # 削除率
    res = pg.wilcoxon(df_renamed["deletion_rate_without_clone"], df_renamed["deletion_rate_with_clone"])
    results.append({
        "指標": "平均削除率",
        "類似なし": f"{df_renamed['deletion_rate_without_clone'].mean() / 100:.3f}",
        "類似あり": f"{df_renamed['deletion_rate_with_clone'].mean() / 100:.3f}",
        "p値": f"{res.loc['Wilcoxon', 'p-val']:.2f}",
        "r_rb": f"{res.loc['Wilcoxon', 'RBC']:.2f}",
    })

    # テーブル出力
    table = Table(title="クローンの有無による比較")
    table.add_column("指標", style="cyan")
    table.add_column("類似なし", justify="right")
    table.add_column("類似あり", justify="right")
    table.add_column("p値", justify="right")
    table.add_column("r_rb", justify="right")
    
    for row in results:
        table.add_row(row["指標"], row["類似なし"], row["類似あり"], row["p値"], row["r_rb"])
    
    console.print(table)


@test_analysis.command()
@click.option(
    "--input-file",
    type=click.Path(exists=True, file_okay=True, dir_okay=False),
    default="./output/versions/nil/7_class_high_low_sim.csv",
    help="Input CSV file containing test analysis data",
)
def deleted_high_low(input_file):
    df = pd.read_csv(input_file)

    df = df.loc[2:, :]
    df_renamed = df.rename(
        columns={
            "is_status": "rev_id",
            "absorbed": "absorbed_without_clone",
            "absorbed.1": "absorbed_with_low_sim",
            "absorbed.2": "absorbed_with_high_sim",
            "deleted": "deleted_without_clone",
            "deleted.1": "deleted_with_low_sim",
            "deleted.2": "deleted_with_high_sim",
            "survived": "survived_without_clone",
            "survived.1": "survived_with_low_sim",
            "survived.2": "survived_with_high_sim",
            "high_sim_deleted_rate(%)": "deletion_rate_with_high_sim",
            "high_sim_absorbed_rate(%)": "absorption_rate_with_high_sim",
            "low_sim_deleted_rate(%)": "deletion_rate_with_low_sim",
            "low_sim_absorbed_rate(%)": "absorption_rate_with_low_sim",
        }
    )

    # 数値型に変換
    numeric_columns = [
        "absorbed_without_clone",
        "absorbed_with_low_sim",
        "absorbed_with_high_sim",
        "deleted_without_clone",
        "deleted_with_low_sim",
        "deleted_with_high_sim",
        "survived_without_clone",
        "survived_with_low_sim",
        "survived_with_high_sim",
        "deletion_rate_with_high_sim",
        "deletion_rate_with_low_sim",
        "absorption_rate_with_high_sim",
        "absorption_rate_with_low_sim",
    ]
    for col in numeric_columns:
        df_renamed[col] = pd.to_numeric(df_renamed[col], errors="coerce")

    # 最後の行を除外
    df_renamed = df_renamed.iloc[:-1]

    # 結果を格納するリスト
    results = []

    # 生存数
    res = pg.wilcoxon(df_renamed["survived_with_low_sim"], df_renamed["survived_with_high_sim"])
    results.append({
        "指標": "平均生存数",
        "低類似": f"{df_renamed['survived_with_low_sim'].mean():,.0f}",
        "高類似": f"{df_renamed['survived_with_high_sim'].mean():,.0f}",
        "p値": f"{res.loc['Wilcoxon', 'p-val']:.2f}",
        "r_rb": f"{res.loc['Wilcoxon', 'RBC']:.2f}",
    })
    
    # 統合数
    res = pg.wilcoxon(df_renamed["absorbed_with_low_sim"], df_renamed["absorbed_with_high_sim"])
    results.append({
        "指標": "平均統合数",
        "低類似": f"{df_renamed['absorbed_with_low_sim'].mean():,.0f}",
        "高類似": f"{df_renamed['absorbed_with_high_sim'].mean():,.0f}",
        "p値": f"{res.loc['Wilcoxon', 'p-val']:.2f}",
        "r_rb": f"{res.loc['Wilcoxon', 'RBC']:.2f}",
    })

    # 削除数
    res = pg.wilcoxon(df_renamed["deleted_with_low_sim"], df_renamed["deleted_with_high_sim"])
    results.append({
        "指標": "平均削除数",
        "低類似": f"{df_renamed['deleted_with_low_sim'].mean():,.0f}",
        "高類似": f"{df_renamed['deleted_with_high_sim'].mean():,.0f}",
        "p値": f"{res.loc['Wilcoxon', 'p-val']:.2f}",
        "r_rb": f"{res.loc['Wilcoxon', 'RBC']:.2f}",
    })
    
    # 統合率
    res = pg.wilcoxon(df_renamed["absorption_rate_with_low_sim"], df_renamed["absorption_rate_with_high_sim"])
    results.append({
        "指標": "平均統合率",
        "低類似": f"{df_renamed['absorption_rate_with_low_sim'].mean() / 100:.3f}",
        "高類似": f"{df_renamed['absorption_rate_with_high_sim'].mean() / 100:.2f}",
        "p値": f"{res.loc['Wilcoxon', 'p-val']:.2f}",
        "r_rb": f"{res.loc['Wilcoxon', 'RBC']:.2f}",
    })

    # 削除率
    res = pg.wilcoxon(df_renamed["deletion_rate_with_low_sim"], df_renamed["deletion_rate_with_high_sim"])
    results.append({
        "指標": "平均削除率",
        "低類似": f"{df_renamed['deletion_rate_with_low_sim'].mean() / 100:.3f}",
        "高類似": f"{df_renamed['deletion_rate_with_high_sim'].mean() / 100:.3f}",
        "p値": f"{res.loc['Wilcoxon', 'p-val']:.2f}",
        "r_rb": f"{res.loc['Wilcoxon', 'RBC']:.2f}",
    })

    # テーブル出力
    table = Table(title="類似度による比較（クローンあり内）")
    table.add_column("指標", style="cyan")
    table.add_column("低類似", justify="right")
    table.add_column("高類似", justify="right")
    table.add_column("p値", justify="right")
    table.add_column("r_rb", justify="right")
    
    for row in results:
        table.add_row(row["指標"], row["低類似"], row["高類似"], row["p値"], row["r_rb"])
    
    console.print(table)