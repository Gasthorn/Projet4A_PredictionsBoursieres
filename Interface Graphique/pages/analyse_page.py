from dash import html, dcc, Input, Output, State, callback, register_page,no_update,ctx,ALL
import plotly.graph_objects as go
import pandas as pd
import numpy as np

register_page(__name__, path="/analysis", name="Analyse")

df_features = pd.read_csv("Data/ALL_FEATURES.csv", parse_dates=["date"])

layout = html.Div(className="analysis-page", children = [
    # Titre animé
    html.Div(className="page-title", children=[
        html.H1("Analyse effectuée par le modèle", className="glow-title"),
        html.Div(className="neon-underline")
    ]),
    html.Div(className="text-panel", children=[
        html.H4("Données Utilisées", className="panel-title"),
        html.Table(
            className="lux-table split-table",
            children=[
                html.Thead(
                    html.Tr([
                        html.Th("Open"),
                        html.Th("High"),
                        html.Th("Low"),
                        html.Th("Close"),
                        html.Th("Volume"),
                        html.Th("Volatility"),
                        html.Th("RSI"),
                        html.Th("MA 20"),
                    ])
                ),
            ]
        )
    ]),
])