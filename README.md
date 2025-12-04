# 📊 Archive de Données Financières

*Dernière mise à jour: 2025-12-04 10:19:30*

## 📁 Fichiers disponibles

| Fichier | Description | Taille |
|---------|-------------|--------|
| `data/ALL_CLEANED.csv` | Données brutes nettoyées | 1048 lignes |
| `data/ALL_FEATURES.csv` | Données avec indicateurs techniques | 632 lignes |
| `data/data_report.csv` | Rapport des données disponibles | 8 actions |

## 📈 Symboles suivis

AAPL, TSLA, MSFT, BTC-USD, GOOGL, NVDA, AMZN, META

## 🔍 Source des données

Données collectées depuis Yahoo Finance via l'API yFinance.
Mises à jour automatiques quotidiennes.

## 📄 Structure des données

Chaque fichier CSV contient les colonnes suivantes:
- `date`: Date de la donnée (AAAA-MM-JJ)
- `symbol`: Symbole de l'action/crypto
- `Open`, `High`, `Low`, `Close`: Prix d'ouverture, plus haut, plus bas, clôture
- `Volume`: Volume échangé
- `daily_return`, `volatility_10`, `MA_*`, `RSI_14`: Indicateurs techniques

## ⚠️ Avertissement

Ces données sont fournies à titre informatif uniquement.
Ne constitue pas un conseil en investissement.

---

*Généré automatiquement par [GitHub Actions](https://github.com/adam-hassen/stock-auto-update)*
