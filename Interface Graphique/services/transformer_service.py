"""
Service Transformer — Prédiction hybride (prix + sentiment) via HybridTransformerBounded.
Modèle PyTorch entraîné sur 44 features : OHLCV, indicateurs techniques et scores sentiment.
"""

import os
import json
import math
import warnings
import numpy as np

_HERE    = os.path.dirname(os.path.abspath(__file__))
_BASE    = os.path.dirname(os.path.dirname(_HERE))
_DIR     = os.path.join(_BASE, "Model AI Transformer")
_PT      = os.path.join(_DIR, "transformer_model.pt")   # ← vrai modèle PyTorch
_SCALER  = os.path.join(_DIR, "feature_scaler.save")
_CFG     = os.path.join(_DIR, "config.json")
_FCOLS   = os.path.join(_DIR, "feature_cols.json")

_model          = None
_scaler         = None
_encoder        = None
_cfg            = None
_articles_cache = {'df': None, 'ts': 0}

_ENCODER = os.path.join(_DIR, "symbol_encoder.save")

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


# ─────────────────────── Wrapper scaler (dict → sklearn-like) ────────────────

class _DictScaler:
    """Wrapper pour un scaler sauvegardé sous forme de dict plutôt que sklearn."""
    def __init__(self, d: dict):
        keys = set(d.keys())
        # StandardScaler
        if 'mean_' in keys and 'scale_' in keys:
            self._mean  = np.array(d['mean_'],  dtype=np.float32)
            self._scale = np.array(d['scale_'], dtype=np.float32)
            self._type  = 'standard'
        elif 'mean' in keys and ('scale' in keys or 'std' in keys):
            self._mean  = np.array(d['mean'],               dtype=np.float32)
            self._scale = np.array(d.get('scale', d.get('std')), dtype=np.float32)
            self._type  = 'standard'
        # RobustScaler
        elif 'center_' in keys and 'scale_' in keys:
            self._mean  = np.array(d['center_'], dtype=np.float32)
            self._scale = np.array(d['scale_'],  dtype=np.float32)
            self._type  = 'standard'
        elif 'center' in keys and 'scale' in keys:
            self._mean  = np.array(d['center'], dtype=np.float32)
            self._scale = np.array(d['scale'],  dtype=np.float32)
            self._type  = 'standard'
        # MinMaxScaler
        elif 'data_min_' in keys and 'data_max_' in keys:
            self._min   = np.array(d['data_min_'], dtype=np.float32)
            self._range = np.array(d['data_max_'], dtype=np.float32) - self._min
            self._type  = 'minmax'
        elif 'min' in keys and 'max' in keys:
            self._min   = np.array(d['min'], dtype=np.float32)
            self._range = np.array(d['max'], dtype=np.float32) - self._min
            self._type  = 'minmax'
        else:
            raise ValueError(f"[TRANSFORMER] Format scaler dict inconnu — clés: {list(keys)}")

    def transform(self, X):
        X = np.array(X, dtype=np.float32)
        if self._type == 'standard':
            return (X - self._mean) / (self._scale + 1e-9)
        else:
            return (X - self._min) / (self._range + 1e-9)

    def inverse_transform(self, X):
        X = np.array(X, dtype=np.float32)
        if self._type == 'standard':
            return X * self._scale + self._mean
        else:
            return X * self._range + self._min


# ─────────────────────── Architecture PyTorch ────────────────────────────────

