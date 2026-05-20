"""
Service Transformer — Prédiction hybride (prix + sentiment) via HybridTransformerBounded.
Modèle PyTorch entraîné sur 44 features : OHLCV, indicateurs techniques et scores sentiment.
"""

import os
import math
import warnings
import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
_BASE = os.path.dirname(os.path.dirname(_HERE))
_PT   = os.path.join(_BASE, "Model AI Transformer", "transformer_model.pt")

_model      = None
_checkpoint = None
_articles_cache = {'df': None, 'ts': 0}

_MOIS_FR = {
    1: 'jan.', 2: 'fév.', 3: 'mars', 4: 'avr.', 5: 'mai', 6: 'juin',
    7: 'juil.', 8: 'août', 9: 'sept.', 10: 'oct.', 11: 'nov.', 12: 'déc.',
}

def _date_fr(d) -> str:
    try:
        import pandas as _pd
        t = _pd.Timestamp(d) if not hasattr(d, 'month') else d
        return f"{t.day} {_MOIS_FR[t.month]} {t.year}"
    except Exception:
        return str(d)

_GITHUB_MASTER = (
    "https://raw.githubusercontent.com/adam-hassen/stock-auto-update"
    "/main/data/articles_sentiment/ALL_ARTICLES_MASTER.csv"
)


# ─────────────────────── Model definition ────────────────────────

def _build_model():
    import torch
    import torch.nn as nn

    class _PE(nn.Module):
        def __init__(self, d_model, max_len=5000):
            super().__init__()
            pe  = torch.zeros(1, max_len, d_model)
            pos = torch.arange(0, max_len).float().unsqueeze(1)
            div = torch.exp(
                torch.arange(0, d_model, 2).float() * (-math.log(10000.0) / d_model)
            )
            pe[0, :, 0::2] = torch.sin(pos * div)
            pe[0, :, 1::2] = torch.cos(pos * div)
            self.register_buffer('pe', pe)

        def forward(self, x):
            return x + self.pe[:, :x.size(1), :]

    class _Transformer(nn.Module):
        def __init__(self):
            super().__init__()
            self.input_proj = nn.Linear(44, 64)
            self.pos        = _PE(64)
            layer = nn.TransformerEncoderLayer(
                d_model=64, nhead=4, dim_feedforward=256,
                dropout=0.0, batch_first=True
            )
            self.encoder  = nn.TransformerEncoder(layer, num_layers=2)
            self.norm     = nn.LayerNorm(64)
            self.dir_head = nn.Linear(64, 1)
            self.amp_head = nn.Linear(64, 1)

        def forward(self, x):
            x     = self.input_proj(x)
            x     = self.pos(x)
            x     = self.encoder(x)
            x     = self.norm(x[:, -1, :])
            dir_p = torch.sigmoid(self.dir_head(x))
            amp   = torch.tanh(self.amp_head(x))
            return dir_p, amp

    return _Transformer()


def _load():
    global _model, _checkpoint
    if _model is not None:
        return _model, _checkpoint
    import torch
    warnings.filterwarnings('ignore')
    ckpt = torch.load(_PT, map_location='cpu', weights_only=False)
    m    = _build_model()
    m.load_state_dict(ckpt['model_state_dict'])
    m.eval()
    _model      = m
    _checkpoint = ckpt
    return _model, _checkpoint


# ─────────────────────── Articles ────────────────────────

def _get_articles():
    import time, requests, pandas as pd
    from io import StringIO
    now = time.time()
    if _articles_cache['df'] is not None and now - _articles_cache['ts'] < 300:
        return _articles_cache['df']
    try:
        resp = requests.get(_GITHUB_MASTER, timeout=12)
        if resp.status_code == 200:
            df = pd.read_csv(StringIO(resp.text))
            df['date_publication'] = (
                pd.to_datetime(df['date_publication'], errors='coerce', utc=True)
                .dt.tz_localize(None)
            )
            df = df.dropna(subset=['date_publication', 'score_sentiment'])
            _articles_cache['df'] = df
            _articles_cache['ts'] = now
            return df
    except Exception as e:
        print(f"[TRANSFORMER] Articles: {e}")
    return _articles_cache['df'] if _articles_cache['df'] is not None else __import__('pandas').DataFrame()


