from pathlib import Path

import pandas as pd
import click
from rich.console import Console
import matplotlib.pyplot as plt
import seaborn as sns

from b4_thesis.const.column import ColumnNames

console = Console()


@click.group()
def survival():
    """Method Tracking Command Group."""
    pass


@survival.command()
@click.option(
    "--input-file",
    type=click.Path(exists=True, file_okay=True, dir_okay=False),
    default="./output/versions/nil/4_track_median_similarity.csv",
    help="Input file containing tracked methods data",
)
@click.option(
    "--output-csv",
    type=click.Path(file_okay=True, dir_okay=False),
    default="./output/versions/survival/deletion_survival.csv",
    help="Output file for CSV data",
)
@click.option(
    "--output-boxplot-absorber",
    type=click.Path(file_okay=True, dir_okay=False),
    default="./output/versions/survival/deletion_survival_boxplot_absorber.pdf",
    help="Output file for the absorber group boxplot",
)
@click.option(
    "--output-boxplot-deletion",
    type=click.Path(file_okay=True, dir_okay=False),
    default="./output/versions/survival/deletion_survival_boxplot_deletion.pdf",
    help="Output file for the absorbed+deleted group boxplot",
)
@click.option(
    "--output-areaplot-absorber",
    type=click.Path(file_okay=True, dir_okay=False),
    default="./output/versions/survival/deletion_survival_areaplot_absorber.pdf",
    help="Output file for the absorber group area plot",
)
@click.option(
    "--output-areaplot-deletion",
    type=click.Path(file_okay=True, dir_okay=False),
    default="./output/versions/survival/deletion_survival_areaplot_deletion.pdf",
    help="Output file for the absorbed+deleted group stacked area plot",
)
def deletion_survival(
    input_file: str,
    output_csv: str,
    output_boxplot_absorber: str,
    output_boxplot_deletion: str,
    output_areaplot_absorber: str,
    output_areaplot_deletion: str,
) -> None:
    """Track median_similarity evolution per method_id for different deletion types."""
    cols = [
        ColumnNames.PREV_REVISION_ID.value,
        "is_deleted",
        # "is_partial_deleted",
        # "is_all_deleted",
        "is_absorbed",
        "is_absorber",
        "is_matched",
        "median_similarity",
        "method_id",
    ]
    df = pd.read_csv(input_file, usecols=cols)

    # 各method_idの最新行で4分類: "Matched" / "Absorber" / "Absorbed" / "Deleted"
    latest = (
        df.sort_values(ColumnNames.PREV_REVISION_ID.value, ascending=False)
        .groupby("method_id")
        .first()
    )
    latest["survival_group"] = None
    # 最終行の状態で分類
    latest.loc[latest["is_matched"], "survival_group"] = "Matched"
    latest.loc[latest["is_deleted"], "survival_group"] = "Deleted"
    latest.loc[latest["is_absorbed"], "survival_group"] = "Absorbed"
    # Absorber: 最終状態がMatchedかつ生存期間中にis_absorber=Trueを持つ
    absorber_any = df.groupby("method_id")["is_absorber"].any()
    absorber_ids = absorber_any[absorber_any].index
    latest.loc[
        (latest["survival_group"] == "Matched") & latest.index.isin(absorber_ids),
        "survival_group",
    ] = "Absorber"

    group_map = latest["survival_group"].dropna()
    df["survival_group"] = df["method_id"].map(group_map)
    df = df[df["survival_group"].notna()]

    # 各method_idごとに相対時間を計算
    df = df.sort_values(["method_id", ColumnNames.PREV_REVISION_ID.value])

    # デフォルト: 最新行=0、遡って-1, -2, ...
    df["relative_time"] = (
        (
            df.groupby("method_id").cumcount()
            - df.groupby("method_id")["method_id"].transform("count")
            + 1
        )
        .fillna(0)
        .astype(int)
    )

    # Absorberグループ: 最後のis_absorber=True行を基準(0)に再計算
    absorber_mask = df["survival_group"] == "Absorber"
    if absorber_mask.any():
        absorber_df = df.loc[absorber_mask].copy()
        absorber_df["_pos"] = absorber_df.groupby("method_id").cumcount()
        last_absorber_pos = (
            absorber_df[absorber_df["is_absorber"]].groupby("method_id")["_pos"].last()
        )
        absorber_df["_anchor"] = absorber_df["method_id"].map(last_absorber_pos)
        df.loc[absorber_mask, "relative_time"] = (
            absorber_df["_pos"] - absorber_df["_anchor"]
        ).astype(int)
    df.to_csv(output_csv, index=False)
    latest_df = df[df["relative_time"] == 0]
    console.print(latest_df.groupby(["survival_group"]).size())
    console.print(
        latest_df[latest_df["median_similarity"].notna()]
        .groupby(["survival_group"])["median_similarity"]
        .mean()
    )
    console.print(f"[green]Data with survival groups saved to:[/green] {output_csv}")

    # プロット設定（論文用、PDF出力対応）
    plt.rcParams.update(
        {
            "font.family": "Hiragino Sans",  # macOS用日本語フォント
            "font.size": 16,
            "axes.titlesize": 20,
            "axes.labelsize": 18,
            "xtick.labelsize": 14,
            "ytick.labelsize": 14,
            "legend.fontsize": 16,
            "figure.dpi": 300,
            "pdf.fonttype": 42,  # TrueTypeフォントを埋め込み（日本語対応）
            "ps.fonttype": 42,
        }
    )

    # 日本語ラベル用のマッピング
    label_map = {"Matched": "生存", "Absorber": "統合先", "Absorbed": "統合元", "Deleted": "削除"}
    df["survival_group_ja"] = df["survival_group"].map(label_map)

    colors = {"生存": "#1f77b4", "統合先": "#2ca02c", "統合元": "#ff7f0e", "削除": "#d62728"}

    plot_df = df[df["median_similarity"].notna()]

    # DataFrameを統合先群と統合元+削除群に分割
    absorber_df = plot_df[plot_df["survival_group_ja"] == "統合先"]
    deletion_df = plot_df[plot_df["survival_group_ja"].isin(["統合元", "削除"])]

    # 統合先用のtime_values（中央が0）
    absorber_time_values = sorted(absorber_df["relative_time"].unique())
    # 統合元+削除用のtime_values（右端が0、降順で並べる）
    deletion_time_values = sorted(deletion_df["relative_time"].unique())

    # サンプル数の集計
    count_df = (
        plot_df.groupby(["relative_time", "survival_group_ja"]).size().reset_index(name="count")
    )
    count_absorber = count_df[count_df["survival_group_ja"] == "統合先"]
    count_deletion = count_df[count_df["survival_group_ja"].isin(["統合元", "削除"])]

    # --- 箱ひげ図: 統合先群（中央が0） ---
    fig1, ax1 = plt.subplots(figsize=(12, 6))
    sns.boxplot(
        data=absorber_df,
        x="relative_time",
        y="median_similarity",
        color=colors["統合先"],
        linewidth=1.2,
        fliersize=3,
        order=absorber_time_values,
        ax=ax1,
    )
    ax1.set_xlabel("相対時間 (0 = 統合直前のバージョン)", labelpad=10)
    ax1.set_ylabel("類似度（中央値） (%)", labelpad=10)
    ax1.grid(True, alpha=0.3, linestyle="--")
    ax1.set_xlim(-0.5, len(absorber_time_values) - 0.5)
    # x軸ラベルは偶数（0含む）のみ表示（目盛り線は全値に残す）
    ax1.set_xticks(range(len(absorber_time_values)))
    ax1.set_xticklabels([str(t) if t % 2 == 0 else "" for t in absorber_time_values])

    plt.tight_layout()
    plt.savefig(
        output_boxplot_absorber, dpi=300, bbox_inches="tight", facecolor="white", edgecolor="none"
    )
    plt.close()
    console.print(f"[green]Boxplot (absorber) saved to:[/green] {output_boxplot_absorber}")

    # --- 箱ひげ図: 統合元+削除群（右端が0） ---
    fig2, ax2 = plt.subplots(figsize=(12, 6))
    sns.boxplot(
        data=deletion_df,
        x="relative_time",
        y="median_similarity",
        hue="survival_group_ja",
        palette={k: colors[k] for k in ["統合元", "削除"]},
        linewidth=1.2,
        fliersize=3,
        order=deletion_time_values,
        ax=ax2,
    )
    ax2.set_xlabel("相対時間 (0 = 削除または統合直前のバージョン)", labelpad=10)
    ax2.set_ylabel("類似度（中央値） (%)", labelpad=10)
    ax2.grid(True, alpha=0.3, linestyle="--")
    ax2.legend(loc="upper left", frameon=True, fancybox=True, shadow=True)
    ax2.set_xlim(-0.5, len(deletion_time_values) - 0.5)
    # x軸ラベルは偶数（0含む）のみ表示（目盛り線は全値に残す）
    ax2.set_xticks(range(len(deletion_time_values)))
    ax2.set_xticklabels([str(t) if t % 2 == 0 else "" for t in deletion_time_values])

    plt.tight_layout()
    plt.savefig(
        output_boxplot_deletion, dpi=300, bbox_inches="tight", facecolor="white", edgecolor="none"
    )
    plt.close()
    console.print(f"[green]Boxplot (deletion) saved to:[/green] {output_boxplot_deletion}")

    # --- 面グラフ用のデータ準備と縦軸の最大値計算 ---
    absorber_time_to_pos = {t: i for i, t in enumerate(absorber_time_values)}

    # 統合先群のカウントデータ
    absorber_count_data = count_absorber.sort_values("relative_time")
    absorber_count_by_time = (
        dict(zip(absorber_count_data["relative_time"], absorber_count_data["count"]))
        if not absorber_count_data.empty
        else {}
    )
    absorber_counts = [absorber_count_by_time.get(t, 0) for t in absorber_time_values]

    # 統合元+削除群のカウントデータ
    stacked_data = {}
    for group in ["統合元", "削除"]:
        group_data = count_deletion[count_deletion["survival_group_ja"] == group]
        count_by_time = dict(zip(group_data["relative_time"], group_data["count"]))
        stacked_data[group] = [count_by_time.get(t, 0) for t in deletion_time_values]

    # 両グラフの縦軸最大値を揃える
    max_absorber = max(absorber_counts) if absorber_counts else 0
    max_deletion = (
        max(a + b for a, b in zip(stacked_data["統合元"], stacked_data["削除"]))
        if stacked_data["統合元"]
        else 0
    )
    y_max = max(max_absorber, max_deletion) * 1.05  # 5%の余白

    # --- 面グラフ: 統合先群（中央が0） ---
    fig3, ax3 = plt.subplots(figsize=(12, 4))
    if absorber_counts:
        positions = list(range(len(absorber_time_values)))
        ax3.fill_between(
            positions,
            absorber_counts,
            color=colors["統合先"],
            alpha=0.7,
            label="統合先",
        )
        ax3.plot(positions, absorber_counts, color=colors["統合先"], linewidth=1.5)
    ax3.set_xlabel("相対時間 (0 = 統合直前のバージョン)", labelpad=10)
    ax3.set_ylabel("メソッド数", labelpad=10)
    ax3.grid(True, alpha=0.3, linestyle="--")
    ax3.legend(loc="upper left", frameon=True, fancybox=True, shadow=True)
    ax3.set_xticks(range(len(absorber_time_values)))
    # x軸ラベルは偶数（0含む）のみ表示（目盛り線は全値に残す）
    ax3.set_xticklabels([str(t) if t % 2 == 0 else "" for t in absorber_time_values])
    ax3.set_xlim(-0.5, len(absorber_time_values) - 0.5)
    ax3.set_ylim(0, y_max)

    plt.tight_layout()
    plt.savefig(
        output_areaplot_absorber, dpi=300, bbox_inches="tight", facecolor="white", edgecolor="none"
    )
    plt.close()
    console.print(f"[green]Area plot (absorber) saved to:[/green] {output_areaplot_absorber}")

    # --- 積み上げ面グラフ: 統合元+削除群（右端が0） ---
    fig4, ax4 = plt.subplots(figsize=(12, 4))

    positions = list(range(len(deletion_time_values)))
    ax4.stackplot(
        positions,
        stacked_data["統合元"],
        stacked_data["削除"],
        labels=["統合元", "削除"],
        colors=[colors["統合元"], colors["削除"]],
        alpha=0.7,
    )
    ax4.set_xlabel("相対時間 (0 = 統合または削除直前のバージョン)", labelpad=10)
    ax4.set_ylabel("メソッド数", labelpad=10)
    ax4.grid(True, alpha=0.3, linestyle="--")
    ax4.legend(loc="upper left", frameon=True, fancybox=True, shadow=True)
    ax4.set_xticks(positions)
    # x軸ラベルは偶数（0含む）のみ表示（目盛り線は全値に残す）
    ax4.set_xticklabels([str(t) if t % 2 == 0 else "" for t in deletion_time_values])
    ax4.set_xlim(-0.5, len(deletion_time_values) - 0.5)
    ax4.set_ylim(0, y_max)

    plt.tight_layout()
    plt.savefig(
        output_areaplot_deletion, dpi=300, bbox_inches="tight", facecolor="white", edgecolor="none"
    )
    plt.close()
    console.print(f"[green]Area plot (deletion) saved to:[/green] {output_areaplot_deletion}")