def _get_torch():
    import torch
    import torch.nn as nn

    class _PE(nn.Module):
        def __init__(self, d, maxlen=512, drop=0.1):
            super().__init__()
            self.drop = nn.Dropout(drop)
            pe = torch.zeros(maxlen, d)
            pos = torch.arange(maxlen).unsqueeze(1).float()
            div = torch.exp(torch.arange(0, d, 2).float() * (-math.log(10000.0) / d))
            pe[:, 0::2] = torch.sin(pos * div)
            if d % 2 == 0:
                pe[:, 1::2] = torch.cos(pos * div)
            else:
                pe[:, 1::2] = torch.cos(pos * div[:-1])
            self.register_buffer('pe', pe.unsqueeze(0))
        def forward(self, x):
            return self.drop(x + self.pe[:, :x.size(1)])

    class HybridTransformerBounded(nn.Module):
        def __init__(self, d_input=44, d_model=64, nhead=4, num_layers=2,
                     dropout=0.15, num_symbols=8, max_logret=0.05):
            super().__init__()
            self.max_logret  = max_logret
            self.input_proj  = nn.Linear(d_input, d_model)
            self.symbol_emb  = nn.Embedding(num_symbols, d_model)
            self.pos_enc     = _PE(d_model, drop=dropout)
            enc = nn.TransformerEncoderLayer(d_model, nhead,
                                             dim_feedforward=d_model * 4,
                                             dropout=dropout,
                                             batch_first=True)
            self.transformer = nn.TransformerEncoder(enc, num_layers)
            self.head = nn.Sequential(
                nn.LayerNorm(d_model),
                nn.Linear(d_model, d_model // 2),
                nn.GELU(),
                nn.Dropout(dropout),
                nn.Linear(d_model // 2, 1),
            )
        def forward(self, x, sym):
            if sym.dim() > 1:
                sym = sym.squeeze(-1)
            x = self.input_proj(x) + self.symbol_emb(sym).unsqueeze(1)
            x = self.pos_enc(x)
            x = self.transformer(x)
            return torch.tanh(self.head(x[:, -1, :])) * self.max_logret

    return torch, HybridTransformerBounded


# ─────────────────────── Chargement modèle PyTorch ───────────────────────────

def _load():
    global _model, _scaler, _encoder, _cfg
    if _model is not None:
        return _model, _scaler, _encoder, _cfg

    import joblib
    torch, HybridTransformerBounded = _get_torch()

    raw_sc   = joblib.load(_SCALER)
    _scaler  = _DictScaler(raw_sc) if isinstance(raw_sc, dict) else raw_sc
    _encoder = joblib.load(_ENCODER)
    with open(_CFG, 'r') as f:
        _cfg = json.load(f)

    num_symbols = len(_encoder.classes_)

    # Chargement unique avec weights_only=False (fichier de confiance — projet local)
    # PyTorch 2.6 refuse weights_only=True si le checkpoint contient des numpy arrays
    err_msg = "inconnu"
    try:
        loaded = torch.load(_PT, map_location='cpu', weights_only=False)

        # Cas 1 : torch.save(model, ...) — objet complet
        if hasattr(loaded, 'eval'):
            _model = loaded
            _model.eval()
            print(f"[TRANSFORMER] Modèle PyTorch (full) chargé ✓  symboles={num_symbols}")
            return _model, _scaler, _encoder, _cfg

        # Cas 2 : torch.save({'model_state_dict': ..., ...}) ou state dict direct
        checkpoint = loaded if isinstance(loaded, dict) else {}
        state = checkpoint.get('model_state_dict', checkpoint)
        print(f"[TRANSFORMER] Checkpoint dict — clés: {list(checkpoint.keys())[:6]}")

        model = HybridTransformerBounded(
            d_input     = _cfg.get('feature_count', 44),
            d_model     = _cfg.get('d_model', 64),
            nhead       = _cfg.get('nhead', 4),
            num_layers  = _cfg.get('num_layers', 2),
            dropout     = _cfg.get('dropout', 0.15),
            num_symbols = num_symbols,
            max_logret  = _cfg.get('max_logret', 0.05),
        )
        missing, unexpected = model.load_state_dict(state, strict=False)
        if missing:
            print(f"[TRANSFORMER] Clés manquantes: {missing[:5]}")
        model.eval()
        _model = model
        print(f"[TRANSFORMER] Modèle PyTorch (state dict) chargé ✓  symboles={num_symbols}")
        return _model, _scaler, _encoder, _cfg

    except Exception as exc:
        err_msg = str(exc)
        print(f"[TRANSFORMER] _load() ERREUR: {err_msg}")
        raise RuntimeError(f"Impossible de charger transformer_model.pt : {err_msg}")


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
            # tz_convert(None) retire le timezone sans crash si déjà tz-aware
            df['date_publication'] = (
                pd.to_datetime(df['date_publication'], errors='coerce', utc=True)
                .dt.tz_convert(None)
            )
            df = df.dropna(subset=['date_publication', 'score_sentiment'])
            _articles_cache['df'] = df
            _articles_cache['ts'] = now
            return df
    except Exception as e:
        print(f"[TRANSFORMER] Articles erreur: {e}")
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
    Prédit le log-rendement du lendemain avec le HybridTransformerBounded (PyTorch).
    Retourne {'return_pct', 'signal', 'current_price', 'predicted_price', 'dir_prob'} ou None.
    """
    import traceback
    try:
        import yfinance as yf, pandas as pd

        print(f"[TRANSFORMER] Chargement modèle pour {symbol}...")
        model, scaler, encoder, cfg = _load()
        window = cfg.get('window', 60)
        max_lr = cfg.get('max_logret', 0.05)
        print(f"[TRANSFORMER] Modèle chargé — window={window}, max_lr={max_lr}")

        hist = yf.Ticker(symbol).history(period='150d', interval='1d')
        print(f"[TRANSFORMER] {symbol}: {len(hist)} jours de données")
        if len(hist) < 65:
            print(f"[TRANSFORMER] {symbol}: données insuffisantes ({len(hist)} < 65)")
            return None

        try:
            hist.index = pd.to_datetime(hist.index).tz_localize(None)
        except Exception:
            hist.index = pd.to_datetime(hist.index).tz_convert(None)

        df_price = hist[['Open', 'High', 'Low', 'Close', 'Volume']].copy().reset_index()
        df_price.columns = ['date', 'open', 'high', 'low', 'close', 'volume']

        df_feat = _build_features(symbol, df_price, _get_articles())
        print(f"[TRANSFORMER] {symbol}: {len(df_feat)} lignes features buildées")
        if len(df_feat) < window:
            print(f"[TRANSFORMER] {symbol}: features insuffisantes ({len(df_feat)} < {window})")
            return None

        X      = df_feat[_FEATURE_COLS].values[-window:].astype(np.float32)
        X_norm = np.nan_to_num(scaler.transform(X)).reshape(1, window, len(_FEATURE_COLS))

        try:
            sym_id = int(encoder.transform([symbol])[0])
        except Exception:
            sym_id = 0
            print(f"[TRANSFORMER] {symbol} non trouvé dans l'encodeur, sym_id=0")
        print(f"[TRANSFORMER] {symbol}: input shape={X_norm.shape}, sym_id={sym_id}")

        # ── Inférence PyTorch ──────────────────────────────────────────────────
        torch, _ = _get_torch()
        with torch.no_grad():
            X_t   = torch.FloatTensor(X_norm)       # (1, window, 44)
            Xs_t  = torch.LongTensor([[sym_id]])     # (1, 1)
            out   = model(X_t, Xs_t)                 # (1, 1)
            logret = float(out.squeeze().item())

        dir_prob = min(1.0, max(0.0, 0.5 + logret / (2 * max_lr + 1e-9)))
        ret_pct  = (math.exp(logret) - 1) * 100
        current  = float(hist['Close'].iloc[-1])
        print(f"[TRANSFORMER] {symbol}: dir_prob={dir_prob:.3f}, logret={logret:.4f}, ret_pct={ret_pct:.3f}%")

        return {
            'return_pct':      round(ret_pct, 3),
            'signal':          'ACHETER' if logret > 0 else 'VENDRE',
            'current_price':   round(current, 2),
            'predicted_price': round(current * math.exp(logret), 2),
            'dir_prob':        round(dir_prob, 3),
        }
    except Exception as e:
        print(f"[TRANSFORMER] {symbol} ERREUR: {e}")
        traceback.print_exc()
        return None


def predict_backtest(ticker: str, start_amount: float = 500.0, days: int = 180) -> dict | None:
    """
    Backtest rolling Transformer sur les `days` derniers jours.
    Toutes les inférences sont faites en un seul appel batch.
    """
    try:
        import yfinance as yf, pandas as pd

        model, scaler, encoder, cfg = _load()
        window = cfg.get('window', 60)
        max_lr = cfg.get('max_logret', 0.05)

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
        if len(df_feat) < window + 5:
            return None

        feat_mat = np.nan_to_num(
            scaler.transform(df_feat[_FEATURE_COLS].values.astype(np.float32))
        )
        closes = df_feat['close'].values
        dates  = df_feat['date_only'].values

        bt_start = max(window, len(feat_mat) - 1 - days)
        if bt_start >= len(feat_mat) - 1:
            return None
        n_steps = len(feat_mat) - 1 - bt_start

        # ── Symbol ID ──
        try:
            sym_id = int(encoder.transform([ticker])[0])
        except Exception:
            sym_id = 0

        # ── Batch toutes les séquences ──
        seqs = np.stack([
            feat_mat[i - window: i]
            for i in range(bt_start, len(feat_mat) - 1)
        ]).astype(np.float32)   # (n_steps, window, 44)
        sym_ids_batch = np.full((n_steps, 1), sym_id, dtype=np.int32)

        # ── Inférence PyTorch batch ────────────────────────────────────────────
        torch, _ = _get_torch()
        with torch.no_grad():
            seqs_t  = torch.FloatTensor(seqs)              # (n, window, 44)
            sym_t   = torch.LongTensor(sym_ids_batch)       # (n, 1)
            out     = model(seqs_t, sym_t)                  # (n, 1)
            logrets = out.squeeze().numpy()                 # (n,) ou scalar si n=1
            if logrets.ndim == 0:
                logrets = np.array([float(logrets)])

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
