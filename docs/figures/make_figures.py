"""Builds docs/figures/runs.csv and the figures from the Inspect logs in evals/logs/.

Run from the repo root:
  uv --project third_party/inspect-metr-task-bridge run --with pandas --with matplotlib \
      python docs/figures/make_figures.py
"""

import glob
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from inspect_ai.log import read_eval_log

OUT = "docs/figures"
FIRST, RETRY, OPENAI = "First sweep (default tools)", "Retry (tool-timeout note)", "OpenAI runs (tool-timeout note)"

# palette: categorical slots 1 and 2 (validated), de-emphasis gray, fixed status colors, text tokens
SURFACE, GRID = "#fcfcfb", "#e7e6e2"
INK, INK2, MUTED = "#0b0b0b", "#52514e", "#8c8b86"
GEN, TOOL, OTHER = "#2a78d6", "#eb6834", "#c9c8c3"
GOOD, CRIT = "#0ca30c", "#d03b3b"


# Publication dates: the `created` timestamp of each model on OpenRouter, read with the OpenRouter MCP (get-model) on
# 2026-10-11. This is the date OpenRouter listed the model, which may differ slightly from the vendor's announcement.
CREATED = {
    "opus-4.1": 1754411591, "opus-4.5": 1764010580, "opus-4.6": 1770219050, "opus-4.7": 1776351100,
    "opus-4.8": 1779905091, "opus-5": 1784912544, "opus-5.5": 1790094732,
    "sonnet-4": 1747930371, "sonnet-4.5": 1759161676, "sonnet-4.6": 1771342990, "sonnet-5": 1782843083,
    "sonnet-5.5": 1790618686, "haiku-4.5": 1760547638, "haiku-5.5": 1791397883,
    "gpt-4o-2024-11-20": 1732127594, "gpt-4.1": 1744651385, "gpt-oss-120b": 1754414231,
    "gpt-5.4-mini": 1773748178, "gpt-6-sol": 1790100775, "gpt-6-luna": 1790100786,
}
COMPANY = {"anthropic": "Anthropic", "openai": "OpenAI"}
VIOLET, AQUA = "#4a3aa7", "#1baf7a"  # categorical slots 7 and 3, validated as a pair (all-pairs)


def tool_text(result) -> str:
    if isinstance(result, str):
        return result
    return " ".join(getattr(c, "text", "") or "" for c in result or [])


# Route to the answer (figure 4). Solved runs are sorted by the tool seconds spent before the checker first said
# "correct answer"; the observed values fall into three groups with wide gaps (0-4 s, 46-52 s, 260 s and up).
DIRECT_MAX_S, DETOUR_MAX_S = 10, 120  # 120 s is about one tool timeout


def route(r) -> str:
    """✓ checker first, → brief brute-force detour, ↷ late pivot, ⏱ working limit hit, ✗ submitted a wrong answer."""
    if not r.solved:
        return "⏱" if r.ended_by == "working" else "✗"
    if pd.isna(r.to_answer_s):
        raise ValueError(f"solved run without a checker reply: {r.log}")
    return "✓" if r.to_answer_s <= DIRECT_MAX_S else "→" if r.to_answer_s <= DETOUR_MAX_S else "↷"


