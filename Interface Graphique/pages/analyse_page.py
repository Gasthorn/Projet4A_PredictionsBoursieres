from dash import html, dcc, Input, Output, State, callback, register_page,no_update,ctx,ALL
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from supabase import create_client

register_page(__name__, path="/data", name="Data")
url = "https://qeolwdccnegosrbldxqa.supabase.co"
key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InFlb2x3ZGNjbmVnb3NyYmxkeHFhIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Njc4NjIxOTIsImV4cCI6MjA4MzQzODE5Mn0.BHFV2ANfkC3RP-_R-cyjp-8yKtQhsZhVWUmnGnuU9b4"
supabase = create_client(url, key)
symbol_groups = {
    "BTC": ["BTC", "BTC-USD"],
    # Ajouter d'autres regroupements si nécessaire
}

stock_items = []

response = supabase.table("stocks") \
    .select("symbol,name") \
    .order("symbol") \
    .execute()

available_symbols_raw = []
symbol_to_name_raw = {}

for row in response.data:
    available_symbols_raw.append(row["symbol"])
    symbol_to_name_raw[row["symbol"]] = row["name"]

available_symbols = []
symbol_to_name = {}

for group_name, group_symbols in symbol_groups.items():
    present_symbols = [s for s in group_symbols if s in available_symbols_raw]
    if present_symbols:
        available_symbols.append(group_name)  
        symbol_to_name[group_name] = symbol_to_name_raw[present_symbols[0]]
        for s in present_symbols:
            available_symbols_raw.remove(s)

for s in available_symbols_raw:
    available_symbols.append(s)
    symbol_to_name[s] = symbol_to_name_raw[s]

for symbol in available_symbols:
    display_name = symbol_to_name.get(symbol, symbol) 
    stock_items.append(html.Div(
        display_name,
        id={'type': 'stock-item', 'index': symbol},  
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
            dcc.Loading(
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
                                html.Th("MA 5"),
                                html.Th("MACD"),
                            ])
                        ),
                        html.Tbody(id="features-table-body")  ,
                    ]
                ),
                type= "circle",
                color="white"
            )
        ]),
        
    ]),
])

def generate_table_rows(df, max_rows=60):
    """
    Génère les lignes HTML du tableau pour Dash.
    Arrondit certaines colonnes pour plus de lisibilité.
    """
    df = df.head(max_rows).copy()

    # Arrondir les colonnes pour plus de lisibilité
    for col in ["open", "high", "low", "close","ma_5"]:
        if col in df.columns:
            df[col] = df[col].round(2)
    if "rsi" in df.columns:
        df["rsi"] = df["rsi"].round(1)
    if "volatility" in df.columns:
        df["volatility"] = df["volatility"].round(4)
    if "macd" in df.columns:
        df["macd"] = df["macd"].round(3)
    if "volume" in df.columns:
        df["volume"] = df["volume"].astype(int)
    if "date" in df.columns:
        df["date"] = df["date"].dt.date

    rows = []
    close_values = df["close"].tolist() if "close" in df.columns else []
    for i, (_, row) in enumerate(df.iterrows()):
        if i < len(close_values) - 1:
            next_close = close_values[i + 1]
            current_close = row["close"]
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
                html.Td(f"{row.get('open', '-')}$"),
                html.Td(f"{row.get('high', '-')}$"),
                html.Td(f"{row.get('low', '-')}$"),
                html.Td(f"{row.get('close', '-')}$", className=close_class),
                html.Td(row.get("volume", "-")),
                html.Td(row.get("volatility", "-")),
                html.Td(row.get("rsi", "-")),
                html.Td(row.get("ma_5", "-")),
                html.Td(row.get("macd", "-")),
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
    
    ticker_symbol = symbol
    for group_name, group_symbols in symbol_groups.items():
        if symbol in group_symbols:
            ticker_group = group_symbols  
            break
    else:
        ticker_group = [symbol]  

    all_data = []
    batch_size = 1000
    start = 0
    while True:
        response = supabase.table("historical_data") \
            .select("date, open, high, low, close, volume") \
            .in_("symbol", ticker_group) \
            .order("date", desc=True) \
            .range(start, start + batch_size - 1) \
            .execute()
        
        if not response.data:
            break
        
        all_data.extend(response.data)
        start += batch_size

    df1 = pd.DataFrame(all_data)
    df1["date"] = pd.to_datetime(df1["date"])
    df1 = df1.drop_duplicates(subset=[ "date"], keep="first")

    all_data = []
    batch_size = 1000
    start = 0
    while True:
        response = supabase.table("features") \
            .select("date, ma_5, volatility, rsi, macd") \
            .in_("symbol", ticker_group) \
            .order("date", desc=True) \
            .range(start, start + batch_size - 1) \
            .execute()
        
        if not response.data:
            break
        
        all_data.extend(response.data)
        start += batch_size

    df2 = pd.DataFrame(all_data)
    df2["date"] = pd.to_datetime(df2["date"])
    df2 = df2.drop_duplicates(subset=[ "date"], keep="first")

    df = pd.merge(df1, df2, on="date", how="inner")

    return generate_table_rows(df, max_rows=60)


