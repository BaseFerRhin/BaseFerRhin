"""Build Plotly map figure for archaeological sites."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from .archaeo_palettes import MAP_CENTER, MAP_ZOOM, PERIODE_COLORS, TYPE_SITE_COLORS


def build_site_map(df: pd.DataFrame, color_by: str = "type_site") -> go.Figure:
    """Return a Scattermapbox figure with one trace per category for the legend."""
    df_geo = df.dropna(subset=["latitude", "longitude"]) if not df.empty else df
    if df_geo.empty:
        return _empty_map()

    color_map = TYPE_SITE_COLORS if color_by == "type_site" else PERIODE_COLORS
    fig = go.Figure()

    for cat, color in color_map.items():
        mask = df_geo[color_by] == cat
        if not mask.any():
            continue
        subset = df_geo[mask]
        custom = subset[["type_site", "periodes", "commune", "pays"]].values
        fig.add_trace(go.Scattermapbox(
            lat=subset["latitude"],
            lon=subset["longitude"],
            mode="markers",
            marker=dict(size=13, color=color, opacity=0.88),
            name=cat.capitalize() if cat[0].islower() else cat,
            text=subset["nom_site"],
            customdata=custom,
            hovertemplate=(
                "<b>%{text}</b><br>"
                "Type : %{customdata[0]}<br>"
                "Période : %{customdata[1]}<br>"
                "%{customdata[2]}, %{customdata[3]}"
                "<extra></extra>"
            ),
        ))

    _apply_layout(fig)
    return fig


def _empty_map() -> go.Figure:
    fig = go.Figure(go.Scattermapbox())
    _apply_layout(fig)
    return fig


def _apply_layout(fig: go.Figure) -> None:
    fig.update_layout(
        mapbox=dict(
            style="open-street-map",
            center=dict(lat=MAP_CENTER["lat"], lon=MAP_CENTER["lon"]),
            zoom=MAP_ZOOM,
        ),
        margin=dict(l=0, r=0, t=0, b=0),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        legend=dict(
            bgcolor="rgba(22,24,45,0.85)",
            font=dict(color="white", size=11),
            bordercolor="rgba(42,45,80,0.6)",
            borderwidth=1,
            orientation="v",
            yanchor="top",
            y=0.98,
            xanchor="left",
            x=0.01,
        ),
        height=520,
    )