def collect() -> pd.DataFrame:
    rows = []
    for f in sorted(glob.glob("evals/logs/*.eval") + glob.glob("evals/logs/first_sweep/*.eval")):
        h = read_eval_log(f, header_only=True)
        model = h.eval.model
        tagged = "tool-timeout-note" in (h.eval.tags or [])
        image = h.eval.task_args.get("image_tag", "")
        if not model.startswith(("openrouter/anthropic", "openrouter/openai")) or not image.startswith("bruteforce_digits-"):
            continue
        log = read_eval_log(f, resolve_attachments=True)
        if not log.samples:
            continue
        smp = log.samples[0]
        gen = tool = 0.0
        timeouts = 0
        to_answer = None  # tool seconds spent before the checker first replied "correct answer"
        for e in smp.events:
            if e.event == "model":
                gen += e.working_time or 0
            elif e.event == "tool":
                if to_answer is None and e.function != "submit" and "correct answer" in tool_text(e.result).lower():
                    to_answer = tool
                tool += e.working_time or 0
                if getattr(e, "error", None) is not None and e.error.type == "timeout":
                    timeouts += 1
        score = list(smp.scores.values())[0].value if smp.scores else None
        provider = model.split("/")[1]
        group = FIRST if not tagged else (OPENAI if provider == "openai" else RETRY)
        rows.append(
            dict(
                group=group,
                model=model.split("/", 2)[2].replace("claude-", ""),
                provider=provider,
                created=h.eval.created,
                solved=score == 1.0,
                total_s=round(smp.total_time, 1),
                working_s=round(smp.working_time, 1),
                generation_s=round(gen, 1),
                tool_s=round(tool, 1),
                other_s=round(max(smp.working_time - gen - tool, 0), 1),
                to_answer_s=round(to_answer, 1) if score == 1.0 and to_answer is not None else None,
                messages=len(smp.messages),
                ended_by=smp.limit.type if smp.limit else "submit",
                timeouts=timeouts,
                log=os.path.basename(f),
            )
        )
    df = pd.DataFrame(rows).sort_values(["group", "working_s"]).reset_index(drop=True)
    # label repeated models in the same group
    dup = df.groupby(["group", "model"]).cumcount()
    n = df.groupby(["group", "model"])["model"].transform("count")
    df["label"] = df["model"] + (" #" + (dup + 1).astype(str)).where(n > 1, "")
    df["published"] = pd.to_datetime(df["model"].map(CREATED), unit="s").dt.date
    return df


def style(ax):
    ax.set_facecolor(SURFACE)
    for side in ("top", "right", "left"):
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(GRID)
    ax.tick_params(colors=INK2, length=0)
    ax.grid(axis="x", color=GRID, linewidth=1, zorder=0)
    ax.set_axisbelow(True)


def fig_timeline(df: pd.DataFrame):
    groups = [FIRST, RETRY, OPENAI]
    ratios = [max((df.group == g).sum(), 1) for g in groups]
    fig, axes = plt.subplots(3, 1, figsize=(11, 0.34 * sum(ratios) + 3.2), sharex=True,
                             gridspec_kw=dict(height_ratios=ratios, hspace=0.38), facecolor=SURFACE)
    xmax = 820
    for ax, g in zip(axes, groups):
        d = df[df.group == g].reset_index(drop=True)
        style(ax)
        y = range(len(d))
        ax.barh(y, d.generation_s, height=0.6, color=GEN, edgecolor=SURFACE, linewidth=2, zorder=3)
        ax.barh(y, d.tool_s, left=d.generation_s, height=0.6, color=TOOL, edgecolor=SURFACE, linewidth=2, zorder=3)
        ax.barh(y, d.other_s, left=d.generation_s + d.tool_s, height=0.6, color=OTHER, edgecolor=SURFACE, linewidth=2, zorder=3)
        ax.set_yticks(list(y))
        ax.set_yticklabels(d.label, color=INK, fontsize=9.5)
        ax.invert_yaxis()
        ax.set_ylim(len(d) - 0.4, -0.7)
        ax.axvline(600, color=MUTED, linewidth=1, zorder=2)
        for i, r in d.iterrows():
            icon, col = ("✓", GOOD) if r.solved else ("✗", CRIT)
            x = r.working_s + 8
            note = ""
            if r.total_s - r.working_s > 30:
                note += f" ({r.total_s:.0f} s wall clock)"
            if not r.solved:
                note += "  ended by the working limit" if r.ended_by == "working" else (
                    "  ended by the message limit" if r.ended_by == "message" else "  submitted a wrong answer")
            ax.text(x, i, icon, color=col, fontsize=11, fontweight="bold", va="center", ha="left", zorder=4)
            ax.text(x + 22, i, f"{r.working_s:.0f} s" + note, color=INK2, fontsize=8.5, va="center", ha="left", zorder=4)
        ns = int(d.solved.sum())
        ax.set_title(f"{g}: {ns} of {len(d)} solved", loc="left", color=INK, fontsize=10.5, fontweight="semibold", pad=6)
        ax.set_xlim(0, xmax)
    axes[0].text(600, -1.9, "600 s working limit", color=INK2, fontsize=8.5, ha="center", va="bottom")
    axes[-1].set_xlabel("Working time per sample (s)", color=INK2, fontsize=9.5)
    axes[-1].set_xticks(range(0, 801, 100))
    fig.suptitle("Where each run's working time went", x=0.02, y=0.985, ha="left", fontsize=14, fontweight="semibold", color=INK)
    fig.text(0.02, 0.945, f"Working time per run (the limit applies to this), split into model generation, tool calls and other overhead. "
             f"One sample per model; {len(df)} runs.", color=INK2, fontsize=9.5, ha="left")
    handles = [plt.Rectangle((0, 0), 1, 1, color=c) for c in (GEN, TOOL, OTHER)]
    leg = fig.legend(handles, ["Model generation", "Tool calls", "Other overhead"], loc="upper right",
                     bbox_to_anchor=(0.985, 0.985), ncol=3, frameon=False, fontsize=9.5, labelcolor=INK2)
    fig.savefig(f"{OUT}/fig1_time_per_run.png", dpi=150, facecolor=SURFACE, bbox_inches="tight")
    plt.close(fig)


