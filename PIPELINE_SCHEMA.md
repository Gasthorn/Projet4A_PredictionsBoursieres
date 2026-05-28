# Demande de schéma — Pipeline de prédictions boursières

## Contexte pour le designer

Génère un **schéma de pipeline clair et professionnel** (style diagramme de flux / architecture ML) pour un projet de prédictions boursières qui implémente **3 modes de prédiction distincts**.

---

## Clarification de l'architecture (réponse au prof)

### Question du prof : Que signifie « Transformer hybride » ?

**Réponse précise :**
Le mot « hybride » qualifie les **sources de données**, pas les modèles.

| Mode | Sources de données | Modèle | Nature du "hybride" |
|------|-------------------|--------|---------------------|
| Actualités | Articles de presse uniquement | Analyse de sentiment (règles) | ✗ Non hybride |
| LSTM | Historique des prix uniquement | BiLSTM + Embedding symbole | ✗ Non hybride |
| Transformer | **Prix + Actualités (combinés)** | Transformer Encoder | ✓ Hybride (2 sources) |

---

## Les 3 pipelines complets

---

### MODE 1 — Analyse des Actualités (Sentiment)

```
SOURCE          PRÉTRAITEMENT           MODÈLE              SORTIE
─────           ─────────────           ──────              ──────

Articles        Score de               Agrégation          Signal
de presse  ──►  sentiment         ──►  temporelle    ──►   HAUSSIER
(CSV GitHub)    [-1, +1]               (moyenne           BAISSIER
                par article            glissante)          NEUTRE
                                       + seuils
```

**Détails techniques :**
- Source : fichier CSV hébergé sur GitHub (mis à jour automatiquement)
- Scoring : score de sentiment par article (colonne `score_sentiment`)
- Agrégation : moyenne des scores sur une fenêtre temporelle par ticker
- Signal : HAUSSIER si score > seuil+, BAISSIER si score < seuil-, NEUTRE sinon
- Sortie : signal directionnel + score de confiance

---

### MODE 2 — LSTM (Historique des prix)

```
SOURCE          FEATURE ENGINEERING     NORMALISATION       MODÈLE              SORTIE
─────           ───────────────────     ─────────────       ──────              ──────

Prix OHLCV      14 indicateurs          RobustScaler        BiLSTM              Probabilité
(yfinance)  ──► techniques         ──►  clip [-5, 5]   ──►  (30 × 14)     ──►  directionnelle
90 jours        ret1, ret3, ret5        (sauvegardé)        + Embedding         → ACHETER
                trend_s, trend_l                            symbole (8 dim)      VENDRE
                mom3, mom10                                 ↓
                vol10, vol_ratio                            Dense → Sigmoid
                rsi14, rsi7
                atr, bb, volr
```

**Détails techniques :**
- Fenêtre temporelle : 30 jours (SEQ_LEN = 30)
- Features : 14 indicateurs techniques calculés sur l'historique OHLCV
- Normalisation : RobustScaler (résistant aux outliers) + clipping ±5
- Architecture : Bidirectional LSTM (64 unités) → LSTM (32) → Dense → Sigmoid
- Embedding symbole : 8 dimensions (pour AAPL, TSLA, MSFT, GOOGL, NVDA, AMZN, META, BTC-USD)
- Sortie : probabilité ∈ [0,1] → signal + rendement estimé (prob × volatilité récente)

---

### MODE 3 — Transformer Hybride (Prix + Actualités)

```
SOURCE 1        FEATURE ENG.           FUSION              NORMALISATION
─────────       ────────────           ──────              ─────────────
Prix OHLCV ──►  16 features       ──►                ──►  StandardScaler
(yfinance)      techniques             44 features         (feature_scaler)
                                       combinées
SOURCE 2        FEATURE ENG.           ↓
─────────       ────────────
Articles    ──►  28 features      ──►
de presse        sentiment-dérivées
(GitHub CSV)     (lags, moyennes,
                 EMA, sommes)

                                       MODÈLE              SORTIE
                                       ──────              ──────
                                       Transformer    ──►  Dir. prob. (sigmoid)
                                       Encoder             + Amplitude (tanh)
                                       (60 × 44)           ↓
                                       d_model=64          log-rendement
                                       nhead=4             = (2p-1) × |amp| × max_lr
                                       2 couches           ↓
                                                           ACHETER / VENDRE
                                                           + prix prédit demain
```

