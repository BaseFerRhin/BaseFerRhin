"""Dash callbacks — filtering, map interaction, detail panel."""

from __future__ import annotations

from dash import Dash, Input, Output, State, callback_context, html, no_update
import pandas as pd

from .archaeo_palettes import PAYS_COLORS, TYPE_SITE_COLORS
from .chronology_chart import build_chronology
from .site_map import build_site_map


def register_callbacks(app: Dash) -> None:
    @app.callback(
        Output("site-map", "figure"),
        Output("chronology-chart", "figure"),
        Output("site-table", "data"),
        Output("stats-content", "children"),
        Input("filter-periode", "value"),
        Input("filter-type", "value"),
        Input("filter-pays", "value"),
        Input("color-by", "value"),
        State("full-data", "data"),
    )
    def update_views(periodes, types, pays, color_by, data):
        df = pd.DataFrame(data)
        df = _apply_filters(df, periodes, types, pays)

        table_df = df.copy()
        for col in table_df.columns:
            if table_df[col].apply(lambda x: isinstance(x, (list, dict))).any():
                table_df[col] = table_df[col].apply(
                    lambda x: ", ".join(str(i) for i in x) if isinstance(x, list) else str(x) if isinstance(x, dict) else x
                )

        return (
            build_site_map(df, color_by=color_by),
            build_chronology(df),
            table_df.to_dict("records"),
            _build_stats(df),
        )

    @app.callback(
        Output("site-detail", "is_open"),
        Output("site-detail", "title"),
        Output("site-detail-content", "children"),
        Input("site-map", "clickData"),
        Input("site-table", "selected_rows"),
        State("site-table", "data"),
        prevent_initial_call=True,
    )
    def show_detail(click_data, selected_rows, data):
        trigger = (callback_context.triggered or [{}])[0].get("prop_id", "")

        if "site-map" in trigger and click_data:
            name = click_data["points"][0].get("text", "")
            for row in data:
                if row.get("nom_site") == name:
                    return True, name, _build_detail(row)

        if "site-table" in trigger and selected_rows:
            row = data[selected_rows[0]]
            return True, row.get("nom_site", ""), _build_detail(row)

        return False, no_update, no_update


# -- filtering ---------------------------------------------------------------

def _apply_filters(
    df: pd.DataFrame,
    periodes: list[str] | None,
    types: list[str] | None,
    pays: list[str] | None,
) -> pd.DataFrame:
    if periodes:
        pattern = "|".join(periodes)
        df = df[df["periodes"].str.contains(pattern, na=False)]
    if types:
        df = df[df["type_site"].isin(types)]
    if pays:
        df = df[df["pays"].isin(pays)]
    return df


# -- stats panel -------------------------------------------------------------

def _build_stats(df: pd.DataFrame) -> list:
    total = len(df)
    geo = df[["latitude", "longitude"]].dropna().shape[0]

    type_counts = df["type_site"].value_counts()
    type_items = [
        html.Div([
            html.Span("\u25cf ", style={"color": TYPE_SITE_COLORS.get(t, "#999")}),
            html.Span(f"{t} ", className="fw-bold"),
            html.Span(str(c)),
        ], className="small")
        for t, c in type_counts.items()
    ]

    pays_counts = df["pays"].value_counts()
    pays_items = [
        html.Span([
            html.Span(f" {p} ", style={
                "backgroundColor": PAYS_COLORS.get(p, "#555"),
                "color": "white",
                "borderRadius": "3px",
                "padding": "1px 6px",
                "fontSize": "0.75rem",
                "fontWeight": "600",
                "marginRight": "6px",
            }),
            html.Span(f"{c}  ", className="small"),
        ])
        for p, c in pays_counts.items()
    ]

    return [
        html.Div([
            html.Span(str(total), className="stat-number"),
            html.Span(" sites", className="stat-label"),
        ]),
        html.Div([
            html.Span(str(geo), className="stat-number-sm"),
            html.Span(f" / {total} géolocalisés", className="stat-label"),
        ], className="mt-1"),
        html.Hr(),
        html.Div(type_items, className="mb-2"),
        html.Hr(),
        html.Div(pays_items),
    ]


# -- detail panel ------------------------------------------------------------

_FIELDS = [
    ("Site", "nom_site"),
    ("Type", "type_site"),
    ("Période", "periodes"),
    ("Sous-période", "sous_periodes"),
    ("Commune", "commune"),
    ("Pays", "pays"),
    ("Région", "region_admin"),
    ("Latitude", "latitude"),
    ("Longitude", "longitude"),
    ("Précision", "precision_localisation"),
    ("Altitude", "altitude_m"),
    ("Surface", "surface_m2"),
    ("Fouille", "statut_fouille"),
    ("Sources", "sources"),
]


def _build_detail(row: dict) -> html.Div:
    items: list = []
    for label, key in _FIELDS:
        val = row.get(key)
        if not val and val != 0:
            continue
        items.extend([
            html.Dt(label, className="small text-muted mt-2"),
            html.Dd(str(val), className="mb-0"),
        ])

    deb = row.get("datation_debut")
    fin = row.get("datation_fin")
    if deb is not None:
        items.extend([
            html.Dt("Datation", className="small text-muted mt-2"),
            html.Dd(f"{abs(int(deb))} – {abs(int(fin))} av. J.-C." if fin else str(deb)),
        ])

    desc = row.get("description")
    if desc:
        items.append(html.Hr())
        items.append(html.P(str(desc), className="small fst-italic", style={"color": "#7e80a0"}))

    return html.Div([html.Dl(items)])