def fig_scatter(df: pd.DataFrame):
    fig, ax = plt.subplots(figsize=(9.5, 6.3), facecolor=SURFACE)
    style(ax)
    ax.grid(axis="y", color=GRID, linewidth=1)
    ok, bad = df[df.solved], df[~df.solved]
    ax.scatter(ok.generation_s, ok.tool_s.clip(lower=0.3), s=70, color=GOOD, edgecolor=SURFACE, linewidth=2, zorder=3, marker="o")
    ax.scatter(bad.generation_s, bad.tool_s.clip(lower=0.3), s=80, color=CRIT, linewidth=2.4, zorder=3, marker="x")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlim(3, 320)
    ax.set_ylim(0.25, 4000)
    ax.set_xticks([5, 10, 20, 50, 100, 200])
    ax.set_xticklabels(["5", "10", "20", "50", "100", "200"])
    ax.set_yticks([1, 10, 100, 1000])
    ax.set_yticklabels(["1", "10", "100", "1,000"])
    ax.minorticks_off()
    ax.set_xlabel("Model generation time per run (s, log scale)", color=INK2, fontsize=9.5)
    ax.set_ylabel("Time in tool calls per run (s, log scale)", color=INK2, fontsize=9.5)
    # figure 1 carries the names; label only the points the title and subtitle talk about
    def tag(group, label, text, off, ha="left"):
        r = df[(df.group == group) & (df.label == label)].iloc[0]
        ax.annotate(text, (r.generation_s, max(r.tool_s, 0.3)), xytext=off, textcoords="offset points",
                    color=INK2, fontsize=8.5, va="center", ha=ha,
                    arrowprops=dict(arrowstyle="-", color=MUTED, linewidth=1, shrinkA=2, shrinkB=6))
    tag(OPENAI, "gpt-5.4-mini", "gpt-5.4-mini: fewest tool seconds of any failure", (14, -48))
    tag(OPENAI, "gpt-4o-2024-11-20", "gpt-4o: longest generation time", (-10, -75), ha="center")
    tag(RETRY, "sonnet-5", "sonnet-5 (retry): solved after 496 s in tools", (40, 45), ha="center")
    lo = int(bad.tool_s.min())
    n_slow_ok = int((ok.tool_s > 250).sum())
    n_gen_hi = int((df.generation_s > 110).sum())
    fig.suptitle(f"Every failed run spent {lo} s or more in tool calls", x=0.02, y=0.99, ha="left", fontsize=14,
                 fontweight="semibold", color=INK)
    fig.text(0.02, 0.935, f"{n_slow_ok} runs that solved the task also spent over 250 s in tools. "
             f"Generation time was under 110 s in {len(df) - n_gen_hi} of {len(df)} runs.", color=INK2, fontsize=9.5, ha="left")
    h = [plt.Line2D([], [], marker="o", color=SURFACE, markerfacecolor=GOOD, markersize=9, linestyle=""),
         plt.Line2D([], [], marker="x", color=CRIT, markersize=9, markeredgewidth=2.4, linestyle="")]
    ax.legend(h, ["✓ solved", "✗ failed"], loc="lower right", frameon=False, fontsize=9.5, labelcolor=INK2)
    fig.subplots_adjust(top=0.88)
    fig.savefig(f"{OUT}/fig2_generation_vs_tool_time.png", dpi=150, facecolor=SURFACE, bbox_inches="tight")
    plt.close(fig)


