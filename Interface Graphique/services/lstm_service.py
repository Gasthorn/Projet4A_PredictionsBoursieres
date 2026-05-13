"""
Service LSTM — Prédiction de prix par le modèle BiLSTM entraîné.
Utilisé par la page home et par Mon Suivi.
"""

import os
import warnings
import numpy as np

_HERE    = os.path.dirname(os.path.abspath(__file__))
_BASE    = os.path.dirname(os.path.dirname(_HERE))
_MODEL   = os.path.join(_BASE, "Modèle IA", "global_return_lstm.keras")
_SCALER  = os.path.join(_BASE, "Modèle IA", "return_scaler.save")
_ENCODER = os.path.join(_BASE, "Modèle IA", "symbol_encoder.save")

_model = _scaler = _encoder = None


def _load():
    global _model, _scaler, _encoder
    if _model is None:
        warnings.filterwarnings('ignore')
        import keras
        import joblib
        _model   = keras.models.load_model(_MODEL)
        _scaler  = joblib.load(_SCALER)
        _encoder = joblib.load(_ENCODER)
    return _model, _scaler, _encoder


def predict(symbol: str) -> dict | None:
    """
    Prédit le rendement journalier suivant pour un ticker.
    Retourne un dict ou None en cas d'erreur.

    Clés retournées :
      return_pct       float   rendement prédit en %
      signal           str     'ACHETER' | 'VENDRE'
      current_price    float   dernier cours de clôture ($)
      predicted_price  float   cours prédit le prochain jour ($)
    """
    try:
        import yfinance as yf
        model, scaler, encoder = _load()

        hist = yf.Ticker(symbol).history(period='90d', interval='1d')
        if len(hist) < 62:
            return None

        closes  = hist['Close'].values
        returns = np.diff(closes) / closes[:-1]
        seq_sc  = scaler.transform(returns[-60:].reshape(-1, 1)).reshape(1, 60, 1)
        sym_id  = encoder.transform([symbol])[0]

        warnings.filterwarnings('ignore')
        pred_sc  = model.predict([seq_sc, np.array([[sym_id]])], verbose=0)
        pred_ret = float(scaler.inverse_transform(pred_sc)[0][0])

        current = float(hist['Close'].iloc[-1])
        return {
            'return_pct':      round(pred_ret * 100, 3),
            'signal':          'ACHETER' if pred_ret > 0 else 'VENDRE',
            'current_price':   round(current, 2),
            'predicted_price': round(current * (1 + pred_ret), 2),
        }
    except Exception as e:
        print(f"[LSTM] {symbol} : {e}")
        return None
