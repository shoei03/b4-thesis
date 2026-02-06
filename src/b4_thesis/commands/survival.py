from pathlib import Path

import click
import matplotlib.pyplot as plt
import pandas as pd
from rich.console import Console
import seaborn as sns

from b4_thesis.const.column import ColumnNames
from b4_thesis.utils.revision_manager import RevisionManager

console = Console()

# --- 定数 ---

_PLOT_RCPARAMS: dict[str, object] = {
    "font.family": "Hiragino Sans",
    "font.size": 16,
    "axes.titlesize": 20,
    "axes.labelsize": 18,
    "xtick.labelsize": 14,
    "ytick.labelsize": 14,
    "legend.fontsize": 16,
    "figure.dpi": 300,
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
}

_SURVIVAL_LABEL_MAP = {
    "Matched": "生存",
    "Absorber": "統合先",
    "Absorbed": "統合元",
    "Deleted": "削除",
}

_SURVIVAL_COLORS = {
    "生存": "#1f77b4",
    "統合先": "#2ca02c",
    "統合元": "#ff7f0e",
    "削除": "#d62728",
}

_DELETION_SURVIVAL_COLS = [
    ColumnNames.PREV_REVISION_ID.value,
    "is_deleted",
    "is_absorbed",
    "is_absorber",
    "is_matched",
    "median_similarity",
    "method_id",
]


# --- deletion_survival ヘルパー ---


def _classify_survival_groups(df: pd.DataFrame) -> pd.Series:
    """各method_idを最終行の状態で4分類し、method_id → survival_group のマッピングを返す。

    分類ルール（上流でis_matched/is_deletedは排他的、is_absorbed/is_absorberはis_matched行のみ）:
    - Matched: 最終行がis_matched=True
    - Deleted: 最終行がis_deleted=True
    - Absorbed: 最終行がis_absorbed=True
    - Absorber: 最終行がis_matched=True かつ 生存期間中にis_absorber=Trueを持つ
    """
    latest = (
        df.sort_values(ColumnNames.PREV_REVISION_ID.value, ascending=False)
        .groupby("method_id")
        .first()
    )
    latest["survival_group"] = None
    latest.loc[latest["is_matched"], "survival_group"] = "Matched"
    latest.loc[latest["is_deleted"], "survival_group"] = "Deleted"
    latest.loc[latest["is_absorbed"], "survival_group"] = "Absorbed"

    absorber_any = df.groupby("method_id")["is_absorber"].any()
    absorber_ids = absorber_any[absorber_any].index
    latest.loc[
        (latest["survival_group"] == "Matched") & latest.index.isin(absorber_ids),
        "survival_group",
    ] = "Absorber"

    return latest["survival_group"].dropna()


def _compute_relative_time(df: pd.DataFrame) -> pd.DataFrame:
    """各method_idごとに相対時間を計算する。

    デフォルト: 最新行=0、遡って-1, -2, ...
    Absorberグループ: 最後のis_absorber=True行を基準(0)に再アンカリング。
    """
    df = df.sort_values(["method_id", ColumnNames.PREV_REVISION_ID.value])

    df["relative_time"] = (
        (
            df.groupby("method_id").cumcount()
            - df.groupby("method_id")["method_id"].transform("count")
            + 1
        )
        .fillna(0)
        .astype(int)
    )

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

    return df


def _setup_plot_style() -> None:
    """matplotlib を論文用PDF出力向けに設定する。"""
    plt.rcParams.update(_PLOT_RCPARAMS)


def _plot_boxplot_absorber(
    absorber_df: pd.DataFrame, time_values: list[int], output_path: str
) -> None:
    """統合先群の箱ひげ図を描画・保存する（t=0 = 統合直前）。"""
    fig, ax = plt.subplots(figsize=(12, 6))
    sns.boxplot(
        data=absorber_df,
        x="relative_time",
        y="median_similarity",
        color=_SURVIVAL_COLORS["統合先"],
        linewidth=1.2,
        fliersize=3,
        order=time_values,
        ax=ax,
    )
    ax.set_xlabel("相対時間 (0 = 統合直前のバージョン)", labelpad=10)
    ax.set_ylabel("類似度（中央値） (%)", labelpad=10)
    ax.grid(True, alpha=0.3, linestyle="--")
    ax.set_xlim(-0.5, len(time_values) - 0.5)
    ax.set_xticks(range(len(time_values)))
    ax.set_xticklabels([str(t) if t % 2 == 0 else "" for t in time_values])

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches="tight", facecolor="white", edgecolor="none")
    plt.close()
    console.print(f"[green]Boxplot (absorber) saved to:[/green] {output_path}")


