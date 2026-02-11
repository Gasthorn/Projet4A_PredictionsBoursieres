from dash import html, dcc, Input, Output, State, callback, register_page,no_update,ctx,ALL
import plotly.graph_objects as go
import pandas as pd
import numpy as np

register_page(__name__, path="/analysis", name="Analyse")

layout = html.Div(className="analysis-page", children = [
    # Titre animé
    html.Div(className="page-title", children=[
        html.H1("Analyse d'Actifs en Temps Réel", className="glow-title"),
        html.Div(className="neon-underline")
    ]),
    html.Div(className="data-container", children=[]),
])