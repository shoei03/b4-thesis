from pathlib import Path

import pandas as pd
import click
from rich.console import Console
import matplotlib.pyplot as plt
import seaborn as sns

from b4_thesis.const.column import ColumnNames
from b4_thesis.utils.revision_manager import RevisionManager

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


@survival.command()
@click.option(
    "--input-file",
    type=click.Path(exists=True, file_okay=True, dir_okay=False),
    default="./output/versions/survival/deletion_survival.csv",
    help="Input file from deletion_survival command",
)
@click.option(
    "--input-tracking",
    type=click.Path(exists=True, file_okay=True, dir_okay=False),
    default="./output/versions/method_tracker/method_tracked.csv",
    help="Full tracking data with method signatures",
)
@click.option(
    "--input",
    "-i",
    type=click.Path(exists=True, file_okay=False, dir_okay=True),
    required=True,
    default="./data/versions",
    help="Input directory containing revision subdirectories",
)
@click.option(
    "--output-csv",
    "-o",
    type=click.Path(file_okay=True, dir_okay=False),
    default="./output/versions/survival/2_analyze_absorbed.csv",
    help="Output CSV with absorbed method analysis",
)
@click.option(
    "--output-histogram",
    type=click.Path(file_okay=True, dir_okay=False),
    default="./output/versions/survival/2_analyze_absorbed_histogram.png",
    help="Output histogram of lifetime distribution",
)
@click.option(
    "--output-revision-breakdown",
    type=click.Path(file_okay=True, dir_okay=False),
    default="./output/versions/survival/2_analyze_absorbed_breakdown.png",
    help="Output per-revision breakdown chart",
)
def analyze_absorbed(
    input_file: str,
    input_tracking: str,
    input: str,
    output_csv: str,
    output_histogram: str,
    output_revision_breakdown: str,
) -> None:
    """Analyze Absorbed methods: lifetime distribution and origin classification."""
    # Step 1: Load deletion_survival data and compute lifetime
    ds_cols = [
        ColumnNames.PREV_REVISION_ID.value,
        "method_id",
        "survival_group",
        "relative_time",
        "median_similarity",
    ]
    df_ds = pd.read_csv(input_file, usecols=ds_cols)

    lifetime = df_ds.groupby("method_id").size().rename("lifetime")

    # Step 2: Get method signatures from tracking data
    sig_cols = [
        "method_id",
        ColumnNames.PREV_REVISION_ID.value,
        ColumnNames.PREV_FILE_PATH.value,
        ColumnNames.PREV_METHOD_NAME.value,
        ColumnNames.PREV_RETURN_TYPE.value,
        ColumnNames.PREV_PARAMETERS.value,
    ]
    has_clone_col = ColumnNames.HAS_CLONE.value
    try:
        df_tracking = pd.read_csv(input_tracking, usecols=sig_cols + [has_clone_col])
    except ValueError:
        df_tracking = pd.read_csv(input_tracking, usecols=sig_cols)
        df_tracking[has_clone_col] = None

    # Get t=0 row for each Absorbed method
    absorbed_t0 = df_ds[(df_ds["survival_group"] == "Absorbed") & (df_ds["relative_time"] == 0)][
        ["method_id", ColumnNames.PREV_REVISION_ID.value, "median_similarity"]
    ].copy()

    absorbed_t0 = absorbed_t0.merge(lifetime.reset_index(), on="method_id")

    # Add signatures from tracking data (join on method_id + prev_revision_id)
    # Remove duplicates to prevent row explosion during merge
    df_tracking_dedup = df_tracking.drop_duplicates(
        subset=["method_id", ColumnNames.PREV_REVISION_ID.value], keep="first"
    )
    absorbed_t0 = absorbed_t0.merge(
        df_tracking_dedup,
        on=["method_id", ColumnNames.PREV_REVISION_ID.value],
        how="left",
    )

    # Step 3: Check prior revision existence for lifetime=1 methods
    revision_manager = RevisionManager()
    revisions = revision_manager.get_revisions(Path(input))

    prev_rev_lookup: dict = {}
    for i in range(1, len(revisions)):
        prev_rev_lookup[str(revisions[i].timestamp)] = revisions[i - 1]

    absorbed_t0["origin"] = "already_tracked"
    absorbed_t0.loc[absorbed_t0["lifetime"] == 1, "origin"] = "unknown"

    single_row = absorbed_t0[absorbed_t0["lifetime"] == 1]

    for rev_id, group in single_row.groupby(ColumnNames.PREV_REVISION_ID.value):
        if rev_id not in prev_rev_lookup:
            absorbed_t0.loc[group.index, "origin"] = "first_revision"
            continue

        prev_rev = prev_rev_lookup[rev_id]
        code_blocks = revision_manager.load_code_blocks(prev_rev)

        sig_set = set(
            zip(
                code_blocks[ColumnNames.FILE_PATH.value],
                code_blocks[ColumnNames.METHOD_NAME.value],
                code_blocks[ColumnNames.RETURN_TYPE.value],
                code_blocks[ColumnNames.PARAMETERS.value],
            )
        )

        for idx, row in group.iterrows():
            method_sig = (
                row[ColumnNames.PREV_FILE_PATH.value],
                row[ColumnNames.PREV_METHOD_NAME.value],
                row[ColumnNames.PREV_RETURN_TYPE.value],
                row[ColumnNames.PREV_PARAMETERS.value],
            )
            if method_sig in sig_set:
                absorbed_t0.loc[idx, "origin"] = "similarity_crossed"
            else:
                absorbed_t0.loc[idx, "origin"] = "newly_added"

    # Step 4: Print summary
    total = len(absorbed_t0)
    single_count = int((absorbed_t0["lifetime"] == 1).sum())
    multi_count = int((absorbed_t0["lifetime"] >= 2).sum())

    newly_added_count = int((absorbed_t0["origin"] == "newly_added").sum())
    sim_crossed_count = int((absorbed_t0["origin"] == "similarity_crossed").sum())
    first_rev_count = int((absorbed_t0["origin"] == "first_revision").sum())

    console.print("\n[bold]Absorbed Method Analysis[/bold]")
    console.print("=" * 40)
    console.print(f"Total Absorbed methods: {total:,}")
    console.print(f"  lifetime=1 (t=0 only): {single_count:,} ({single_count / total * 100:.1f}%)")
    console.print(
        f"    newly_added:        {newly_added_count:,} ({newly_added_count / total * 100:.1f}%)"
    )
    console.print(
        f"    similarity_crossed: {sim_crossed_count:,} ({sim_crossed_count / total * 100:.1f}%)"
    )
    console.print(
        f"    first_revision:     {first_rev_count:,} ({first_rev_count / total * 100:.1f}%)"
    )
    console.print(f"  lifetime>=2 (tracked): {multi_count:,} ({multi_count / total * 100:.1f}%)")
    if multi_count > 0:
        multi_lifetime = absorbed_t0[absorbed_t0["lifetime"] >= 2]["lifetime"]
        console.print(f"    Mean lifetime: {multi_lifetime.mean():.1f}")
        console.print(f"    Median lifetime: {multi_lifetime.median():.1f}")
    console.print(f"\nt=0 -> t=-1 drop: {single_count:,} methods")

    # # Step 5: Save CSV
    # output_path = Path(output_csv)
    # output_path.parent.mkdir(parents=True, exist_ok=True)

    # output_cols = [
    #     "method_id",
    #     "lifetime",
    #     "origin",
    #     ColumnNames.PREV_REVISION_ID.value,
    #     ColumnNames.PREV_FILE_PATH.value,
    #     ColumnNames.PREV_METHOD_NAME.value,
    #     "median_similarity",
    #     has_clone_col,
    # ]
    # absorbed_t0[output_cols].to_csv(output_path, index=False)
    # console.print(f"\n[green]Results saved to:[/green] {output_path}")

    # # Step 6: Visualizations
    # plt.rcParams.update(
    #     {
    #         "font.family": "Hiragino Sans",
    #         "font.size": 12,
    #         "axes.titlesize": 14,
    #         "axes.labelsize": 12,
    #         "xtick.labelsize": 10,
    #         "ytick.labelsize": 10,
    #         "legend.fontsize": 11,
    #         "figure.dpi": 300,
    #     }
    # )

    # colors = {
    #     "newly_added": "#2ca02c",
    #     "similarity_crossed": "#ff7f0e",
    #     "first_revision": "#9467bd",
    #     "already_tracked": "#1f77b4",
    # }
    # label_map = {
    #     "newly_added": "新規追加",
    #     "similarity_crossed": "類似度超過",
    #     "first_revision": "初回リビジョン",
    #     "already_tracked": "追跡済み",
    # }

    # # --- Histogram: lifetime distribution with origin breakdown ---
    # fig, ax = plt.subplots(figsize=(10, 6))
    # max_lifetime = int(absorbed_t0["lifetime"].max())

    # # Stacked histogram for lifetime=1 (by origin) and lifetime>=2 (already_tracked)
    # origin_order = ["newly_added", "similarity_crossed", "first_revision", "already_tracked"]
    # bottom = pd.Series(0, index=range(1, max_lifetime + 1))

    # for origin in origin_order:
    #     subset = absorbed_t0[absorbed_t0["origin"] == origin]
    #     if subset.empty:
    #         continue
    #     counts = subset["lifetime"].value_counts().reindex(range(1, max_lifetime + 1), fill_value=0)
    #     ax.bar(
    #         counts.index,
    #         counts.values,
    #         bottom=bottom.values,
    #         color=colors[origin],
    #         label=label_map[origin],
    #         edgecolor="white",
    #         linewidth=0.5,
    #     )
    #     bottom += counts

    # ax.set_xlabel("ライフタイム (リビジョンペア数)")
    # ax.set_ylabel("メソッド数")
    # ax.legend(loc="upper right", frameon=True, fancybox=True, shadow=True)
    # ax.set_xticks(range(1, max_lifetime + 1))
    # ax.grid(True, alpha=0.3, linestyle="--", axis="y")

    # plt.tight_layout()
    # Path(output_histogram).parent.mkdir(parents=True, exist_ok=True)
    # plt.savefig(output_histogram, dpi=300, bbox_inches="tight", facecolor="white", edgecolor="none")
    # plt.close()
    # console.print(f"[green]Histogram saved to:[/green] {output_histogram}")

    # # --- Per-revision breakdown stacked bar chart ---
    # rev_order = sorted(absorbed_t0[ColumnNames.PREV_REVISION_ID.value].dropna().unique())
    # rev_breakdown = pd.crosstab(
    #     absorbed_t0[ColumnNames.PREV_REVISION_ID.value],
    #     absorbed_t0["origin"],
    # ).reindex(index=rev_order, columns=origin_order, fill_value=0)

    # fig2, ax2 = plt.subplots(figsize=(14, 6))
    # bottom2 = pd.Series(0.0, index=rev_breakdown.index)

    # for origin in origin_order:
    #     if origin not in rev_breakdown.columns:
    #         continue
    #     vals = rev_breakdown[origin]
    #     ax2.bar(
    #         range(len(rev_order)),
    #         vals.values,
    #         bottom=bottom2.values,
    #         color=colors[origin],
    #         label=label_map[origin],
    #         edgecolor="white",
    #         linewidth=0.5,
    #     )
    #     bottom2 += vals

    # ax2.set_xlabel("リビジョン")
    # ax2.set_ylabel("Absorbed メソッド数")
    # ax2.set_xticks(range(len(rev_order)))
    # ax2.set_xticklabels([r[:10] for r in rev_order], rotation=45, ha="right", fontsize=8)
    # ax2.legend(loc="upper left", frameon=True, fancybox=True, shadow=True)
    # ax2.grid(True, alpha=0.3, linestyle="--", axis="y")

    # plt.tight_layout()
    # Path(output_revision_breakdown).parent.mkdir(parents=True, exist_ok=True)
    # plt.savefig(
    #     output_revision_breakdown,
    #     dpi=300,
    #     bbox_inches="tight",
    #     facecolor="white",
    #     edgecolor="none",
    # )
    # plt.close()
    # console.print(f"[green]Revision breakdown saved to:[/green] {output_revision_breakdown}")