# ─────────────────────── Feature engineering ────────────────────────

_FEATURE_COLS = [
    'open', 'high', 'low', 'close', 'volume',
    'close_lag1', 'ma_5', 'volatility', 'rsi', 'macd', 'bb_position_enc',
    'ret_1', 'ret_5', 'logret', 'sma_ratio', 'hl_range',
    'sentiment_score', 'articles_count', 'sentiment_weighted', 'has_news',
    'sentiment_lag1', 'sentiment_lag2', 'sentiment_lag3', 'sentiment_lag5',
    'articles_lag1', 'articles_lag2', 'articles_lag3', 'articles_lag5',
    'sentiment_mean_3d', 'sentiment_mean_5d', 'sentiment_mean_7d', 'sentiment_mean_14d',
    'sentiment_sum_3d', 'sentiment_sum_5d', 'sentiment_sum_7d', 'sentiment_sum_14d',
    'articles_sum_3d', 'articles_sum_5d', 'articles_sum_7d', 'articles_sum_14d',
    'sentiment_ema_5', 'sentiment_ema_10',
    'strong_positive_sentiment', 'strong_negative_sentiment',
]


def _build_features(ticker: str, df_price, df_articles):
    """
    Construit le DataFrame de features complet (N, 44).
    df_price doit avoir colonnes : date, open, high, low, close, volume.
    """
    import pandas as pd

    df = df_price.copy().reset_index(drop=True)

    # ── Technical ──
    df['close_lag1'] = df['close'].shift(1)
    df['ma_5']       = df['close'].rolling(5).mean()
    df['volatility'] = df['close'].rolling(5).std()
    df['ret_1']      = df['close'].pct_change(1)
    df['ret_5']      = df['close'].pct_change(5)
    df['logret']     = np.log(df['close'] / df['close'].shift(1))
    df['sma_ratio']  = df['close'] / df['ma_5'].replace(0, np.nan)
    df['hl_range']   = (df['high'] - df['low']) / df['close'].replace(0, np.nan)

    delta = df['close'].diff()
    gain  = delta.clip(lower=0).rolling(14).mean()
    loss  = (-delta.clip(upper=0)).rolling(14).mean()
    df['rsi'] = 100 - 100 / (1 + gain / loss.replace(0, 1e-9))

    ema12       = df['close'].ewm(span=12, adjust=False).mean()
    ema26       = df['close'].ewm(span=26, adjust=False).mean()
    df['macd']  = ema12 - ema26

    bb_ma  = df['close'].rolling(20).mean()
    bb_std = df['close'].rolling(20).std()
    bb_rng = (2 * bb_std).replace(0, 1e-9)
    df['bb_position_enc'] = (df['close'] - (bb_ma - bb_std)) / (2 * bb_rng)

    # ── Sentiment daily aggregation ──
    if not df_articles.empty:
        col_sym = next((c for c in ['symbol', 'ticker'] if c in df_articles.columns), None)
        arts = df_articles[df_articles[col_sym] == ticker].copy() if col_sym else pd.DataFrame()
    else:
        arts = pd.DataFrame()

    if not arts.empty:
        arts['_date'] = arts['date_publication'].dt.normalize()
        agg = arts.groupby('_date').agg(
            sentiment_score=('score_sentiment', 'mean'),
            articles_count=('score_sentiment', 'count'),
        ).reset_index().rename(columns={'_date': 'date_only'})
        agg['sentiment_weighted'] = agg['sentiment_score'] * np.log1p(agg['articles_count'])
        agg['has_news'] = 1.0
    else:
        import pandas as _pd
        agg = _pd.DataFrame(columns=['date_only', 'sentiment_score', 'articles_count',
                                      'sentiment_weighted', 'has_news'])

    df['date_only'] = pd.to_datetime(df['date']).dt.normalize()
    df = df.merge(agg, on='date_only', how='left')
    for c in ['sentiment_score', 'articles_count', 'sentiment_weighted', 'has_news']:
        df[c] = df[c].fillna(0.0)

    for lag in [1, 2, 3, 5]:
        df[f'sentiment_lag{lag}'] = df['sentiment_score'].shift(lag).fillna(0.0)
        df[f'articles_lag{lag}']  = df['articles_count'].shift(lag).fillna(0.0)

    for w in [3, 5, 7, 14]:
        df[f'sentiment_mean_{w}d'] = df['sentiment_score'].rolling(w, min_periods=1).mean()
        df[f'sentiment_sum_{w}d']  = df['sentiment_score'].rolling(w, min_periods=1).sum()
        df[f'articles_sum_{w}d']   = df['articles_count'].rolling(w, min_periods=1).sum()

    df['sentiment_ema_5']  = df['sentiment_score'].ewm(span=5,  adjust=False).mean()
    df['sentiment_ema_10'] = df['sentiment_score'].ewm(span=10, adjust=False).mean()
    df['strong_positive_sentiment'] = (df['sentiment_score'] > 0.5).astype(float)
    df['strong_negative_sentiment'] = (df['sentiment_score'] < -0.5).astype(float)

    df = df.fillna(0.0)
    return df