def _plot_boxplot_deletion(
    deletion_df: pd.DataFrame, time_values: list[int], output_path: str
) -> None:
    """統合元+削除群の箱ひげ図を描画・保存する（t=0 = 削除/統合直前）。"""
    fig, ax = plt.subplots(figsize=(12, 6))
    sns.boxplot(
        data=deletion_df,
        x="relative_time",
        y="median_similarity",
        hue="survival_group_ja",
        palette={k: _SURVIVAL_COLORS[k] for k in ["統合元", "削除"]},
        linewidth=1.2,
        fliersize=3,
        order=time_values,
        ax=ax,
    )
    ax.set_xlabel("相対時間 (0 = 削除または統合直前のバージョン)", labelpad=10)
    ax.set_ylabel("類似度（中央値） (%)", labelpad=10)
    ax.grid(True, alpha=0.3, linestyle="--")
    ax.legend(loc="upper left", frameon=True, fancybox=True, shadow=True)
    ax.set_xlim(-0.5, len(time_values) - 0.5)
    ax.set_xticks(range(len(time_values)))
    ax.set_xticklabels([str(t) if t % 2 == 0 else "" for t in time_values])

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches="tight", facecolor="white", edgecolor="none")
    plt.close()
    console.print(f"[green]Boxplot (deletion) saved to:[/green] {output_path}")


def _prepare_area_data(
    count_df: pd.DataFrame,
    absorber_time_values: list[int],
    deletion_time_values: list[int],
) -> tuple[list[int], dict[str, list[int]], float]:
    """面グラフ用のカウントデータを整形し、共通のy_maxを計算する。

    Returns:
        (absorber_counts, stacked_data, y_max)
    """
    count_absorber = count_df[count_df["survival_group_ja"] == "統合先"]
    count_deletion = count_df[count_df["survival_group_ja"].isin(["統合元", "削除"])]

    # 統合先群のカウントデータ
    absorber_count_data = count_absorber.sort_values("relative_time")
    absorber_count_by_time = (
        dict(zip(absorber_count_data["relative_time"], absorber_count_data["count"]))
        if not absorber_count_data.empty
        else {}
    )
    absorber_counts = [absorber_count_by_time.get(t, 0) for t in absorber_time_values]

    # 統合元+削除群のカウントデータ
    stacked_data: dict[str, list[int]] = {}
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
    y_max = max(max_absorber, max_deletion) * 1.05

    return absorber_counts, stacked_data, y_max


def _plot_area_absorber(
    absorber_counts: list[int],
    time_values: list[int],
    y_max: float,
    output_path: str,
) -> None:
    """統合先群の面グラフを描画・保存する。"""
    fig, ax = plt.subplots(figsize=(12, 4))
    if absorber_counts:
        positions = list(range(len(time_values)))
        ax.fill_between(
            positions,
            absorber_counts,
            color=_SURVIVAL_COLORS["統合先"],
            alpha=0.7,
            label="統合先",
        )
        ax.plot(positions, absorber_counts, color=_SURVIVAL_COLORS["統合先"], linewidth=1.5)
    ax.set_xlabel("相対時間 (0 = 統合直前のバージョン)", labelpad=10)
    ax.set_ylabel("メソッド数", labelpad=10)
    ax.grid(True, alpha=0.3, linestyle="--")
    ax.legend(loc="upper left", frameon=True, fancybox=True, shadow=True)
    ax.set_xticks(range(len(time_values)))
    ax.set_xticklabels([str(t) if t % 2 == 0 else "" for t in time_values])
    ax.set_xlim(-0.5, len(time_values) - 0.5)
    ax.set_ylim(0, y_max)

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches="tight", facecolor="white", edgecolor="none")
    plt.close()
    console.print(f"[green]Area plot (absorber) saved to:[/green] {output_path}")


def _plot_area_deletion(
    stacked_data: dict[str, list[int]],
    time_values: list[int],
    y_max: float,
    output_path: str,
) -> None:
    """統合元+削除群の積み上げ面グラフを描画・保存する。"""
    fig, ax = plt.subplots(figsize=(12, 4))

    positions = list(range(len(time_values)))
    ax.stackplot(
        positions,
        stacked_data["統合元"],
        stacked_data["削除"],
        labels=["統合元", "削除"],
        colors=[_SURVIVAL_COLORS["統合元"], _SURVIVAL_COLORS["削除"]],
        alpha=0.7,
    )
    ax.set_xlabel("相対時間 (0 = 統合または削除直前のバージョン)", labelpad=10)
    ax.set_ylabel("メソッド数", labelpad=10)
    ax.grid(True, alpha=0.3, linestyle="--")
    ax.legend(loc="upper left", frameon=True, fancybox=True, shadow=True)
    ax.set_xticks(positions)
    ax.set_xticklabels([str(t) if t % 2 == 0 else "" for t in time_values])
    ax.set_xlim(-0.5, len(time_values) - 0.5)
    ax.set_ylim(0, y_max)

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches="tight", facecolor="white", edgecolor="none")
    plt.close()
    console.print(f"[green]Area plot (deletion) saved to:[/green] {output_path}")