def fig_outcomes(df: pd.DataFrame):
    groups = [FIRST, RETRY, OPENAI]
    fig, ax = plt.subplots(figsize=(9.5, 3.4), facecolor=SURFACE)
    style(ax)
    ax.grid(axis="x", color=GRID, linewidth=1)
    for i, g in enumerate(groups):
        d = df[df.group == g]
        s, f = int(d.solved.sum()), int((~d.solved).sum())
        ax.barh(i, s, height=0.55, color=GOOD, edgecolor=SURFACE, linewidth=2, zorder=3)
        ax.barh(i, f, left=s, height=0.55, color=CRIT, edgecolor=SURFACE, linewidth=2, zorder=3)
        ax.text(s / 2, i, f"✓ {s}", color="white", fontsize=10, fontweight="bold", ha="center", va="center", zorder=4)
        if f:
            ax.text(s + f / 2, i, f"✗ {f}", color="white", fontsize=10, fontweight="bold", ha="center", va="center", zorder=4)
        ax.text(s + f + 0.3, i, f"{len(d)} runs", color=INK2, fontsize=9, va="center")
    ax.set_yticks(range(len(groups)))
    ax.set_yticklabels(groups, color=INK, fontsize=9.5)
    ax.invert_yaxis()
    ax.set_xlim(0, 19)
    ax.set_xticks([0, 5, 10, 15])
    ax.set_xlabel("Runs", color=INK2, fontsize=9.5)
    fig.suptitle("Most runs solved the task in every setup", x=0.02, y=1.02, ha="left", fontsize=14, fontweight="semibold", color=INK)
    fig.text(0.02, 0.93, "One epoch per model. The groups use different models and tools, so they are not a like-for-like comparison.",
             color=INK2, fontsize=9.5, ha="left")
    fig.subplots_adjust(top=0.82)
    fig.savefig(f"{OUT}/fig3_outcomes_by_group.png", dpi=150, facecolor=SURFACE, bbox_inches="tight")
    plt.close(fig)


def fig_release_timeline(df: pd.DataFrame, latest_only: bool = False):
    """latest_only drops first-sweep (0.2.0) runs of models that were rerun on 0.3.0."""
    import matplotlib.dates as mdates
    from matplotlib.transforms import ScaledTranslation

    df = df.copy()
    if latest_only:
        rerun = set(df[df.group != FIRST].model)
        df = df[(df.group != FIRST) | ~df.model.isin(rerun)]
    df["pub"] = pd.to_datetime(df["published"])
    lanes = [("Solved", True), ("Failed", False)]
    nrows = [df[df.solved == v].model.nunique() for _, v in lanes]
    fig, axes = plt.subplots(2, 1, figsize=(11, 0.33 * sum(nrows) + 3.0), sharex=True,
                             gridspec_kw=dict(height_ratios=nrows, hspace=0.32), facecolor=SURFACE)
    color = {"anthropic": VIOLET, "openai": AQUA}
    marker = {"anthropic": "o", "openai": "D"}
    for ax, (name, v) in zip(axes, lanes):
        style(ax)
        ax.grid(axis="x", color=GRID, linewidth=1)
        d = df[df.solved == v]
        order = d.groupby("model").pub.first().sort_values().index.tolist()
        for i, m in enumerate(order):
            runs = d[d.model == m]
            prov = runs.provider.iloc[0]
            for k, (_, r) in enumerate(runs.iterrows()):
                tr = ax.transData + ScaledTranslation(k * 11 / 72, 0, fig.dpi_scale_trans)
                ax.scatter([r.pub], [i], s=85, color=color[prov], marker=marker[prov], edgecolor=SURFACE,
                           linewidth=2, zorder=3, transform=tr)
            ax.text(runs.pub.iloc[0], i, "", va="center")
        ax.set_yticks(range(len(order)))
        ax.set_yticklabels(order, color=INK, fontsize=9.5)
        ax.invert_yaxis()
        ax.set_ylim(len(order) - 0.4, -0.7)
        ax.set_title(f"{name}: {len(d)} runs, {len(order)} models (oldest model at the top)", loc="left", color=INK,
                     fontsize=10.5, fontweight="semibold", pad=6)
    ax.xaxis.set_major_locator(mdates.MonthLocator(bymonth=[1, 4, 7, 10]))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
    ax.set_xlim(pd.Timestamp("2024-10-01"), pd.Timestamp("2026-11-15"))
    ax.set_xlabel("Model published on OpenRouter", color=INK2, fontsize=9.5)
    fig.suptitle("Release date does not separate solved from failed runs", x=0.02, y=0.985, ha="left", fontsize=14,
                 fontweight="semibold", color=INK)
    both = sorted(set(df[df.solved].model) & set(df[~df.solved].model))
    note = f" {', '.join(both)} appears in both lanes." if both else ""
    if latest_only:
        note += " Models rerun on 0.3.0 show only the 0.3.0 runs."
    fig.text(0.02, 0.945, "One dot per run, placed at the model's publication date. Repeated runs of a model sit side by side."
             + note, color=INK2, fontsize=9.5, ha="left")
    h = [plt.Line2D([], [], marker=marker[k], color=SURFACE, markerfacecolor=color[k], markersize=9, linestyle="")
         for k in ("anthropic", "openai")]
    fig.legend(h, ["Anthropic", "OpenAI"], loc="upper right", bbox_to_anchor=(0.985, 0.99), ncol=2, frameon=False,
               fontsize=9.5, labelcolor=INK2)
    fig.savefig(f"{OUT}/fig4_release_timeline{'_0.3.0_only' if latest_only else ''}.png", dpi=150, facecolor=SURFACE, bbox_inches="tight")
    plt.close(fig)


