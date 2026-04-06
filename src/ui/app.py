"""BaseFerRhin — Archaeological site explorer (Dash application factory)."""

from __future__ import annotations

from pathlib import Path

from dash import Dash
import dash_bootstrap_components as dbc

from .callbacks import register_callbacks
from .layout import create_layout
from .site_loader import load_sites


def create_app() -> Dash:
    app = Dash(
        __name__,
        external_stylesheets=[
            dbc.themes.DARKLY,
            "https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap",
        ],
        title="BaseFerRhin — Âge du Fer",
        assets_folder=str(Path(__file__).parent / "assets"),
    )

    df = load_sites()
    app.layout = create_layout(df)
    register_callbacks(app)
    return app


def main() -> None:
    app = create_app()
    print("\n  BaseFerRhin UI → http://127.0.0.1:8050\n")
    app.run(debug=True, port=8050, host="127.0.0.1")


if __name__ == "__main__":
    main()
