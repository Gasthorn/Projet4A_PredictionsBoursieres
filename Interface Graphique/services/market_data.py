import os
from typing import Optional
import pandas as pd
import datetime as dt
import time

try:
    import requests  # for Alpha Vantage fallback
except Exception:
    requests = None

try:
    import yfinance as yf  # lightweight polling, near real-time for popular tickers
except Exception:
    yf = None


def fetch_candles_yf(symbol: str, period: str = '1d', interval: str = '1m') -> pd.DataFrame:
    if yf is None:
        raise RuntimeError("yfinance is not installed. Please install yfinance.")
    ticker = yf.Ticker(symbol)
    df = ticker.history(period=period, interval=interval, auto_adjust=False)
    df = df.rename(columns={
        'Open': 'Open', 'High': 'High', 'Low': 'Low', 'Close': 'Close', 'Volume': 'Volume'
    })
    # Ensure index is datetime and sorted
    # yfinance can return either Datetime or Date in index/columns. Normalize to Date index
    if 'Datetime' in df.columns:
        df = df.rename(columns={'Datetime': 'Date'})
    df = df.reset_index().rename(columns={'Date': 'Date'})
    if 'Date' not in df.columns:
        df = df.rename(columns={'index': 'Date'})
    df = df.set_index('Date')
    df = df.sort_index()
    return df[['Open', 'High', 'Low', 'Close']]


def _map_interval_to_alpha_vantage(interval: str) -> Optional[str]:
    mapping = {
        '1m': '1min',
        '5m': '5min',
        '15m': '15min',
        '60m': '60min'
    }
    return mapping.get(interval)


def fetch_candles_alpha_vantage(symbol: str, interval: str, api_key: str) -> pd.DataFrame:
    if requests is None:
        raise RuntimeError("requests n'est pas installé. Veuillez installer requests.")
    av_interval = _map_interval_to_alpha_vantage(interval) or '1min'
    params = {
        'function': 'TIME_SERIES_INTRADAY',
        'symbol': symbol,
        'interval': av_interval,
        'apikey': api_key,
        'outputsize': 'compact'
    }
    url = 'https://www.alphavantage.co/query'
    resp = requests.get(url, params=params, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    key = f'Time Series ({av_interval})'
    if key not in data:
        # Alpha Vantage rate limit or unsupported symbol
        raise RuntimeError(f"Alpha Vantage réponse invalide: {list(data.keys())[:3]}")
    ts = data[key]
    rows = []
    for ts_str, ohlc in ts.items():
        # parse timestamps as local naive datetime
        try:
            ts_dt = dt.datetime.fromisoformat(ts_str)
        except Exception:
            # fallback format
            ts_dt = dt.datetime.strptime(ts_str, '%Y-%m-%d %H:%M:%S')
        rows.append({
            'Date': ts_dt,
            'Open': float(ohlc['1. open']),
            'High': float(ohlc['2. high']),
            'Low': float(ohlc['3. low']),
            'Close': float(ohlc['4. close'])
        })
    df = pd.DataFrame(rows).set_index('Date').sort_index()
    return df[['Open', 'High', 'Low', 'Close']]


def fetch_latest_candles(symbol: str, period: str = '1d', interval: str = '1m') -> pd.DataFrame:
    # If Alpha Vantage key is present and symbol looks supported, try AV first
    av_key = os.getenv('ALPHAVANTAGE_API_KEY')
    # Simple heuristic: AV does not support indices like ^GSPC, ^FCHI directly
    looks_index = symbol.startswith('^')
    if av_key and not looks_index:
        try:
            return fetch_candles_alpha_vantage(symbol, interval=interval, api_key=av_key)
        except Exception:
            # fall back to yfinance below
            pass
    # Retry yfinance a couple of times in case of DNS hiccups
    last_err = None
    for _ in range(2):
        try:
            return fetch_candles_yf(symbol, period=period, interval=interval)
        except Exception as e:
            last_err = e
            time.sleep(1.0)
    # final raise
    raise last_err if last_err else RuntimeError('Unknown data fetch error')