class Glyph:
    """Legend handle for a route mark: a text glyph, or the drawn clock when `ch` is "⏱" (DejaVu Sans lacks that glyph)."""

    def __init__(self, ch, color):
        self.ch, self.color = ch, color


def _clock_path():
    from matplotlib.path import Path
    c = Path.unit_circle()
    verts = list(c.vertices) + [(0, 0), (0, 0.62), (0, 0), (0.42, 0)]  # circle, minute hand up, hour hand right
    codes = list(c.codes) + [Path.MOVETO, Path.LINETO, Path.MOVETO, Path.LINETO]
    return Path(verts, codes)


CLOCK = _clock_path()


from matplotlib.legend_handler import HandlerBase


class GlyphHandler(HandlerBase):
    def create_artists(self, legend, orig_handle, xdescent, ydescent, width, height, fontsize, trans):
        from matplotlib.text import Text
        cx, cy = xdescent + width / 2, ydescent + height / 2
        if orig_handle.ch == "⏱":
            a = plt.Line2D([cx], [cy], linestyle="", marker=CLOCK, markersize=10, markerfacecolor="none",
                           markeredgecolor=orig_handle.color, markeredgewidth=1.6)
        else:
            a = Text(cx, cy, orig_handle.ch, color=orig_handle.color, fontsize=13, fontweight="bold", ha="center", va="center")
        a.set_transform(trans)
        return [a]


