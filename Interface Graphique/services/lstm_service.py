"""
Service LSTM — Prédiction de direction par le modèle BiLSTM entraîné.
Architecture : (30, 14) features + symbol embedding → probabilité directionnelle.
"""

import os
import warnings
import numpy as np
import pandas as pd

_HERE    = os.path.dirname(os.path.abspath(__file__))
_BASE    = os.path.dirname(os.path.dirname(_HERE))
_MODEL   = os.path.join(_BASE, "Modèle IA", "global_return_lstm.keras")
_SCALER  = os.path.join(_BASE, "Modèle IA", "return_scaler.save")
_ENCODER = os.path.join(_BASE, "Modèle IA", "symbol_encoder.save")

SEQ_LEN  = 30
FEATURES = [
    "ret1", "ret3", "ret5",
    "trend_s", "trend_l",
    "mom3", "mom10",
    "vol10", "vol_ratio",
    "rsi14", "rsi7",
    "atr", "bb", "volr",
]

_model = _scaler = _encoder = None


def _load():
    global _model, _scaler, _encoder
    if _model is None:
        warnings.filterwarnings("ignore")
        import keras
        import joblib
        _model   = keras.models.load_model(_MODEL)
        _scaler  = joblib.load(_SCALER)
        _encoder = joblib.load(_ENCODER)
    return _model, _scaler, _encoder


# ── Helpers feature engineering (même formules que le notebook) ──────────────

def _rsi(s: pd.Series, p: int = 14) -> pd.Series:
    delta = s.diff()
    gain  = delta.clip(lower=0).ewm(com=p - 1, min_periods=p).mean()
    loss  = (-delta.clip(upper=0)).ewm(com=p - 1, min_periods=p).mean()
    rs    = gain / (loss + 1e-9)
    return (100 - 100 / (1 + rs)) / 100.0


def _atr_norm(high: pd.Series, low: pd.Series, close: pd.Series, p: int = 14) -> pd.Series:
    tr  = pd.concat([
        high - low,
        (high - close.shift()).abs(),
        (low  - close.shift()).abs(),
    ], axis=1).max(axis=1)
    atr = tr.ewm(com=p - 1, min_periods=p).mean()
    return atr / (close + 1e-9)


def _bb_pos(close: pd.Series, p: int = 20) -> pd.Series:
    ma  = close.rolling(p).mean()
    std = close.rolling(p).std()
    return (close - (ma - 2 * std)) / (4 * std + 1e-9)


def _build_features(hist: pd.DataFrame) -> pd.DataFrame:
    df = hist[["Open", "High", "Low", "Close", "Volume"]].copy()
    df.columns = ["open", "high", "low", "close", "volume"]

    close  = df["close"]
    high   = df["high"]
    low    = df["low"]
    volume = df["volume"]

    df["ret1"] = close.pct_change()
    df["ret3"] = close.pct_change(3)
    df["ret5"] = close.pct_change(5)

    ma5  = close.rolling(5).mean()
    ma10 = close.rolling(10).mean()
    ma20 = close.rolling(20).mean()

    df["trend_s"] = (ma5  - ma10) / (ma10 + 1e-9)
    df["trend_l"] = (ma10 - ma20) / (ma20 + 1e-9)

    df["mom3"]  = close.diff(3)  / (close.shift(3)  + 1e-9)
    df["mom10"] = close.diff(10) / (close.shift(10) + 1e-9)

    df["vol10"]     = df["ret1"].rolling(10).std()
    df["vol_ratio"] = df["vol10"] / (df["ret1"].rolling(30).std() + 1e-9)

    df["rsi14"] = _rsi(close, 14)
    df["rsi7"]  = _rsi(close, 7)
    df["atr"]   = _atr_norm(high, low, close, 14)
    df["bb"]    = _bb_pos(close, 20).clip(0, 1)

    vol_ma      = volume.rolling(10).mean()
    df["volr"]  = (volume / (vol_ma + 1e-9)).clip(0, 5) / 5

    return df


# ── Prédiction principale ─────────────────────────────────────────────────────

def predict(symbol: str) -> dict | None:
    """
    Prédit la direction du prochain jour pour un ticker.
    Retourne un dict ou None en cas d'erreur.

    Clés retournées :
      return_pct       float   rendement estimé en %
      signal           str     'ACHETER' | 'VENDRE'
      current_price    float   dernier cours de clôture ($)
      predicted_price  float   cours estimé le prochain jour ($)
      probability      float   probabilité directionnelle (0-1)
    """
    try:
        import yfinance as yf

        model, scaler, encoder = _load()

        # 120 jours pour avoir assez de données après dropna (rolling 30)
        hist = yf.Ticker(symbol).history(period="120d", interval="1d")
        if len(hist) < 70:
            return None

        df = _build_features(hist)
        df = df.dropna(subset=FEATURES)

        if len(df) < SEQ_LEN:
            return None

        # Dernière fenêtre de SEQ_LEN lignes
        feat = df[FEATURES].values[-SEQ_LEN:].astype(np.float32)

        # Scale (RobustScaler entraîné sur les 14 features)
        feat_sc = scaler.transform(feat).astype(np.float32)
        feat_sc = np.clip(feat_sc, -5, 5)

        # Encodage symbole
        try:
            sym_id = int(encoder.transform([symbol])[0])
        except Exception:
            print(f"[LSTM] {symbol} non trouvé dans l'encodeur")
            return None

        X  = feat_sc.reshape(1, SEQ_LEN, len(FEATURES))
        Xs = np.array([[sym_id]], dtype=np.int32)

        warnings.filterwarnings("ignore")
        prob = float(model.predict([X, Xs], verbose=0)[0][0])

        # Rendement estimé = direction * volatilité récente
        vol = float(df["vol10"].iloc[-1])
        if np.isnan(vol) or vol == 0:
            vol = 0.01
        pred_ret = (prob - 0.5) * 2 * vol

        current = float(hist["Close"].iloc[-1])

        return {
            "return_pct":      round(pred_ret * 100, 3),
            "signal":          "ACHETER" if prob >= 0.52 else "VENDRE",
            "current_price":   round(current, 2),
            "predicted_price": round(current * (1 + pred_ret), 2),
            "probability":     round(prob, 4),
        }

    except Exception as e:
        print(f"[LSTM] {symbol} : {e}")
        return None
