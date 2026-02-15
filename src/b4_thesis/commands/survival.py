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
    nonnull_count_df: pd.DataFrame,
    null_count_df: pd.DataFrame,
    absorber_time_values: list[int],
    deletion_time_values: list[int],
) -> tuple[list[int], list[int], dict[str, list[int]], dict[str, list[int]], float]:
    """面グラフ用のカウントデータを整形し、共通のy_maxを計算する。

    Returns:
        (absorber_counts, null_absorber_counts, stacked_data, null_stacked_data, y_max)
    """

    def _extract_counts(
        count_df: pd.DataFrame, group_name: str, time_values: list[int]
    ) -> list[int]:
        group_data = count_df[count_df["survival_group_ja"] == group_name]
        count_by_time = dict(zip(group_data["relative_time"], group_data["count"]))
        return [count_by_time.get(t, 0) for t in time_values]

    # 非nullカウント
    absorber_counts = _extract_counts(nonnull_count_df, "統合先", absorber_time_values)
    stacked_data = {
        g: _extract_counts(nonnull_count_df, g, deletion_time_values) for g in ["統合元", "削除"]
    }

    # nullカウント
    null_absorber_counts = _extract_counts(null_count_df, "統合先", absorber_time_values)
    null_stacked_data = {
        g: _extract_counts(null_count_df, g, deletion_time_values) for g in ["統合元", "削除"]
    }

    # 合計（非null + null）に基づくy_max
    max_absorber = (
        max(a + b for a, b in zip(absorber_counts, null_absorber_counts)) if absorber_counts else 0
    )
    max_deletion = (
        max(
            a + b + c + d
            for a, b, c, d in zip(
                stacked_data["統合元"],
                stacked_data["削除"],
                null_stacked_data["統合元"],
                null_stacked_data["削除"],
            )
        )
        if stacked_data["統合元"]
        else 0
    )
    y_max = max(max_absorber, max_deletion) * 1.05

    return absorber_counts, null_absorber_counts, stacked_data, null_stacked_data, y_max