**Détails techniques :**
- Fenêtre temporelle : 60 jours (window = 60)
- Features prix (16) : OHLCV, close_lag1, MA5, volatilité, RSI, MACD, BB, returns, log-return, ratio SMA, range HL
- Features sentiment (28) : score_sentiment, articles_count, has_news, lags [1,2,3,5], moyennes [3,5,7,14j], sommes, EMA [5,10], signaux forts
- Total : 44 features
- Architecture : Linear(44→64) → Positional Encoding → TransformerEncoder × 2 → LayerNorm → tête direction (sigmoid) + tête amplitude (tanh)
- Sortie finale : log-rendement signé → prix prédit + signal directionnel

---

## Schéma global comparatif à générer

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     APPLICATION DE PRÉDICTIONS BOURSIÈRES                   │
│                           (8 tickers : US + Crypto)                         │
└───────────────────────────┬─────────────────────────────────────────────────┘
                            │
        ┌───────────────────┼──────────────────────┐
        ▼                   ▼                       ▼
 ┌─────────────┐    ┌──────────────┐    ┌─────────────────────┐
 │   MODE 1    │    │   MODE 2     │    │       MODE 3        │
 │ Actualités  │    │    LSTM      │    │  Transformer Hybride│
 └──────┬──────┘    └──────┬───────┘    └──────────┬──────────┘
        │                  │                        │
        ▼                  ▼                        ▼
   Articles de         Prix OHLCV           Prix OHLCV
   presse (CSV)        90 jours             + Articles
        │                  │                   (2 sources)
        ▼                  ▼                        ▼
   Sentiment           14 features             44 features
   scoring             techniques              (16 prix +
                       (30 jours)               28 sentiment)
                                               (60 jours)
        │                  │                        │
        ▼                  ▼                        ▼
   Agrégation          RobustScaler          StandardScaler
   + seuils            + clip ±5
        │                  │                        │
        ▼                  ▼                        ▼
   Règles de          BiLSTM (30×14)        Transformer
   décision           + Embedding            Encoder (60×44)
   (seuils)           symbole               d_model=64, 2L
        │                  │                        │
        ▼                  ▼                        ▼
   Score              Probabilité           Dir.prob + Amplitude
   sentiment          [0,1]                 → log-rendement
        │                  │                        │
        └──────────────────┴────────────────────────┘
                            │
                            ▼
              ┌─────────────────────────┐
              │       SIGNAL FINAL      │
              │  HAUSSIER / BAISSIER /  │
              │        NEUTRE           │
              │  + Prix prédit demain   │
              │  + Rendement estimé %   │
              └─────────────────────────┘
```

---

## Instructions pour le schéma visuel

Génère un **diagramme de pipeline vertical** avec :

1. **3 colonnes** (une par mode), chacune de couleur distincte :
   - Mode 1 (Actualités) : violet/mauve
   - Mode 2 (LSTM) : bleu/cyan
   - Mode 3 (Transformer) : vert/teal

2. **5 rangées** (couches du pipeline) :
   - Sources de données
   - Feature engineering
   - Normalisation
   - Modèle
   - Sortie

3. **Flèches de flux** entre chaque étape

4. **Zone de convergence** en bas des 3 colonnes vers un bloc "Sortie unifiée"

5. Style : professionnel, dark background, adapté rapport académique

6. Mentionner dans chaque colonne : nombre de features, taille de fenêtre temporelle, architecture du modèle

---

## Ce qui différencie les 3 modes (réponse directe au prof)

| Critère | Mode 1 | Mode 2 | Mode 3 |
|---------|--------|--------|--------|
| **Sources** | Actualités uniquement | Prix uniquement | **Prix + Actualités** |
| **Modèle** | Règles (pas de NN) | BiLSTM | Transformer Encoder |
| **Features** | Sentiment [-1,+1] | 14 indicateurs techniques | 44 features (hybrides) |
| **Fenêtre** | Variable (articles) | 30 jours | 60 jours |
| **Sortie brute** | Score sentiment | Probabilité sigmoid | Prob. + Amplitude |
| **"Hybride" ?** | ✗ | ✗ | ✓ (données hybrides) |

**Conclusion :** « Transformer hybride » = architecture Transformer appliquée à une **entrée hybride** (fusion de données de prix et de sentiment d'actualités). Le mot « hybride » qualifie les données d'entrée, non l'architecture du modèle.
