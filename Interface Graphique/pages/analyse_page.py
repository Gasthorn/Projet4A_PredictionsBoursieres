from dash import html, dcc, Input, Output, State, callback, register_page,no_update,ctx,ALL
import plotly.graph_objects as go
import pandas as pd
import numpy as np

register_page(__name__, path="/data", name="Data")
df_features = pd.read_csv("Data/ALL_FEATURES.csv", parse_dates=["date"])

symbol_to_name = {
    "AAPL": "Apple",
    "AMZN": "Amazon",
    "BTC-USD": "Bitcoin",
    "GOOGL": "Google",
    "META": "Meta",
    "MSFT": "Microsoft",
    "NVDA": "NVIDIA",
    "TSLA": "Tesla"
}

available_symbols = sorted(df_features["symbol"].unique())
stock_items = []
for symbol in available_symbols:
    display_name = symbol_to_name.get(symbol, symbol)  # fallback au symbole si pas de nom
    stock_items.append(html.Div(
        display_name,
        id={'type': 'stock-item', 'index': symbol},  # on garde le symbol pour le callback
        n_clicks=0,
        className="stock-item active" if symbol == "AAPL" else "stock-item"
    ))

layout = html.Div(className="data-page", children = [
    dcc.Store(id="selected-stock", data="AAPL"),
    # Titre animé
    html.Div(className="page-title", children=[
        html.H1("Données utilisées par le modèle", className="glow-title"),
        html.Div(className="neon-underline")
    ]),
    html.Div(className="actions-navbar",children=[
        html.Div(className="actions-navbar-inner",children=[
            html.Div(
                className="stock-bar",
                children=stock_items,
            ),
        ])
    ]),
    html.Div(className="text-panel", children=[
        html.H4("Données Utilisées", className="panel-title"),
        html.Div(className="table-container",children=[
            html.Table(
                className="lux-table split-table",
                children=[
                    html.Thead(
                        html.Tr([
                            html.Th("Date"),
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
                    html.Tbody(id="features-table-body")  ,
                ]
            )
        ]),
        
    ]),
])

def generate_table_rows(df, max_rows=60):
    """
    Génère les lignes HTML du tableau pour Dash.
    Arrondit certaines colonnes pour plus de lisibilité.
    """
    df = df.tail(max_rows).copy().iloc[::-1]

    # Arrondir les colonnes pour plus de lisibilité
    for col in ["Open", "High", "Low", "Close", "MA_20"]:
        if col in df.columns:
            df[col] = df[col].round(2)
    if "RSI_14" in df.columns:
        df["RSI_14"] = df["RSI_14"].round(1)
    if "Volume" in df.columns:
        df["Volume"] = df["Volume"].astype(int)
    if "date" in df.columns:
        df["date"] = df["date"].dt.date
    if "volatility_10" in df.columns:
        df["volatility_10"] = df["volatility_10"].round(4)

    rows = []
    close_values = df["Close"].tolist() if "Close" in df.columns else []
    for i, (_, row) in enumerate(df.iterrows()):
        if i < len(close_values) - 1:
            next_close = close_values[i + 1]
            current_close = row["Close"]
            if current_close > next_close:
                close_class = "metric-value up"
            elif current_close < next_close:
                close_class = "metric-value down"
            else:
                close_class = ""
        else:
            close_class = ""
        rows.append(
            html.Tr([
                html.Td(row.get("date", "-")),
                html.Td(f"{row.get('Open', '-')}$"),
                html.Td(f"{row.get('High', '-')}$"),
                html.Td(f"{row.get('Low', '-')}$"),
                html.Td(f"{row.get('Close', '-')}$", className=close_class),
                html.Td(row.get("Volume", "-")),
                html.Td(row.get("volatility_10", "-")),
                html.Td(row.get("RSI_14", "-")),
                html.Td(row.get("MA_20", "-")),
            ])
        )
    return rows


@callback(
    Output("features-table-body", "children"),
    Input("selected-stock", "data")  # on récupère l'action sélectionnée
)
def update_features_table(symbol):
    # Si symbol est None, on met AAPL par défaut
    if not symbol:
        symbol = "AAPL"

    # Filtrer le DataFrame pour ce symbole
    df_symbol = df_features[df_features["symbol"] == symbol].sort_values("date")
    if df_symbol.empty:
        return [html.Tr([html.Td("Pas de données", colSpan=8)])]

    # Retourner les 60 dernières lignes
    return generate_table_rows(df_symbol, max_rows=60)