# --- analyze_absorbed ヘルパー ---


def _load_absorbed_data(input_file: str, input_tracking: str) -> pd.DataFrame:
    """deletion_survivalの出力とトラッキングデータを読み込み、Absorbed t=0行を構築する。"""
    ds_cols = [
        ColumnNames.PREV_REVISION_ID.value,
        "method_id",
        "survival_group",
        "relative_time",
        "median_similarity",
    ]
    df_ds = pd.read_csv(input_file, usecols=ds_cols)

    lifetime = df_ds.groupby("method_id").size().rename("lifetime")

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

    absorbed_t0 = df_ds[(df_ds["survival_group"] == "Absorbed") & (df_ds["relative_time"] == 0)][
        ["method_id", ColumnNames.PREV_REVISION_ID.value, "median_similarity"]
    ].copy()

    absorbed_t0 = absorbed_t0.merge(lifetime.reset_index(), on="method_id")

    df_tracking_dedup = df_tracking.drop_duplicates(
        subset=["method_id", ColumnNames.PREV_REVISION_ID.value], keep="first"
    )
    absorbed_t0 = absorbed_t0.merge(
        df_tracking_dedup,
        on=["method_id", ColumnNames.PREV_REVISION_ID.value],
        how="left",
    )

    return absorbed_t0


def _classify_absorbed_origin(absorbed_t0: pd.DataFrame, input_dir: str) -> pd.DataFrame:
    """lifetime=1のAbsorbedメソッドのoriginを分類する。

    分類結果:
    - already_tracked: lifetime >= 2（以前から追跡済み）
    - newly_added: 前のリビジョンにシグネチャが存在しない（新規追加）
    - similarity_crossed: 前のリビジョンにシグネチャが存在する（類似度閾値超過）
    - first_revision: 最初のリビジョンのため前のリビジョンが存在しない
    """
    revision_manager = RevisionManager()
    revisions = revision_manager.get_revisions(Path(input_dir))

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

    return absorbed_t0


def _print_absorbed_summary(absorbed_t0: pd.DataFrame) -> None:
    """Absorbedメソッドの統計サマリーを表示する。"""
    total = len(absorbed_t0)
    if total == 0:
        console.print("[yellow]No absorbed methods found.[/yellow]")
        return

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


# --- Click コマンド ---


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
    df = pd.read_csv(input_file, usecols=_DELETION_SURVIVAL_COLS)

    # 1. survival_group 分類
    group_map = _classify_survival_groups(df)
    df["survival_group"] = df["method_id"].map(group_map)
    df = df[df["survival_group"].notna()]

    # 2. relative_time 計算
    df = _compute_relative_time(df)

    # 3. CSV出力 + サマリー表示
    df.to_csv(output_csv, index=False)
    latest_df = df[df["relative_time"] == 0]
    console.print(latest_df.groupby(["survival_group"]).size())
    console.print(
        latest_df[latest_df["median_similarity"].notna()]
        .groupby(["survival_group"])["median_similarity"]
        .mean()
    )
    console.print(f"[green]Data with survival groups saved to:[/green] {output_csv}")

    # 4. プロット
    _setup_plot_style()
    df["survival_group_ja"] = df["survival_group"].map(_SURVIVAL_LABEL_MAP)
    plot_df = df[df["median_similarity"].notna()]

    absorber_df = plot_df[plot_df["survival_group_ja"] == "統合先"]
    deletion_df = plot_df[plot_df["survival_group_ja"].isin(["統合元", "削除"])]

    absorber_time_values = sorted(absorber_df["relative_time"].unique())
    deletion_time_values = sorted(deletion_df["relative_time"].unique())

    _plot_boxplot_absorber(absorber_df, absorber_time_values, output_boxplot_absorber)
    _plot_boxplot_deletion(deletion_df, deletion_time_values, output_boxplot_deletion)

    count_df = (
        plot_df.groupby(["relative_time", "survival_group_ja"]).size().reset_index(name="count")
    )
    absorber_counts, stacked_data, y_max = _prepare_area_data(
        count_df, absorber_time_values, deletion_time_values
    )
    _plot_area_absorber(absorber_counts, absorber_time_values, y_max, output_areaplot_absorber)
    _plot_area_deletion(stacked_data, deletion_time_values, y_max, output_areaplot_deletion)


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
    default="./output/versions/method_tracker/methods_tracked.csv",
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
def analyze_absorbed(
    input_file: str,
    input_tracking: str,
    input: str,
) -> None:
    """Analyze Absorbed methods: lifetime distribution and origin classification."""
    absorbed_t0 = _load_absorbed_data(input_file, input_tracking)
    absorbed_t0 = _classify_absorbed_origin(absorbed_t0, input)
    _print_absorbed_summary(absorbed_t0)
