"""Dash layout — sidebar filters + map + chronology + table."""

from __future__ import annotations

from dash import dash_table, dcc, html
import dash_bootstrap_components as dbc
import pandas as pd


def create_layout(df: pd.DataFrame) -> dbc.Container:
    type_opts = _dropdown_opts(df, "type_site")
    periode_opts = _dropdown_opts(df, "periodes")
    pays_opts = _dropdown_opts(df, "pays")

    return dbc.Container([
        dcc.Store(id="full-data", data=df.to_dict("records")),
        _navbar(),
        dbc.Row([
            dbc.Col([_filters_card(type_opts, periode_opts, pays_opts), _stats_card()],
                    md=3, className="sidebar-col"),
            dbc.Col([_map_card(), _chrono_card(), _table_card()], md=9),
        ], className="g-3 mt-2 mx-1"),
        _detail_panel(),
    ], fluid=True, className="app-container")


# -- private builders --------------------------------------------------------

def _navbar() -> dbc.Navbar:
    return dbc.Navbar(
        dbc.Container([
            dbc.Row([dbc.Col(html.Div([
                html.H4("BaseFerRhin", className="mb-0 fw-bold",
                         style={"color": "#C47D3B", "letterSpacing": "-0.5px"}),
                html.Small("Sites de l'âge du Fer — Rhin supérieur",
                           className="text-muted"),
            ]))], align="center"),
        ], fluid=True),
        dark=True, color="dark", className="mb-0",
    )


def _filters_card(type_opts, periode_opts, pays_opts) -> dbc.Card:
    return dbc.Card([
        dbc.CardHeader(html.H6("Filtres", className="mb-0")),
        dbc.CardBody([
            _label("Période"),
            dcc.Dropdown(id="filter-periode", options=periode_opts,
                         multi=True, placeholder="Toutes les périodes", className="mb-3"),
            _label("Type de site"),
            dcc.Dropdown(id="filter-type", options=type_opts,
                         multi=True, placeholder="Tous les types", className="mb-3"),
            _label("Pays"),
            dbc.Checklist(id="filter-pays", options=pays_opts,
                          value=[o["value"] for o in pays_opts], inline=True, className="mb-3"),
            _label("Colorer par"),
            dbc.RadioItems(
                id="color-by",
                options=[
                    {"label": "Type de site", "value": "type_site"},
                    {"label": "Période", "value": "periodes"},
                ],
                value="type_site", inline=True,
            ),
        ]),
    ], className="mb-3")


def _stats_card() -> dbc.Card:
    return dbc.Card([
        dbc.CardHeader(html.H6("Statistiques", className="mb-0")),
        dbc.CardBody(id="stats-content"),
    ], className="mb-3")


def _map_card() -> dbc.Card:
    return dbc.Card([
        dbc.CardBody([
            dcc.Graph(id="site-map", config={"scrollZoom": True},
                      style={"height": "520px"}),
        ], className="p-1"),
    ], className="mb-3")


def _chrono_card() -> dbc.Card:
    return dbc.Card([
        dbc.CardHeader(html.H6("Frise chronologique", className="mb-0")),
        dbc.CardBody([
            dcc.Graph(id="chronology-chart", config={"displayModeBar": False}),
        ], className="p-1"),
    ], className="mb-3")


def _table_card() -> dbc.Card:
    columns = [
        {"name": "Site", "id": "nom_site"},
        {"name": "Type", "id": "type_site"},
        {"name": "Période", "id": "periodes"},
        {"name": "Sous-pér.", "id": "sous_periodes"},
        {"name": "Commune", "id": "commune"},
        {"name": "Pays", "id": "pays"},
    ]
    return dbc.Card([
        dbc.CardHeader(html.H6("Inventaire des sites", className="mb-0")),
        dbc.CardBody([
            dash_table.DataTable(
                id="site-table",
                columns=columns,
                data=[],
                sort_action="native",
                filter_action="native",
                page_size=12,
                row_selectable="single",
                style_table={"overflowX": "auto"},
                style_header=_table_header_style(),
                style_cell=_table_cell_style(),
                style_data_conditional=[{
                    "if": {"state": "selected"},
                    "backgroundColor": "#2a2d5a",
                    "border": "1px solid #D95F02",
                }],
                style_filter={"backgroundColor": "#1e2040", "color": "#e0e0e8"},
            ),
        ]),
    ])


def _detail_panel() -> dbc.Offcanvas:
    return dbc.Offcanvas(
        id="site-detail", title="Détail du site", placement="end",
        is_open=False, children=[html.Div(id="site-detail-content")],
        style={"width": "380px"},
    )


# -- helpers -----------------------------------------------------------------

def _label(text: str):
    return dbc.Label(text, className="fw-bold small mb-1")


def _dropdown_opts(df: pd.DataFrame, col: str) -> list[dict]:
    vals = sorted(df[col].dropna().unique())
    return [{"label": v.capitalize() if v[0:1].islower() else v, "value": v} for v in vals if v]


def _table_header_style() -> dict:
    return {
        "backgroundColor": "#1e2040",
        "color": "#e0e0e8",
        "fontWeight": "bold",
        "border": "1px solid #2a2d50",
        "fontSize": "13px",
    }


def _table_cell_style() -> dict:
    return {
        "backgroundColor": "#16182d",
        "color": "#e0e0e8",
        "border": "1px solid #2a2d50",
        "textAlign": "left",
        "padding": "8px 10px",
        "fontSize": "12.5px",
        "maxWidth": "250px",
        "overflow": "hidden",
        "textOverflow": "ellipsis",
    }