# ─────────────────────── Public API ────────────────────────

def predict(symbol: str) -> dict | None:
    """
    Prédit le log-rendement du lendemain avec le Transformer hybride.
    Retourne {'return_pct', 'signal', 'current_price', 'predicted_price', 'dir_prob'} ou None.
    """
    try:
        import torch, yfinance as yf, pandas as pd

        model, ckpt = _load()
        hist = yf.Ticker(symbol).history(period='150d', interval='1d')
        if len(hist) < 65:
            return None
        try:
            hist.index = pd.to_datetime(hist.index).tz_localize(None)
        except Exception:
            hist.index = pd.to_datetime(hist.index).tz_convert(None)

        df_price = hist[['Open', 'High', 'Low', 'Close', 'Volume']].copy().reset_index()
        df_price.columns = ['date', 'open', 'high', 'low', 'close', 'volume']

        df_feat = _build_features(symbol, df_price, _get_articles())
        if len(df_feat) < 60:
            return None

        X = df_feat[_FEATURE_COLS].values[-60:].astype(np.float32)

        mean     = np.array(ckpt['scaler_mean'], dtype=np.float32)
        std      = np.array(ckpt['scaler_std'],  dtype=np.float32)
        std_safe = np.where(std < 1e-9, 1.0, std)
        X_norm   = np.nan_to_num((X - mean) / std_safe)

        t = torch.tensor(X_norm).unsqueeze(0)
        with torch.no_grad():
            dir_p, amp = model(t)

        dir_prob = float(dir_p.item())
        amp_val  = float(amp.item())
        max_lr   = float(ckpt['max_logret'])
        logret   = (2 * dir_prob - 1) * abs(amp_val) * max_lr
        ret_pct  = (math.exp(logret) - 1) * 100
        current  = float(hist['Close'].iloc[-1])

        return {
            'return_pct':      round(ret_pct, 3),
            'signal':          'ACHETER' if logret > 0 else 'VENDRE',
            'current_price':   round(current, 2),
            'predicted_price': round(current * math.exp(logret), 2),
            'dir_prob':        round(dir_prob, 3),
        }
    except Exception as e:
        print(f"[TRANSFORMER] {symbol}: {e}")
        return None