def _plot_area_absorber(
    absorber_counts: list[int],
    null_absorber_counts: list[int],
    time_values: list[int],
    y_max: float,
    output_path: str,
) -> None:
    """統合先群の面グラフを描画・保存する（null/非null積み上げ）。"""
    fig, ax = plt.subplots(figsize=(12, 4))
    if absorber_counts or null_absorber_counts:
        positions = list(range(len(time_values)))
        total = [a + b for a, b in zip(absorber_counts, null_absorber_counts)]
        color = _SURVIVAL_COLORS["統合先"]

        # null層（下）
        ax.fill_between(
            positions,
            null_absorber_counts,
            color=color,
            alpha=0.3,
            hatch="///",
            label="統合先（類似度なし）",
        )
        # 非null層（上）
        ax.fill_between(
            positions,
            null_absorber_counts,
            total,
            color=color,
            alpha=0.7,
            label="統合先",
        )
        ax.plot(positions, total, color=color, linewidth=1.5)

    ax.set_xlabel("相対時間 (0 = 統合直前のバージョン)", labelpad=10)
    ax.set_ylabel("メソッド数", labelpad=10)
    ax.grid(True, alpha=0.3, linestyle="--")
    handles, labels = ax.get_legend_handles_labels()
    ax.legend(
        handles[::-1], labels[::-1], loc="upper left", frameon=True, fancybox=True, shadow=True
    )
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
    null_stacked_data: dict[str, list[int]],
    time_values: list[int],
    y_max: float,
    output_path: str,
) -> None:
    """統合元+削除群の積み上げ面グラフを描画・保存する（null/非null積み上げ）。"""
    fig, ax = plt.subplots(figsize=(12, 4))

    positions = list(range(len(time_values)))

    # 4層の累積値（下から: null削除, 非null削除, null統合元, 非null統合元）
    nn_absorbed = stacked_data["統合元"]
    nn_deleted = stacked_data["削除"]
    null_absorbed = null_stacked_data["統合元"]
    null_deleted = null_stacked_data["削除"]

    y0 = [0] * len(positions)
    y1 = list(null_deleted)
    y2 = [a + b for a, b in zip(y1, nn_deleted)]
    y3 = [a + b for a, b in zip(y2, null_absorbed)]
    y4 = [a + b for a, b in zip(y3, nn_absorbed)]

    # null 削除（下、ハッチング）
    ax.fill_between(
        positions,
        y0,
        y1,
        color=_SURVIVAL_COLORS["削除"],
        alpha=0.3,
        hatch="///",
        label="削除（類似度なし）",
    )
    # 非null 削除
    ax.fill_between(
        positions,
        y1,
        y2,
        color=_SURVIVAL_COLORS["削除"],
        alpha=0.7,
        label="削除",
    )
    # null 統合元（ハッチング）
    ax.fill_between(
        positions,
        y2,
        y3,
        color=_SURVIVAL_COLORS["統合元"],
        alpha=0.3,
        hatch="///",
        label="統合元（類似度なし）",
    )
    # 非null 統合元
    ax.fill_between(
        positions,
        y3,
        y4,
        color=_SURVIVAL_COLORS["統合元"],
        alpha=0.7,
        label="統合元",
    )

    ax.set_xlabel("相対時間 (0 = 統合または削除直前のバージョン)", labelpad=10)
    ax.set_ylabel("メソッド数", labelpad=10)
    ax.grid(True, alpha=0.3, linestyle="--")
    handles, labels = ax.get_legend_handles_labels()
    ax.legend(
        handles[::-1], labels[::-1], loc="upper left", frameon=True, fancybox=True, shadow=True
    )
    ax.set_xticks(positions)
    ax.set_xticklabels([str(t) if t % 2 == 0 else "" for t in time_values])
    ax.set_xlim(-0.5, len(time_values) - 0.5)
    ax.set_ylim(0, y_max)

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches="tight", facecolor="white", edgecolor="none")
    plt.close()
    console.print(f"[green]Area plot (deletion) saved to:[/green] {output_path}")


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

    # 2. relative_time 計算
    df = _compute_relative_time(df)

    # 3. CSV出力 + サマリー表示
    df.to_csv(output_csv, index=False)
    for t in [1, 0, -1]:
        t_df = df[df["relative_time"] == t]
        nonnull = t_df[t_df["median_similarity"].notna()].groupby("survival_group").size()
        null = t_df[t_df["median_similarity"].isna()].groupby("survival_group").size()
        console.print(f"relative_time = {t}:")
        console.print(f"  非null: {nonnull.to_dict()}")
        console.print(f"  null:   {null.to_dict()}")
    console.print(f"[green]Data with survival groups saved to:[/green] {output_csv}")

    # 4. プロット
    _setup_plot_style()
    df["survival_group_ja"] = df["survival_group"].map(_SURVIVAL_LABEL_MAP)
    plot_df = df[df["median_similarity"].notna()]
    null_df = df[df["median_similarity"].isna()]

    # 箱ひげ図（非nullのみ）
    absorber_df = plot_df[plot_df["survival_group_ja"] == "統合先"]
    deletion_df = plot_df[plot_df["survival_group_ja"].isin(["統合元", "削除"])]

    absorber_time_values = sorted(absorber_df["relative_time"].unique())
    deletion_time_values = sorted(deletion_df["relative_time"].unique())

    _plot_boxplot_absorber(absorber_df, absorber_time_values, output_boxplot_absorber)
    _plot_boxplot_deletion(deletion_df, deletion_time_values, output_boxplot_deletion)

    # 面グラフ（全データからtime_valuesを算出）
    area_absorber_df = df[df["survival_group_ja"] == "統合先"]
    area_deletion_df = df[df["survival_group_ja"].isin(["統合元", "削除"])]
    area_absorber_time_values = sorted(area_absorber_df["relative_time"].unique())
    area_deletion_time_values = sorted(area_deletion_df["relative_time"].unique())

    nonnull_count_df = (
        plot_df.groupby(["relative_time", "survival_group_ja"]).size().reset_index(name="count")
    )
    null_count_df = (
        null_df.groupby(["relative_time", "survival_group_ja"]).size().reset_index(name="count")
    )

    absorber_counts, null_absorber_counts, stacked_data, null_stacked_data, y_max = (
        _prepare_area_data(
            nonnull_count_df, null_count_df, area_absorber_time_values, area_deletion_time_values
        )
    )
    _plot_area_absorber(
        absorber_counts,
        null_absorber_counts,
        area_absorber_time_values,
        y_max,
        output_areaplot_absorber,
    )
    _plot_area_deletion(
        stacked_data,
        null_stacked_data,
        area_deletion_time_values,
        y_max,
        output_areaplot_deletion,
    )


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
def analyze_absorbed(
    input_file: str,
    input_tracking: str,
) -> None:
    """Analyze Absorbed methods: lifetime distribution and origin classification."""
    deletion_survival_df = pd.read_csv(input_file)
    method_info_df = pd.read_csv(input_tracking)
    
    df = deletion_survival_df.merge(method_info_df, on=["method_id", "prev_revision_id"], how="left", suffixes=("", "_info"))
    sort_method_info_df = df.sort_values(["method_id", "prev_revision_id"], ascending=[True, False])
    
    absorbed_df = sort_method_info_df[sort_method_info_df["survival_group"] == "Absorbed"]
    
    # t = 0 
    absorbed_time_0 = absorbed_df[absorbed_df["relative_time"] == 0].copy()
    console.print(f"Total Absorbed Methods: {len(absorbed_time_0)}")
    # t = -1
    absorbed_time_minus1 = absorbed_df[absorbed_df["relative_time"] == -1].copy()
    console.print(f"Absorbed Methods at t=-1: {len(absorbed_time_minus1)}")
    # t = -2
    absorbed_time_minus2 = absorbed_df[absorbed_df["relative_time"] == -2].copy()
    console.print(f"Absorbed Methods at t=-2: {len(absorbed_time_minus2)}")
    # t = -3
    absorbed_time_minus3 = absorbed_df[absorbed_df["relative_time"] == -3].copy()
    console.print(f"Absorbed Methods at t=-3: {len(absorbed_time_minus3)}")
    # t = -10
    absorbed_time_minus10 = absorbed_df[absorbed_df["relative_time"] == -10].copy()
    console.print(f"Absorbed Methods at t=-10: {len(absorbed_time_minus10)}")
    # t = -11
    absorbed_time_minus11 = absorbed_df[absorbed_df["relative_time"] == -11].copy()
    console.print(f"Absorbed Methods at t=-11: {len(absorbed_time_minus11)}")
    
    # 一時複製型メソッドID
    unique_method_ids = set(absorbed_time_0["method_id"].unique()) - set(absorbed_time_minus1["method_id"].unique())
    # 段階的収束型メソッドID
    gradually_absorbed_ids = set(absorbed_time_minus1["method_id"].unique())
    console.print(f"Unique Absorbed Method IDs (t=0 only): {len(unique_method_ids)}")
    # 生存期間が2回のメソッドID
    survived_2_ids = set(absorbed_time_minus2["method_id"].unique()) - set(absorbed_time_minus3["method_id"].unique())
    console.print(f"Survived 2 Revisions Method IDs: {len(survived_2_ids)}")
    # 生存期間が10回のメソッドID
    survived_10_ids = set(absorbed_time_minus10["method_id"].unique()) - set(absorbed_time_minus11["method_id"].unique())
    console.print(f"Survived 10 Revisions Method IDs: {len(survived_10_ids)}")

    # t=0での段階的収束型メソッド
    method_info_t0 = absorbed_time_0[absorbed_time_0["method_id"].isin(gradually_absorbed_ids)]
    console.print(f"[blue]Gradually Absorbed Methods (t=-1 present): {method_info_t0["median_similarity"].describe()}[/blue]")
    console.print((method_info_t0["median_similarity"] == 100).sum())
    
    # t = 0での一時複製型メソッド
    method_info_minus1 = absorbed_time_0[absorbed_time_0["method_id"].isin(unique_method_ids)]
    console.print(f"[blue]Unique Absorbed Methods (t=0 only): {method_info_minus1["median_similarity"].describe()}[/blue]")
    console.print((method_info_minus1["median_similarity"] == 100).sum())
    
    # lifetime=2のメソッドのt = -2での生存分析
    method_info_life_2 = absorbed_time_minus2[absorbed_time_minus2["method_id"].isin(survived_2_ids)]
    console.print(f"method count : {len(method_info_life_2)}")
    console.print(f"[blue]Absorbed Methods Survived 2 Revisions (at t=-2): {method_info_life_2["median_similarity"].describe()}[/blue]")
    console.print((method_info_life_2["median_similarity"] == 100).sum())
    
    # lifetime=2のメソッドのt = -1での生存分析
    method_info_life_2 = absorbed_time_minus1[absorbed_time_minus1["method_id"].isin(survived_2_ids)]
    console.print(f"method count : {len(method_info_life_2)}")
    console.print(f"[blue]Absorbed Methods Survived 2 Revisions (at t=-1): {method_info_life_2["median_similarity"].describe()}[/blue]")
    console.print((method_info_life_2["median_similarity"] == 100).sum())
    
    # lifetime=10のメソッドのt=-2での生存分析
    method_info_life_10_at_2 = absorbed_time_minus2[absorbed_time_minus2["method_id"].isin(survived_10_ids)]
    console.print(f"method count : {len(method_info_life_10_at_2)}")
    console.print(f"[blue]Absorbed Methods Survived 10 Revisions (at t=-2): {method_info_life_10_at_2["median_similarity"].describe()}[/blue]")
    console.print((method_info_life_10_at_2["median_similarity"] == 100).sum())
    
    # lifetime=10のメソッドのt=-10での生存分析
    method_info_life_10 = absorbed_time_minus10[absorbed_time_minus10["method_id"].isin(survived_10_ids)]
    console.print(f"method count : {len(method_info_life_10)}")
    console.print(f"[blue]Absorbed Methods Survived 10 Revisions (at t=-10): {method_info_life_10["median_similarity"].describe()}[/blue]")
    console.print((method_info_life_10["median_similarity"] == 100).sum())
    
    
    absorber_df = sort_method_info_df[(sort_method_info_df["survival_group"] == "Absorber") & (sort_method_info_df["relative_time"] == 0)]
    high_similarity_absorbers = absorber_df[absorber_df["median_similarity"] == 100]
    console.print(f"[blue]Absorber Methods at t=0 with 100% Similarity: {len(high_similarity_absorbers)}[/blue]")
    console.print(absorber_df["median_similarity"].describe())
    
    
    # # 段階的収束型メソッドの生存分析
    # gradually_absorbed_methods = method_info_t0[method_info_t0["method_id"].isin(gradually_absorbed_ids)]
    # # 段階的収束型メソッドのt=0での分析
    # console.print(f"[blue]Gradually Absorbed Methods (t=-1 present): {gradually_absorbed_methods["median_similarity"].describe()}[/blue]")
    # console.print((gradually_absorbed_methods["median_similarity"] == 100).sum())
    
    # # 一時的複製型メソッドの生存分析
    # temporary_absorbed_methods = method_info_t0[method_info_t0["method_id"].isin(unique_method_ids)]
    
    
    # console.print(f"[blue]Unique Absorbed Methods (t=0 only): {len(unique_method_ids)}[/blue]")
    
    # added_to_merged = method_info_df[method_info_df["method_id"].isin(unique_method_ids)]
    # console.print(f"[blue]Details of Unique Absorbed Methods: {len(added_to_merged)}[/blue]")
    
    # # 以下は分析例
    # console.print(added_to_merged["median_similarity"].describe())
    
    # # added_to_mergedのprev_file_pathの文字列にtestがどれだけ含まれるか
    # test_count = added_to_merged["prev_file_path"].str.contains("test", case=False, na=False).sum()
    # console.print(f"[blue]Number of Unique Absorbed Methods in Test Files: {test_count}[/blue]")
    
    # # added_to_mergedのprev_method_nameの一覧
    # unique_prev_method_names = added_to_merged["prev_method_name"].unique()
    # console.print(f"[blue]Unique Previous Method Names of Absorbed Methods: {len(unique_prev_method_names)}[/blue]")
    # # ランキング上位10件を表示
    # top_prev_method_names = (
    #     added_to_merged["prev_method_name"]
    #     .value_counts()
    #     .head(15)
    # )
    # console.print("[blue]Top 10 Previous Method Names of Absorbed Methods:[/blue]")
    # console.print(top_prev_method_names)