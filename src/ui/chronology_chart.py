"""Build chronology timeline chart for Iron Age sub-periods."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from .archaeo_palettes import PERIODE_COLORS, SUB_PERIODS


def build_chronology(df: pd.DataFrame) -> go.Figure:
    """Horizontal bar chart: one bar per broad sub-period, annotated with site count."""
    counts = _count_sites_per_subperiod(df)

    fig = go.Figure()
    prev_parent: str | None = None

    for label, start, end, parent in SUB_PERIODS:
        count = counts.get(label, 0)
        color = PERIODE_COLORS.get(parent, "#999")
        show_legend = parent != prev_parent
        prev_parent = parent

        fig.add_trace(go.Bar(
            y=[label],
            x=[abs(start - end)],
            base=[start],
            orientation="h",
            marker=dict(color=color, opacity=0.75, line=dict(color=color, width=1)),
            name=parent,
            showlegend=show_legend,
            legendgroup=parent,
            text=f"  {count}" if count else "",
            textposition="inside",
            textfont=dict(color="white", size=11, family="Inter, sans-serif"),
            hovertemplate=(
                f"<b>{label}</b> ({parent})<br>"
                f"{abs(start)} – {abs(end)} av. J.-C.<br>"
                f"{count} site{'s' if count != 1 else ''}"
                "<extra></extra>"
            ),
        ))

    fig.update_layout(
        barmode="stack",
        xaxis=dict(
            title=dict(text="av. J.-C.", font=dict(size=11)),
            autorange="reversed",
            showgrid=True,
            gridcolor="rgba(255,255,255,0.06)",
            tickformat="d",
            color="#7e80a0",
        ),
        yaxis=dict(autorange="reversed", color="#e0e0e8", tickfont=dict(size=12)),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=55, r=15, t=8, b=35),
        height=210,
        legend=dict(
            bgcolor="rgba(0,0,0,0)",
            font=dict(color="#e0e0e8", size=11),
        ),
    )
    return fig


def _count_sites_per_subperiod(df: pd.DataFrame) -> dict[str, int]:
    counts: dict[str, int] = {}
    if df.empty or "sous_periodes" not in df.columns:
        return counts
    for sp_cell in df["sous_periodes"].dropna():
        for label, *_ in SUB_PERIODS:
            if label in str(sp_cell):
                counts[label] = counts.get(label, 0) + 1
    return counts