def fig_release_timeline_combined(df: pd.DataFrame):
    """Solved and failed runs in one panel, 0.3.0 runs only: first-sweep (0.2.0) runs of models rerun on 0.3.0 are dropped."""
    import matplotlib.dates as mdates
    FAIL_BG = "#f8e3e1"  # light tint of CRIT

    rerun = set(df[df.group != FIRST].model)
    df = df[(df.group != FIRST) | ~df.model.isin(rerun)].copy()
    df["pub"] = pd.to_datetime(df["published"])
    mixed = df.groupby("model").solved.nunique()
    if (mixed > 1).any():
        raise ValueError(f"models with differing results across runs: {sorted(mixed[mixed > 1].index)}")
    df["route"] = df.apply(route, axis=1)
    mixed_route = df.groupby("model").route.nunique()
    if (mixed_route > 1).any():
        raise ValueError(f"models with differing routes across runs: {sorted(mixed_route[mixed_route > 1].index)}")
    n_runs = len(df)
    df = df.drop_duplicates("model")
    order = df.groupby("model").pub.first().sort_values(kind="stable").index.tolist()
    fig, ax = plt.subplots(figsize=(11, 0.3 * len(order) + 2.6), facecolor=SURFACE)
    style(ax)
    marker = {"anthropic": "o", "openai": "D"}
    for i, m in enumerate(order):
        r = df[df.model == m].iloc[0]
        if r.solved:
            ax.scatter([r.pub], [i], s=85, color=GOOD, marker=marker[r.provider], edgecolor=SURFACE, linewidth=2, zorder=3)
        else:  # tinted row plus a hollow red marker, so failures differ in fill as well as hue
            ax.axhspan(i - 0.5, i + 0.5, xmin=-0.04, xmax=1, clip_on=False, color=FAIL_BG, linewidth=0, zorder=1)
            ax.scatter([r.pub], [i], s=85, facecolor=FAIL_BG, marker=marker[r.provider], edgecolor=CRIT, linewidth=2.4, zorder=3)
    # route column next to the model names (x in axes fraction, y in data units)
    col = -0.022
    ax.tick_params(axis="y", pad=26)
    ax.text(col, -1.15, "Route", transform=ax.get_yaxis_transform(), color=INK, fontsize=9, fontweight="semibold",
            ha="center", va="center", clip_on=False)
    for i, m in enumerate(order):
        mark = df[df.model == m].route.iloc[0]
        color = {"✓": GOOD, "→": INK2, "↷": INK2}.get(mark, CRIT)
        if mark == "⏱":
            ax.scatter([col], [i], s=95, marker=CLOCK, facecolor="none", edgecolor=color, linewidth=1.6,
                       transform=ax.get_yaxis_transform(), clip_on=False, zorder=4)
        else:
            ax.text(col, i, mark, transform=ax.get_yaxis_transform(), color=color, fontsize=13, fontweight="bold",
                    ha="center", va="center", clip_on=False)
    ax.set_yticks(range(len(order)))
    ax.set_yticklabels(order, color=INK, fontsize=9.5)
    ax.invert_yaxis()
    ax.set_ylim(len(order) - 0.4, -0.7)
    ax.xaxis.set_major_locator(mdates.MonthLocator(bymonth=[1, 4, 7, 10]))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
    ax.set_xlim(pd.Timestamp("2024-10-01"), pd.Timestamp("2026-11-15"))
    ax.set_xlabel("Model published on OpenRouter (oldest model at the top)", color=INK2, fontsize=9.5)
    fig.suptitle("Release date does not separate solved from failed runs", x=0.02, y=0.99, ha="left", fontsize=14,
                 fontweight="semibold", color=INK)
    fig.text(0.02, 0.945, f"One dot per model, placed at its publication date; {int(df.solved.sum())} solved, "
             f"{int((~df.solved).sum())} failed ({n_runs} runs; failed rows shaded). Models rerun on 0.3.0 use only their 0.3.0 runs.", color=INK2, fontsize=9.5, ha="left")
    h = [plt.Line2D([], [], marker="o", color=SURFACE, markerfacecolor=GOOD, markersize=9, linestyle=""),
         plt.Line2D([], [], marker="o", color=SURFACE, markerfacecolor=FAIL_BG, markeredgecolor=CRIT, markeredgewidth=2.4,
                    markersize=9, linestyle=""),
         plt.Line2D([], [], marker="o", color=SURFACE, markerfacecolor=MUTED, markersize=9, linestyle=""),
         plt.Line2D([], [], marker="D", color=SURFACE, markerfacecolor=MUTED, markersize=9, linestyle="")]
    fig.legend(h, ["Solved", "Failed", "Anthropic (circle)", "OpenAI (diamond)"], loc="upper left",
               bbox_to_anchor=(0.015, 0.925), ncol=4, frameon=False, fontsize=9.5, labelcolor=INK2)
    keys = [(Glyph("✓", GOOD), "checker first"),
            (Glyph("→", INK2), f"brute-force detour, then checker (under {DETOUR_MAX_S} s of tool time)"),
            (Glyph("↷", INK2), f"late pivot to the checker (over {DETOUR_MAX_S} s)"),
            (Glyph("⏱", CRIT), "working limit hit"), (Glyph("✗", CRIT), "wrong answer submitted")]
    fig.legend([k for k, _ in keys], [t for _, t in keys], handler_map={Glyph: GlyphHandler()}, loc="upper left", bbox_to_anchor=(0.015, 0.885), ncol=5,
               frameon=False, fontsize=9, labelcolor=INK2, columnspacing=1.2, handletextpad=0.2, handlelength=1.4)
    fig.subplots_adjust(top=0.81)
    fig.savefig(f"{OUT}/fig4_release_timeline_0.3.0_only.png", dpi=150, facecolor=SURFACE, bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    df = collect()
    df.drop(columns=["created"]).to_csv(f"{OUT}/runs.csv", index=False)
    pd.DataFrame(
        [(m, pd.to_datetime(t, unit="s").date()) for m, t in sorted(CREATED.items(), key=lambda kv: kv[1])],
        columns=["model", "published_on_openrouter"],
    ).to_csv(f"{OUT}/model_dates.csv", index=False)
    print(df.groupby("group").agg(runs=("solved", "size"), solved=("solved", "sum")))
    fig_timeline(df)
    fig_scatter(df)
    fig_outcomes(df)
    fig_release_timeline(df)
    fig_release_timeline_combined(df)
