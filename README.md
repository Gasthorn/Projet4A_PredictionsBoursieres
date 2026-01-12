#  Données Financières - Projet 4A

*Dernière mise à jour: 2026-01-12 20:51:55*

##  Fichiers disponibles

Cette branche (`Collecte-Des-Données`) contient les données financières collectées automatiquement.

| Fichier | Description | Taille |
|---------|-------------|--------|
| `data/ALL_CLEANED.csv` | Données brutes nettoyées | 52253 lignes |
| `data/ALL_FEATURES.csv` | Données avec indicateurs techniques | 750 lignes |
| `data/data_report.csv` | Rapport des données disponibles | 8 actions |

##  Symboles suivis

AAPL, TSLA, MSFT, BTC-USD, GOOGL, NVDA, AMZN, META

##  Source des données

Données collectées depuis Yahoo Finance via l'API yFinance.
Mises à jour automatiques quotidiennes à 20h (heure française).

##  Indicateurs inclus

Pour chaque symbole:
- Prix (Open, High, Low, Close, Volume)
- Retours journaliers
- Volatilité (10 jours)
- Moyennes mobiles (5, 20, 50 jours)
- RSI (14 jours)
- Ratio de volume
---

*Généré automatiquement par GitHub Actions depuis [stock-auto-update](https://github.com/adam-hassen/stock-auto-update)*