def predict_backtest(ticker: str, start_amount: float = 500.0, days: int = 180) -> dict | None:
    """
    Backtest rolling Transformer sur les `days` derniers jours.
    Toutes les inférences sont faites en un seul appel batch.
    """
    try:
        import torch, yfinance as yf, pandas as pd

        model, ckpt = _load()

        hist = yf.Ticker(ticker).history(period=f'{days + 120}d', interval='1d')
        if len(hist) < 65:
            return None
        try:
            hist.index = pd.to_datetime(hist.index).tz_localize(None)
        except Exception:
            hist.index = pd.to_datetime(hist.index).tz_convert(None)

        df_price = hist[['Open', 'High', 'Low', 'Close', 'Volume']].copy().reset_index()
        df_price.columns = ['date', 'open', 'high', 'low', 'close', 'volume']

        df_feat = _build_features(ticker, df_price, _get_articles())
        if len(df_feat) < 65:
            return None

        mean     = np.array(ckpt['scaler_mean'], dtype=np.float32)
        std      = np.array(ckpt['scaler_std'],  dtype=np.float32)
        std_safe = np.where(std < 1e-9, 1.0, std)
        max_lr   = float(ckpt['max_logret'])

        feat_mat = df_feat[_FEATURE_COLS].values.astype(np.float32)
        closes   = df_feat['close'].values
        dates    = df_feat['date_only'].values

        bt_start = max(60, len(feat_mat) - 1 - days)
        if bt_start >= len(feat_mat) - 1:
            return None
        n_steps = len(feat_mat) - 1 - bt_start

        # ── Batch all sequences ──
        seqs = np.zeros((n_steps, 60, 44), dtype=np.float32)
        for k, i in enumerate(range(bt_start, len(feat_mat) - 1)):
            window = feat_mat[i - 60: i]
            seqs[k] = np.nan_to_num((window - mean) / std_safe)

        with torch.no_grad():
            t_seqs = torch.tensor(seqs)
            dir_ps, amps = model(t_seqs)

        dir_ps = dir_ps.numpy().flatten()
        amps   = amps.numpy().flatten()
        logrets = (2 * dir_ps - 1) * np.abs(amps) * max_lr

        portfolio    = start_amount
        buy_hold_ref = float(closes[bt_start])
        dates_out, port_vals, bh_vals, trade_log = [], [], [], []
        wins = losses = 0

        for k, i in enumerate(range(bt_start, len(feat_mat) - 1)):
            logret     = logrets[k]
            p_start    = float(closes[i])
            p_end      = float(closes[i + 1])
            actual_ret = (p_end - p_start) / p_start
            signal     = 'ACHETER' if logret > 0 else 'VENDRE'
            pnl_pct    = actual_ret if logret > 0 else -actual_ret
            portfolio  *= (1 + pnl_pct)
            bh          = start_amount * (p_end / buy_hold_ref)
            date_s      = pd.Timestamp(dates[i])

            dates_out.append(date_s)
            port_vals.append(round(portfolio, 2))
            bh_vals.append(round(bh, 2))
            if pnl_pct > 0:
                wins += 1
            else:
                losses += 1
            trade_log.append({
                'date':       _date_fr(date_s),
                'signal':     signal,
                'return_pct': round(pnl_pct * 100, 2),
                'pnl_eur':    round(
                    portfolio * pnl_pct / (1 + pnl_pct) if abs(1 + pnl_pct) > 0.001 else 0, 2
                ),
            })

        if not dates_out:
            return None

        n = wins + losses
        return {
            'dates':           dates_out,
            'portfolio':       port_vals,
            'buy_hold':        bh_vals,
            'final_value':     round(portfolio, 2),
            'total_return':    round((portfolio - start_amount) / start_amount * 100, 2),
            'buy_hold_return': round((bh_vals[-1] - start_amount) / start_amount * 100, 2),
            'start_amount':    start_amount,
            'n_trades':        n,
            'wins':            wins,
            'losses':          losses,
            'win_rate':        round(wins / n * 100) if n > 0 else 0,
            'trades':          trade_log[-15:],
            'start_date':      _date_fr(dates_out[0]),
            'data_start':      _date_fr(dates_out[0]),
            'first_signal_ts': dates_out[0].strftime('%Y-%m-%d'),
        }
    except Exception as e:
        print(f"[TRANSFORMER BACKTEST] {ticker}: {e}")
        return None
