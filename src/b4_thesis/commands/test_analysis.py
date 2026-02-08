import click
import pandas as pd
import pingouin as pg
from rich.console import Console

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
    
    res = pg.wilcoxon(df_renamed["survived_without_clone"], df_renamed["survived_with_clone"])
    console.print(f"p-value: {res.loc['Wilcoxon', 'p-val']:.6f}")
    console.print(f"Effect size: {res.loc['Wilcoxon', 'RBC']:.2f}")

    res = pg.wilcoxon(df_renamed["absorbed_without_clone"], df_renamed["absorbed_with_clone"])
    console.print(f"p-value: {res.loc['Wilcoxon', 'p-val']:.6f}")
    console.print(f"Effect size: {res.loc['Wilcoxon', 'RBC']:.2f}")

    res = pg.wilcoxon(df_renamed["deleted_without_clone"], df_renamed["deleted_with_clone"])
    console.print(f"p-value: {res.loc['Wilcoxon', 'p-val']:.6f}")
    console.print(f"Effect size: {res.loc['Wilcoxon', 'RBC']:.2f}")

    res = pg.wilcoxon(df_renamed["absorption_rate_without_clone"], df_renamed["absorption_rate_with_clone"])
    console.print(f"p-value: {res.loc['Wilcoxon', 'p-val']:.6f}")
    console.print(f"Effect size: {res.loc['Wilcoxon', 'RBC']:.2f}")
    
    res = pg.wilcoxon(
        df_renamed["deletion_rate_without_clone"], df_renamed["deletion_rate_with_clone"]
    )
    console.print(f"p-value: {res.loc['Wilcoxon', 'p-val']:.6f}")
    console.print(f"Effect size: {res.loc['Wilcoxon', 'RBC']:.2f}")


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

    res = pg.wilcoxon(df_renamed["survived_with_low_sim"], df_renamed["survived_with_high_sim"])
    console.print(f"p-value: {res.loc['Wilcoxon', 'p-val']:.6f}")
    console.print(f"Effect size: {res.loc['Wilcoxon', 'RBC']:.2f}")
    
    res = pg.wilcoxon(df_renamed["absorbed_with_low_sim"], df_renamed["absorbed_with_high_sim"])
    console.print(f"p-value: {res.loc['Wilcoxon', 'p-val']:.6f}")
    console.print(f"Effect size: {res.loc['Wilcoxon', 'RBC']:.2f}")

    res = pg.wilcoxon(df_renamed["deleted_with_low_sim"], df_renamed["deleted_with_high_sim"])
    console.print(f"p-value: {res.loc['Wilcoxon', 'p-val']:.6f}")
    console.print(f"Effect size: {res.loc['Wilcoxon', 'RBC']:.2f}")
    
    res = pg.wilcoxon(
        df_renamed["absorption_rate_with_low_sim"], df_renamed["absorption_rate_with_high_sim"]
    )
    console.print(f"p-value: {res.loc['Wilcoxon', 'p-val']:.6f}")
    console.print(f"Effect size: {res.loc['Wilcoxon', 'RBC']:.2f}")

    res = pg.wilcoxon(
        df_renamed["deletion_rate_with_low_sim"], df_renamed["deletion_rate_with_high_sim"]
    )
    console.print(f"p-value: {res.loc['Wilcoxon', 'p-val']:.6f}")
    console.print(f"Effect size: {res.loc['Wilcoxon', 'RBC']:.2f}")
