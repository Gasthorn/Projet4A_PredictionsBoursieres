# Documentation Technique — Plateforme de Prédictions Boursières
## Projet 4A — ENSIM (École Nationale Supérieure d'Ingénieurs du Mans)

> Application web complète de prédiction boursière par intelligence artificielle, combinant trois modèles de Machine Learning, une authentification biométrique par reconnaissance faciale, un assistant IA conversationnel et un tableau de bord de suivi d'investissements en temps réel.

---

## Table des matières

1. [Vue d'ensemble du projet](#1-vue-densemble-du-projet)
2. [Stack technologique](#2-stack-technologique)
3. [Architecture générale](#3-architecture-générale)
4. [Structure des fichiers](#4-structure-des-fichiers)
5. [Modèles d'Intelligence Artificielle](#5-modèles-dintelligence-artificielle)
   - 5.1 [Modèle Sentiment — Analyse des actualités](#51-modèle-sentiment--analyse-des-actualités)
   - 5.2 [Modèle BiLSTM (Long Short-Term Memory)](#52-modèle-bilstm-long-short-term-memory)
   - 5.3 [Modèle Transformer Hybride](#53-modèle-transformer-hybride)
   - 5.4 [Comparaison des trois modèles](#54-comparaison-des-trois-modèles)
6. [Authentification biométrique — Reconnaissance faciale](#6-authentification-biométrique--reconnaissance-faciale)
7. [Assistant IA conversationnel (Chatbot)](#7-assistant-ia-conversationnel-chatbot)
8. [Pages et fonctionnalités détaillées](#8-pages-et-fonctionnalités-détaillées)
9. [Base de données — Schéma complet](#9-base-de-données--schéma-complet)
10. [APIs REST](#10-apis-rest)
11. [Pipeline de données et sources](#11-pipeline-de-données-et-sources)
12. [Installation et démarrage](#12-installation-et-démarrage)

---

## 1. Vue d'ensemble du projet

Cette plateforme est une application web de prédiction boursière développée en Python. Elle intègre trois approches complémentaires de Machine Learning pour prédire les mouvements de prix de 8 actifs financiers (actions technologiques + Bitcoin).

### Actifs financiers supportés

| Symbole   | Entreprise / Actif     | Classe d'actif |
|-----------|------------------------|----------------|
| AAPL      | Apple Inc.             | Action         |
| MSFT      | Microsoft Corporation  | Action         |
| TSLA      | Tesla Inc.             | Action         |
| NVDA      | NVIDIA Corporation     | Action         |
| GOOGL     | Alphabet Inc.          | Action         |
| AMZN      | Amazon.com Inc.        | Action         |
| META      | Meta Platforms Inc.    | Action         |
| BTC-USD   | Bitcoin                | Crypto-monnaie |

### Fonctionnalités principales

- **Prédictions IA en temps réel** : signaux ACHETER / VENDRE / SURVEILLER sur les 8 actifs
- **Trois modèles distincts** : Sentiment (NLP), BiLSTM (deep learning sur prix), Transformer Hybride (prix + actualités)
- **Backtesting sur 180 jours** : simulation de portefeuille en suivant les conseils de chaque modèle
- **Comparaison inter-modèles** : courbes de performance, taux de réussite, PnL comparé
- **Suivi d'investissements personnel** : enregistrement, historique, statistiques
- **Assistant IA conversationnel** : LLaMA 3.3 70B via Groq, streaming temps réel, enregistrement d'investissements
- **Authentification biométrique** : connexion par reconnaissance faciale (OpenCV)
- **Panneau administrateur** : gestion utilisateurs, statistiques plateforme, modération

---

## 2. Stack technologique

### Framework et interface

| Technologie | Version | Utilisation |
|-------------|---------|-------------|
| **Python** | 3.11 | Langage principal |
| **Dash (Plotly)** | 2.x | Framework web Python (SPA réactive) |
| **Flask** | 2.x | Serveur HTTP sous-jacent, APIs REST |
| **Plotly** | 5.x | Graphiques interactifs (courbes, camemberts) |
| **Lightweight-charts** | 4.x | Graphiques en chandeliers japonais (TradingView) |
| **CSS3 custom** | — | Thème glassmorphism néon (fonds translucides, lueurs cyan) |
| **Font Awesome** | 6.5 | Icônes vectorielles |

### Machine Learning — Prédiction boursière

| Technologie | Utilisation |
|-------------|-------------|
| **TensorFlow / Keras** | Modèle BiLSTM (14 features, séquence 30 jours) |
| **PyTorch** | Modèle Transformer hybride (44 features, séquence 60 jours) |
| **scikit-learn** | RobustScaler, StandardScaler, LabelEncoder |
| **NumPy / Pandas** | Feature engineering, séries temporelles |
| **joblib** | Sauvegarde/chargement des scalers |

### Intelligence Artificielle — Chatbot

| Technologie | Utilisation |
|-------------|-------------|
| **Groq API** | Inférence LLM ultra-rapide (~200 tokens/s) |
| **LLaMA 3.3 70B** | Modèle de langage conversationnel (Meta AI) |
| **Server-Sent Events (SSE)** | Streaming des réponses mot par mot |

### Biométrie — Reconnaissance faciale

| Technologie | Utilisation |
|-------------|-------------|
| **OpenCV** | Détection faciale (Haar Cascade frontal) |
| **cv2.TM_CCOEFF_NORMED** | Template matching (cross-corrélation) |
| **Filtres Sobel** | Comparaison des contours/structure |
| **JavaScript (camera.js)** | Capture webcam, encodage base64 |

### Données et base de données

| Technologie | Utilisation |
|-------------|-------------|
| **SQLite** | Base de données locale (users.db) |
| **bcrypt** | Hachage sécurisé des mots de passe |
| **yfinance** | Cours boursiers temps réel et historiques (OHLCV) |
| **Alpha Vantage API** | Source de secours pour données intraday |
| **GitHub CSV** | Articles de presse financière (sentiment, mis à jour quotidiennement) |

### Déploiement

| Technologie | Utilisation |
|-------------|-------------|
| **Docker** | Conteneurisation (Python 3.11, port 7860) |
| **python-dotenv** | Gestion des variables d'environnement |

---

## 3. Architecture générale

```
┌─────────────────────────────────────────────────────────────────────┐
│                     NAVIGATEUR (Client)                             │
│                                                                     │
│  Dash React SPA · Plotly · Lightweight-charts                       │
│  chatbot.js (streaming, modal, drag) · camera.js (webcam)           │
└──────────────────────────────┬──────────────────────────────────────┘
                               │ HTTP / SSE
┌──────────────────────────────▼──────────────────────────────────────┐
│                     SERVEUR FLASK (app.py)                          │
│                                                                     │
│  ┌──────────────┐  ┌────────────────────┐  ┌────────────────────┐  │
│  │  Dash Pages  │  │    APIs Flask      │  │  Assets statiques  │  │
│  │  (Routing)   │  │  /api/chat (SSE)   │  │  chatbot.js        │  │
│  │  /           │  │  /api/chat-invest  │  │  chatbot.css       │  │
│  │  /mon-suivi  │  │  /api/ohlcv/<sym>  │  │  camera.js         │  │
│  │  /analysis   │  │  /api/backtest-    │  │  style.css         │  │
│  │  /actions    │  │    compare         │  │  marche_chart.html │  │
│  │  /profil     │  │  /api/face-login   │  └────────────────────┘  │
│  │  /admin      │  └────────────────────┘                          │
│  └──────────────┘                                                   │
└────────┬────────────────┬───────────────┬────────────────┬──────────┘
         │                │               │                │
┌────────▼──────┐ ┌───────▼────────┐ ┌───▼──────────┐ ┌──▼──────────┐
│  LSTM (Keras) │ │ Transformer    │ │  Groq API    │ │  SQLite DB  │
│               │ │ (PyTorch)      │ │  LLaMA 3.3   │ │  users.db   │
│  14 features  │ │ 44 features    │ │  70B         │ │  4 tables   │
│  30 jours     │ │ 60 jours       │ │  Streaming   │ │             │
└───────────────┘ └────────────────┘ └──────────────┘ └─────────────┘
         │                │
┌────────▼────────────────▼──────────────────────────────────────────┐
│                    SOURCES DE DONNÉES                               │
│                                                                     │
│  yfinance (cours temps réel OHLCV)                                  │
│  Alpha Vantage (backup intraday)                                    │
│  GitHub CSV (articles presse financière + scores sentiment)         │
└────────────────────────────────────────────────────────────────────┘
```

---

## 4. Structure des fichiers

```
Projet4A_PredictionsBoursieres-main/
│
├── Interface Graphique/                    # Application web principale
│   ├── app.py                              # Point d'entrée : Dash + toutes les APIs Flask
│   ├── .env                                # Variables d'environnement (GROQ_API_KEY, etc.)
│   │
│   ├── pages/                              # Pages Dash (routing automatique par nom de fichier)
│   │   ├── home.py                         # Accueil : prédictions temps réel
│   │   ├── mon_suivi.py                    # Suivi des investissements + backtest 180j
│   │   ├── actions_page.py                 # Graphiques chandeliers (Lightweight-charts)
│   │   ├── analyse_page.py                 # Dashboard analyse de sentiment
│   │   ├── profil.py                       # Profil utilisateur + KPIs trading
│   │   ├── login.py                        # Connexion email/mot de passe
│   │   ├── signup.py                       # Inscription + capture visage optionnelle
│   │   ├── face_login.py                   # Connexion par reconnaissance faciale
│   │   ├── temoignages.py                  # Témoignages publics + stats plateforme
│   │   └── admin/                          # Panneau administrateur (accès restreint)
│   │       ├── dashboard.py                # KPIs + navigation admin
│   │       ├── users.py                    # Gestion utilisateurs (CRUD)
│   │       ├── stats.py                    # Statistiques plateforme
│   │       ├── logs.py                     # Historique des connexions
│   │       └── testimonials.py             # File de modération témoignages
│   │
│   ├── services/                           # Couche logique métier et IA
│   │   ├── database.py                     # Schéma SQLite + init + chemin absolu DB
│   │   ├── auth_service.py                 # Authentification, création comptes (bcrypt)
│   │   ├── tracking_service.py             # Enregistrement trades + statistiques
│   │   ├── admin_service.py                # Requêtes admin (CRUD, stats, logs)
│   │   ├── lstm_service.py                 # Service prédiction BiLSTM (Keras)
│   │   ├── transformer_service.py          # Service prédiction Transformer (PyTorch)
│   │   ├── chat_service.py                 # Service chatbot Groq LLaMA 3.3
│   │   ├── face_auth.py                    # Capture et stockage des visages
│   │   ├── face_comparator.py              # Algorithme de comparaison biométrique
│   │   └── market_data.py                  # Récupération données marché (yfinance + AV)
│   │
│   └── assets/                             # Fichiers statiques (CSS, JS, images)
│       ├── style.css                       # Styles principaux (thème glassmorphism)
│       ├── chatbot.css                     # Styles chatbot + modal comparaison
│       ├── chatbot.js                      # Logique chatbot (v6 : streaming, drag, modal)
│       ├── camera.js                       # Gestion webcam (reconnaissance faciale)
│       ├── tooltip.js                      # Tooltips personnalisés
│       ├── suivi.css, analyse.css, etc.    # Styles par page
│       ├── marche_chart.html               # Interface Lightweight-charts embarquée
│       └── logo.png
│
├── Modèle IA/                              # Fichiers modèle BiLSTM
│   ├── global_return_lstm.keras            # Modèle Keras sauvegardé (BiLSTM)
│   ├── return_scaler.save                  # RobustScaler (joblib)
│   └── symbol_encoder.save                 # LabelEncoder (8 symboles)
│
├── Model AI Transformer/                   # Fichiers modèle Transformer
│   ├── transformer_model.pt                # Poids PyTorch (HybridTransformerBounded)
│   ├── feature_scaler.save                 # StandardScaler 44 features (joblib)
│   ├── symbol_encoder.save                 # LabelEncoder
│   ├── return_scaler.save                  # Scaler sortie (log-rendement)
│   ├── config.json                         # Hyperparamètres (d_model, nhead, layers, etc.)
│   └── feature_cols.json                   # Liste des 44 noms de features
│
├── Data/                                   # Données d'entraînement
│   ├── ALL_CLEANED.csv                     # Dataset complet nettoyé
│   ├── ALL_FEATURES.csv                    # Matrice de features construite
│   └── data_report.csv                     # Rapport qualité des données
│
├── face_data/                              # Images faciales encodées (persistance)
├── temp_faces/                             # Images temporaires (auth en cours)
├── users.db                                # Base de données SQLite (racine projet)
├── Dockerfile                              # Conteneurisation Docker (Python 3.11)
├── requirements.txt                        # Dépendances Python
└── DOCUMENTATION.md                        # Ce fichier
```

---

## 5. Modèles d'Intelligence Artificielle

La plateforme propose **trois approches complémentaires** de prédiction. Chacune exploite des sources de données et une architecture différente, permettant à l'utilisateur de croiser les signaux.

---

### 5.1 Modèle Sentiment — Analyse des actualités

**Type :** Modèle à base de règles (rule-based NLP)
**Service :** `services/lstm_service.py` (fonction `_compute_signal`)
**Source de données :** Articles de presse financière (CSV GitHub, mis à jour quotidiennement)

#### Description

Ce modèle ne repose pas sur un réseau de neurones mais sur l'**agrégation de scores de sentiment** extraits automatiquement d'articles de presse financière. Le score de chaque article (entre -1 et +1) est calculé en amont via un modèle NLP de traitement de texte financier, puis stocké dans un fichier CSV centralisé.

#### Pipeline de calcul du signal

```
1. Chargement du CSV GitHub (ALL_ARTICLES_MASTER.csv)
   Colonnes : symbol, date_publication, score_sentiment, score_pondere, confiance

2. Filtrage temporel
   → Articles des 48 dernières heures (ou 15 derniers si aucun récent)

3. Calcul du score agrégé
   → Si colonne score_pondere : moyenne directe
   → Sinon : mean(score_sentiment × confiance)
   → Calcul de la confiance globale : min(|score| × (articles/10) × 100, 95)%

4. Classification
   score > +0.15  →  HAUSSIER (signal ACHETER)
   score < -0.15  →  BAISSIER (signal VENDRE)
   |score| ≤ 0.15 →  NEUTRE   (signal SURVEILLER)

5. Validité du signal : ~48h (lié à la fraîcheur des articles)
```

#### Points forts
- Capture les **chocs exogènes** (annonces de résultats, scandales, régulations) non visibles dans les données de prix
- Très réactif aux événements : mise à jour dès que de nouveaux articles sont publiés
- Particulièrement efficace pour les actifs très médiatisés : Tesla, Bitcoin, NVIDIA

---

### 5.2 Modèle BiLSTM (Long Short-Term Memory)

**Type :** Deep Learning — Réseau de neurones récurrents bidirectionnel
**Framework :** TensorFlow / Keras
**Fichier modèle :** `Modèle IA/global_return_lstm.keras`
**Service :** `services/lstm_service.py`

#### Architecture

Le modèle est un **BiLSTM** (Bidirectional Long Short-Term Memory) qui lit la séquence de données à la fois dans le sens chronologique (passé → présent) et dans le sens inverse (présent → passé), capturant ainsi des dépendances dans les deux directions.

```
Entrée : Tenseur (batch_size, 30 jours, 14 features)
              ↓
[Symbol Embedding] → vecteur 8D concaténé à la séquence
              ↓
[BiLSTM Layer(s)]
    → Lecture avant  (t=0 → t=29)
    → Lecture arrière (t=29 → t=0)
    → Sortie : représentation enrichie de la séquence
              ↓
[Dense Layer] → [Activation Sigmoid]
              ↓
Sortie : probabilité ∈ [0.0, 1.0]
    → ≥ 0.52 : signal ACHETER
    → < 0.52 : signal VENDRE
```

#### 14 Features engineered

Ces 14 indicateurs techniques sont calculés à partir des données OHLCV brutes récupérées de Yahoo Finance :

| Feature | Catégorie | Calcul |
|---------|-----------|--------|
| `ret1` | Rendement | (Close[t] - Close[t-1]) / Close[t-1] |
| `ret3` | Rendement | Rendement cumulé sur 3 jours |
| `ret5` | Rendement | Rendement cumulé sur 5 jours |
| `trend_s` | Tendance court terme | MA5 / MA10 - 1 |
| `trend_l` | Tendance long terme | MA10 / MA20 - 1 |
| `mom3` | Momentum | Close[t] / Close[t-3] - 1 |
| `mom10` | Momentum | Close[t] / Close[t-10] - 1 |
| `vol10` | Volatilité | Écart-type des rendements sur 10 jours |
| `vol_ratio` | Volatilité relative | vol10 / vol30 |
| `rsi14` | Oscillateur | RSI (Relative Strength Index) 14 périodes |
| `rsi7` | Oscillateur | RSI 7 périodes |
| `atr` | Risque | Average True Range normalisé par le prix |
| `bb` | Bandes de Bollinger | Position dans les bandes [0, 1] |
| `volr` | Volume | Volume courant / MA volume 10j (clipé [0, 1]) |

#### Pipeline de prédiction complet

```python
# Étape 1 : Téléchargement données (120j pour fenêtres glissantes)
hist = yf.Ticker(ticker).history(period="120d", interval="1d")

# Étape 2 : Feature engineering → DataFrame (120, 14 features)
df = _build_features(hist).dropna(subset=FEATURES).reset_index(drop=True)

# Étape 3 : Encodage du symbole
sym_id = int(encoder.transform([ticker])[0])

# Étape 4 : Extraction dernière fenêtre 30 jours → shape (30, 14)
window = df[FEATURES].values[-SEQ_LEN:]  # SEQ_LEN = 30

# Étape 5 : Normalisation RobustScaler + clip [-5, 5]
window_scaled = np.clip(scaler.transform(window), -5, 5).astype(np.float32)

# Étape 6 : Inférence BiLSTM
prob = model.predict(
    [window_scaled.reshape(1, 30, 14), np.array([[sym_id]])],
    verbose=0
).flatten()[0]

# Étape 7 : Génération du signal et du rendement estimé
signal = "ACHETER" if prob >= 0.52 else "VENDRE"
return_pct = (prob - 0.5) * 2 * vol10_last  # rendement estimé proportionnel à la volatilité
direction_prob = prob  # probabilité directionnelle affichée
```

#### Backtest 180 jours

La fonction `_run_backtest_lstm()` simule un portefeuille sur les 180 derniers jours en mode **rolling window** : pour chaque jour `i`, elle prédit le signal à partir de la fenêtre `[i-30 : i]` et applique le PnL réel du lendemain.

```
Pour chaque jour i de bt_start à N-1 :
   1. Fenêtre = données [i-30 : i] → normalisation → prédiction
   2. Signal = ACHETER si prob ≥ 0.52, sinon VENDRE
   3. PnL réel = rendement réel (Close[i+1] - Close[i]) / Close[i]
      → position longue si ACHETER : PnL = +rendement réel
      → position courte si VENDRE  : PnL = -rendement réel
   4. Portefeuille *= (1 + PnL)
   5. Buy & hold = start_amount × Close[i+1] / Close[bt_start]

Retour : {dates, portfolio_values, buy_hold_values, métriques}
```

---

### 5.3 Modèle Transformer Hybride

**Type :** Deep Learning — Transformer Encoder avec fusion prix + sentiment
**Framework :** PyTorch
**Fichier modèle :** `Model AI Transformer/transformer_model.pt`
**Classe :** `HybridTransformerBounded`
**Service :** `services/transformer_service.py`

#### Description

Le Transformer Hybride est l'architecture la plus sophistiquée de la plateforme. Contrairement au BiLSTM qui ne traite que les données de prix, ce modèle **fusionne explicitement** les données de prix et les données de sentiment (articles de presse) dans un unique vecteur de 44 features par pas de temps. Le mécanisme d'**attention multi-têtes** du Transformer permet au modèle d'apprendre automatiquement quels jours passés (et quelles combinaisons features/sentiment) sont les plus pertinents pour prédire le lendemain.

#### Architecture : HybridTransformerBounded

```
Entrée : (batch_size, 60 jours, 44 features)
              ↓
[Projection linéaire] : 44 → 64 (d_model)
              ↓
[Symbol Embedding] : 8 symboles → vecteurs 64D (ajoutés au signal)
              ↓
[Positional Encoding] : encodage de position appris (par-position)
              ↓
[TransformerEncoder] × 2 couches
  ┌─ MultiHeadAttention (nhead=4, 4 têtes d'attention)
  ├─ Add & LayerNorm
  ├─ FeedForward (64 → 256 → 64) avec GELU
  └─ Add & LayerNorm
              ↓
[Token CLS] → extraction du vecteur de résumé
              ↓
[LayerNorm] → [Dense 64→32] → [GELU] → [Dense 32→1] → [Tanh × 0.05]
              ↓
Sortie : log-rendement ∈ [-0.05, +0.05]
    → > 0 : signal ACHETER
    → < 0 : signal VENDRE
```

#### Hyperparamètres (config.json)

```json
{
  "d_input"   : 44,
  "d_model"   : 64,
  "nhead"     : 4,
  "num_layers": 2,
  "d_ff"      : 256,
  "dropout"   : 0.15,
  "max_logret": 0.05,
  "window"    : 60
}
```

#### 44 Features (16 prix + 28 sentiment)

**Features de prix (16) :**

| Feature | Description |
|---------|-------------|
| `open, high, low, close, volume` | OHLCV bruts |
| `close_lag1` | Prix de clôture J-1 |
| `ma_5` | Moyenne mobile 5 jours |
| `volatility` | Écart-type glissant |
| `rsi` | RSI 14 périodes |
| `macd` | MACD (convergence/divergence) |
| `bb_position` | Position dans les Bandes de Bollinger |
| `ret_1, ret_5` | Rendements sur 1 et 5 jours |
| `logret` | Log-rendement quotidien |
| `sma_ratio` | Ratio close / SMA |
| `hl_range` | Amplitude High-Low normalisée |

**Features de sentiment (28) :**

| Catégorie | Features | Nombre |
|-----------|----------|--------|
| Instantanées | sentiment_score, articles_count, sentiment_weighted, has_news | 4 |
| Décalages temporels | sentiment_lag_{1,2,3,5}j, articles_lag_{1,2,3,5}j | 8 |
| Moyennes glissantes | sentiment_mean_{3,5,7,14}j | 4 |
| Sommes glissantes | sentiment_sum_{3,5,7,14}j, articles_sum_{3,5,7,14}j | 8 |
| EMA sentiment | sentiment_ema_5, sentiment_ema_10 | 2 |
| Signaux binaires | strong_positive_sentiment, strong_negative_sentiment | 2 |

#### Pipeline de prédiction complet

```python
# Étape 1 : Chargement modèle + config (cache mémoire)
model, scaler, encoder, cfg = _load()
window = cfg.get('window', 60)

# Étape 2 : Données prix (150j) et articles depuis GitHub
hist = yf.Ticker(ticker).history(period="150d", interval="1d")
articles = _get_articles()  # cache 5 minutes (DataFrame complet)

# Étape 3 : Construction des 44 features (fusion prix + sentiment)
df_feat = _build_features(ticker, df_price, articles)
# df_feat shape : (N, 44)

# Étape 4 : Normalisation StandardScaler
feat_norm = np.nan_to_num(scaler.transform(df_feat[FEATURE_COLS].values))

# Étape 5 : Encodage symbole
sym_id = int(encoder.transform([ticker])[0])

# Étape 6 : Inférence PyTorch (fenêtre de 60 jours)
with torch.no_grad():
    seq = torch.FloatTensor(feat_norm[-window:]).unsqueeze(0)  # (1, 60, 44)
    sym = torch.LongTensor([[sym_id]])
    logret = model(seq, sym).item()  # log-rendement prédit ∈ [-0.05, 0.05]

# Étape 7 : Conversion en signal et prix prédit
direction_prob = 0.5 + logret / (2 * max_logret)  # [0, 1]
signal = 'ACHETER' if logret > 0 else 'VENDRE'
predicted_price = current_price * np.exp(logret)
return_pct = (np.exp(logret) - 1) * 100  # rendement prédit en %
```

#### Source des articles (GitHub CSV)

```
URL : https://raw.githubusercontent.com/[repo]/main/ALL_ARTICLES_MASTER.csv
Colonnes : symbol, date_publication, score_sentiment, [score_pondere], [confiance]
Cache : 5 minutes en mémoire (variable globale _articles_cache)
Fallback : DataFrames vides si réseau indisponible (prédiction sans sentiment)
```

---

### 5.4 Comparaison des trois modèles

| Critère | Sentiment | BiLSTM | Transformer |
|---------|-----------|--------|-------------|
| **Type** | Rule-based | Deep Learning RNN | Deep Learning Attention |
| **Framework** | Python pur | TensorFlow/Keras | PyTorch |
| **Features** | Score NLP agrégé | 14 indicateurs techniques | 44 (prix + sentiment) |
| **Fenêtre temporelle** | 48h d'articles | 30 jours | 60 jours |
| **Sortie** | Signal discret | Probabilité [0,1] | Log-rendement continu |
| **Points forts** | Événements exogènes | Patterns techniques | Fusion prix + news |
| **Complexité** | Faible | Moyenne | Élevée |
| **Temps d'inférence** | < 1s | ~2s | ~3s |
| **Backtest** | Oui (180j, step=3j) | Oui (180j, batch) | Oui (180j, batch) |

#### Comparaison de modèles dans le chatbot

Quand l'utilisateur demande "quel modèle pour Tesla ?", la plateforme :
1. Lance les **3 backtests en parallèle** (`ThreadPoolExecutor`, max_workers=3)
2. Affiche une **modal flottante déplaçable** avec pour chaque modèle :
   - Courbe SVG du portefeuille IA vs buy & hold (180 jours)
   - Gain/perte total en euros et en pourcentage
   - Valeur finale du portefeuille, taux de réussite des décisions
   - Explication textuelle : "Si vous aviez investi 500€ depuis [date]..."
   - Lien direct "Voir dans Mon Suivi" avec modèle pré-sélectionné
3. Envoie un **message de synthèse** dans le chat avec les vrais résultats
4. Met à jour l'**historique LLM** pour que les recommandations futures reflètent les données réelles

---

## 6. Authentification biométrique — Reconnaissance faciale

### Vue d'ensemble

La plateforme propose une authentification optionnelle par visage, sans mot de passe. Cette fonctionnalité peut être activée lors de l'inscription ou depuis la page Profil.

### Modules impliqués

| Fichier | Rôle |
|---------|------|
| `services/face_auth.py` | Capture webcam, détection visage, stockage |
| `services/face_comparator.py` | Algorithme de comparaison multi-critères |
| `assets/camera.js` | Interface webcam navigateur (capture base64) |
| `pages/face_login.py` | Page de connexion biométrique |
| `pages/signup.py` | Capture initiale lors de l'inscription |
| `pages/profil.py` | Gestion (activer/désactiver/recapturer) |

### Algorithme de comparaison (face_comparator.py)

La comparaison utilise **4 métriques complémentaires** pondérées, conçues pour être robustes aux changements d'éclairage, de pose et d'expression :

```
Score final = (Cross-corrélation × 0.50)
            + (Contours Sobel   × 0.30)
            + (MSE              × 0.10)
            + (Histogramme      × 0.10)
```

| Métrique | Poids | Méthode OpenCV | Justification |
|----------|-------|----------------|---------------|
| **Cross-corrélation** | 50% | `cv2.TM_CCOEFF_NORMED` | Correspondance pixel par pixel — précision maximale |
| **Contours Sobel** | 30% | Gradient Sobel X+Y → corrélation | Robustesse aux variations d'éclairage (structure des contours) |
| **MSE** | 10% | Erreur quadratique moyenne normalisée | Similitude globale de l'image |
| **Histogramme** | 10% | Comparaison histogrammes niveaux de gris | Distribution tonale générale |

**Pénalité** : si la détection Haar Cascade ne trouve pas de visage dans l'une des deux images → score × **0.5** (protection contre les tentatives avec des photos non-humaines).

**Seuil de validation** : score ≥ **0.50** (50%) pour valider la correspondance et ouvrir la session.

### Flux d'authentification complet

```
[Utilisateur sur /face-login]
         ↓
camera.js active la webcam (navigator.mediaDevices.getUserMedia)
         ↓
Capture frame toutes les 2s → canvas.toDataURL("image/jpeg") → base64
         ↓
POST /api/face-login   {image: "data:image/jpeg;base64,..."}
         ↓
[Serveur Flask — face_auth.py]
1. Décodage base64 → tableau NumPy (OpenCV)
2. Conversion en niveaux de gris
3. Détection visage : cv2 Haar Cascade (haarcascade_frontalface_default.xml)
4. Recadrage ROI → redimensionnement 100×100
         ↓
[Serveur Flask — face_comparator.py]
5. Chargement image référence depuis table users (face_image en base64)
6. Même prétraitement sur l'image de référence
7. Calcul 4 métriques → score composite
8. Application pénalité si visage non détecté
         ↓
score ≥ 0.50 ?
   OUI → Création session, redirect vers /
   NON → {"match": false} → retry automatique côté client (2s)
```

### Stockage des visages

Les images faciales sont stockées sous forme de **chaînes base64** dans la colonne `face_image` de la table `users`. Cela évite la gestion d'un système de fichiers séparé et facilite les sauvegardes. Le dossier `face_data/` contient les fichiers pickle de secours.

---

## 7. Assistant IA conversationnel (Chatbot)

### Technologie

| Composant | Détail |
|-----------|--------|
| **Modèle LLM** | LLaMA 3.3 70B Versatile (Meta AI) |
| **Fournisseur** | Groq Cloud (inférence ~200 tokens/s) |
| **Protocol** | Server-Sent Events (SSE) — streaming |
| **Contexte envoyé** | System prompt + 6 derniers messages |
| **Température** | 0.0 (déterministe) |
| **Max tokens** | 1024 par réponse |

### Interface utilisateur

Le chatbot est un **panel flottant** positionné en bas à droite de l'écran, accessible depuis toutes les pages de la plateforme. Il dispose de :

- **Streaming temps réel** : les tokens s'affichent lettre par lettre
- **Historique multi-conversations** : stocké en `localStorage`, jusqu'à 30 conversations × 60 messages
- **Dictée vocale** : bouton microphone → `SpeechRecognition` API
- **Drag & drop** : le panel peut être repositionné librement
- **Badge de notification** : indicateur "!" si une carte de confirmation attend

### Fonctionnalité 1 — Réponses conversationnelles

Le system prompt (124 lignes) encode la connaissance complète de la plateforme :
- Explication des 3 modèles IA et de leurs différences
- Guide de navigation entre les pages
- FAQ sur les fonctionnalités (backtest, suivi, témoignages)
- Règles strictes de comportement (ne jamais inventer de données)

### Fonctionnalité 2 — Enregistrement d'investissements via marqueur `##INVEST##`

Mécanisme central pour l'enregistrement fiable des investissements depuis le chatbot :

**Côté LLM :** Quand l'utilisateur mentionne un investissement (montant, actif, modèle, action), le LLM génère un marqueur structuré à la fin de sa réponse :
```
##INVEST##{"symbol":"TSLA","model":"transformer","action":"ACHETER","amount":500}##
```

**Côté JavaScript (`chatbot.js`) :**
```javascript
// Détection par regex après streaming
const INVEST_RE = /##INVEST##\s*(\{[\s\S]*?\})\s*##/;
const markerData = INVEST_RE.exec(savedText);

// Le marqueur est TOUJOURS supprimé du texte affiché (invisible pour l'utilisateur)
botBubble.textContent = _stripInvestMarker(savedText);

// Affichage de la carte de confirmation si :
// 1. Marqueur trouvé ET montant > 0
// 2. Message utilisateur avait une intention d'investissement (_INTENT_RE)
if (markerData && markerData.amount > 0 && hadInvestIntent) {
    _showInvestConfirm(botBubble, markerData);
}
```

**Carte de confirmation :**
- Affiche symbole, modèle, action, montant
- Bouton "Enregistrer dans Mon Suivi" → `POST /api/chat-invest`
- En cas de succès : badge vert + lien vers Mon Suivi
- Renforcement dans l'historique LLM pour les investissements suivants

### Fonctionnalité 3 — Comparaison de modèles par backtest

**Détection de l'intention :**
```javascript
const _COMPARE_RE = /quel\s+mod.le|meilleur\s+mod.le|compare\s+.{0,15}mod.le|.../i;
const _SYMBOL_MAP = {'tesla':'TSLA', 'apple':'AAPL', 'nvidia':'NVDA', ...};
```

**Flux complet :**
```
Utilisateur : "quel modèle pour Tesla ?"
      ↓
1. _COMPARE_RE détecte l'intention de comparaison
2. _extractCompareSymbol() extrait "TSLA" depuis "Tesla"
3. LLM répond immédiatement (réponse générique basée sur sa connaissance)
4. Modal flottante déplaçable s'ouvre avec spinner "Simulation en cours..."
5. GET /api/backtest-compare?symbol=TSLA
   → 3 backtests lancés en parallèle (ThreadPoolExecutor)
   → ~15 secondes
6. Modal mise à jour avec :
   - Courbe SVG : portefeuille IA (cyan) vs buy & hold (pointillé blanc)
   - Explication textuelle : "Si vous aviez investi 500€ depuis le [date]..."
   - Grille stats : Valeur finale / Taux réussite / Sans IA
   - Badge "Recommandé" sur le meilleur modèle
   - Lien "Voir dans Mon Suivi" → /mon-suivi?mode=lstm&ticker=TSLA
7. Message de correction dans le chat avec les vrais résultats
8. Historique LLM mis à jour → recommandations futures fondées sur données réelles
```

### Fonctionnalité 4 — Détection de l'intention d'investissement

```javascript
// Regex détectant les formulations investissement en français
const _INTENT_RE = /j.?ai\s*(investi|mis\b|achet|vendu|suivi|fait\b)|enregistr|vas-y/i;
```

Exemples déclencheurs :
- "J'ai investi 500€ sur Tesla avec le Transformer"
- "J'ai mis 1000€ sur AAPL en suivant le LSTM"
- "Vas-y, enregistre mon investissement"

---

## 8. Pages et fonctionnalités détaillées

### Page d'accueil `/`

**Fonctionnalités :**
- **Barre de tickers** défilante en haut de page (BTC-USD, ETH-USD, NASDAQ, AAPL, GOOGL) — prix + variation %, rafraîchissement toutes les 5 minutes via `yfinance`
- **Sélecteur de modèle** : 3 boutons (Actualités / LSTM / Transformer) — paramètre URL `?mode=lstm`
- **Cartes de prédiction** (une par actif) :
  - Signal coloré (vert/rouge/gris) : HAUSSIER / BAISSIER / SURVEILLER
  - Prix d'entrée et prix courant
  - Rendement prédit (%)
  - Validité du signal (date d'expiration ~48h)
  - Tooltip au survol : explication détaillée du signal et du modèle
  - Bouton "Calculer mon gain" → redirection vers `/mon-suivi?mode=[modèle]`
- **Rafraîchissement automatique** toutes les 5 minutes (`dcc.Interval`)
- **Protection** : redirection automatique vers `/login` si non authentifié

---

### Page Mon Suivi `/mon-suivi`

**Fonctionnalités :**

**Section 1 — Prédictions et simulation**
- Vue en cartes des actifs avec signal IA courant (selon modèle sélectionné)
- Modal de simulation au clic sur un actif :
  - Saisie du montant et choix BUY/SELL
  - Calcul instantané du PnL simulé (prix entrée vs prix courant)
  - Enregistrement en base de données si l'utilisateur confirme

**Section 2 — Backtest "Et si j'avais suivi les conseils ?"**
- Simulation rolling 180 jours avec le modèle sélectionné
- Graphique Plotly interactif : courbe portefeuille IA vs courbe buy & hold
- Métriques affichées : valeur finale, gain/perte €, rendement %, taux de réussite des décisions, date de début
- Texte explicatif : "Si vous aviez investi X€ depuis [date] et suivi tous les conseils, vous auriez Y€"
- Champ pour modifier le montant de référence + bouton "Recalculer"

**Section 3 — Historique des trades personnels**
- Table des investissements enregistrés (date, symbole, modèle, montant, PnL)
- KPIs globaux : PnL total, win rate, nombre de trades fermés
- Export rapport PDF

**Navigation par URL :**
- `?mode=lstm` → mode BiLSTM activé immédiatement
- `?mode=transformer` → mode Transformer activé
- `?ticker=TSLA` → ouverture automatique de la simulation backtest pour Tesla

---

### Page Marchés `/actions_page`

**Fonctionnalités :**
- Intégration de la bibliothèque **Lightweight-charts** (TradingView-like) via iframe embarqué (`marche_chart.html`)
- **8 actifs** disponibles : AAPL, AMZN, BTC-USD, GOOGL, META, MSFT, NVDA, TSLA
- **2 ans d'historique** de prix en chandeliers japonais (OHLCV)
- Sélecteur d'actif dynamique
- API dédiée : `GET /api/ohlcv/<symbol>` → JSON [{time, open, high, low, close}]

---

### Page Analyse de sentiment `/analysis`

**Fonctionnalités :**
- **Cartes par actif** : score sentiment courant, nombre d'articles analysés (48h), signal HAUSSIER/BAISSIER/NEUTRE
- **Graphique temporel** (Plotly) : évolution du sentiment sur 30 jours + barres indiquant le nombre d'articles
- **Liste des derniers articles** : titre, date, score sentiment, lien vers la source
- Données chargées depuis le GitHub CSV (cache 15 minutes)

---

### Page Profil `/profil`

**Fonctionnalités :**
- **Informations personnelles** (modifiables) : prénom, nom, téléphone
- **KPIs trading automatiques** : total trades, trades fermés, win rate %, PnL total €, rendement moyen %
- **Gestion reconnaissance faciale** : activer / désactiver / recapturer l'image de référence
- **Visibilité publique** : partager ses statistiques sur la page Témoignages
- **Statut en ligne** : affichage sur la page Témoignages

---

### Pages d'authentification

**`/login` — Connexion classique**
- Champ email + mot de passe (toggle visibilité)
- Vérification bcrypt côté serveur
- Session stockée dans `dcc.Store(storage_type="session")` → `sessionStorage`
- Lien vers `/face-login`

**`/signup` — Inscription**
- Formulaire : prénom, nom, email, téléphone (+33)
- Mot de passe : 8 caractères min, 1 majuscule, 1 chiffre (validation temps réel)
- Capture faciale optionnelle via webcam (JavaScript)
- Hash bcrypt du mot de passe avant insertion en base

**`/face-login` — Connexion biométrique**
- Activation automatique webcam
- Détection et comparaison en temps réel (toutes les 2s)
- Connexion instantanée si score ≥ 0.50

---

### Page Témoignages `/temoignages`

**Fonctionnalités :**
- **Statistiques globales** de la plateforme : utilisateurs inscrits, note moyenne, win rate global, PnL cumulé
- **Témoignages approuvés** : contenu, note (étoiles), montant investi, gain réalisé, période
- **Formulaire de soumission** : texte + note + investissement → en attente de validation admin
- **Workflow de modération** : pending → approved (public) / rejected

---

### Panneau Administrateur `/admin`

**Accès restreint** : vérification `session["is_admin"] == True`

**Dashboard principal :**
- KPIs plateforme (actualisés toutes les 5s) : utilisateurs totaux, traders actifs, PnL global, win rate moyen

**Gestion des utilisateurs :**
- Table complète de tous les comptes
- Promotion / rétrogradation admin (toggle)
- Suppression avec confirmation modale (cascade : suppression user + tous ses trades)

**Statistiques :**
- Graphique des inscriptions sur 30 jours
- Répartition victoires/défaites (camembert)
- Classement des top traders par PnL

**Logs de connexion :**
- Historique de toutes les tentatives de connexion (date, email, succès/échec, IP)

**Modération des témoignages :**
- File d'attente des témoignages en attente
- Boutons Approuver / Rejeter

---

## 9. Base de données — Schéma complet

**Type :** SQLite  
**Fichier :** `users.db` à la racine du projet  
**Chemin :** calculé dynamiquement depuis `__file__` dans `database.py` (indépendant du répertoire de lancement)

### Table `users`

```sql
CREATE TABLE IF NOT EXISTS users (
    id           INTEGER  PRIMARY KEY AUTOINCREMENT,
    email        TEXT     UNIQUE NOT NULL,
    password     BLOB     NOT NULL,               -- Hash bcrypt (bytes)
    face_image   TEXT,                            -- Image faciale en base64
    is_admin     INTEGER  DEFAULT 0,              -- 0 = utilisateur, 1 = administrateur
    prenom       TEXT,
    nom          TEXT,
    telephone    TEXT,
    public_stats INTEGER  DEFAULT 0,              -- 0 = privé, 1 = affiché sur /temoignages
    is_online    INTEGER  DEFAULT 0,              -- 0 = hors ligne, 1 = en ligne
    created_at   DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### Table `user_trades`

```sql
CREATE TABLE IF NOT EXISTS user_trades (
    id                   INTEGER  PRIMARY KEY AUTOINCREMENT,
    user_email           TEXT     NOT NULL,
    symbol               TEXT     NOT NULL,        -- AAPL, TSLA, BTC-USD, etc.
    entry_price          REAL     NOT NULL,         -- Prix d'entrée ($)
    exit_price           REAL,                     -- Prix de sortie ($, NULL si trade ouvert)
    entry_date           DATETIME DEFAULT CURRENT_TIMESTAMP,
    exit_date            DATETIME,
    quantity             REAL,                     -- Montant investi en euros
    prediction_direction TEXT,                     -- 'up' ou 'down' (signal du modèle)
    actual_direction     TEXT,                     -- Direction réelle constatée
    pnl                  REAL,                     -- Profit/perte en euros
    pnl_percentage       REAL,                     -- Rendement en %
    status               TEXT     DEFAULT 'open',  -- 'open' ou 'closed'
    model_type           TEXT     DEFAULT 'sentiment', -- 'sentiment', 'lstm', 'transformer'
    FOREIGN KEY (user_email) REFERENCES users(email)
);
```

### Table `predictions_log`

```sql
CREATE TABLE IF NOT EXISTS predictions_log (
    id                   INTEGER  PRIMARY KEY AUTOINCREMENT,
    symbol               TEXT     NOT NULL,
    prediction_price     REAL,
    prediction_direction TEXT,                     -- 'ACHETER' ou 'VENDRE'
    confidence           REAL,
    model_version        TEXT,
    predicted_date       DATE,
    actual_price         REAL,
    actual_direction     TEXT,
    accuracy             BOOLEAN,
    created_at           DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### Table `testimonials`

```sql
CREATE TABLE IF NOT EXISTS testimonials (
    id          INTEGER  PRIMARY KEY AUTOINCREMENT,
    user_email  TEXT     NOT NULL,
    user_name   TEXT     NOT NULL,
    content     TEXT     NOT NULL,
    rating      INTEGER  DEFAULT 5,            -- Note de 1 à 5 étoiles
    investment  REAL,                          -- Montant investi (€)
    gain        REAL,                          -- Gain réalisé (€)
    period      TEXT,                          -- Ex : "6 mois"
    status      TEXT     DEFAULT 'pending',    -- 'pending', 'approved', 'rejected'
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
    approved_at DATETIME,
    FOREIGN KEY (user_email) REFERENCES users(email)
);
```

---

## 10. APIs REST

Toutes les routes API sont définies dans `app.py` et montées sur le serveur Flask de Dash (`app.server`).

| Méthode | Route | Corps / Params | Réponse | Description |
|---------|-------|----------------|---------|-------------|
| `POST` | `/api/chat` | `{messages: [...]}` | SSE stream | Streaming LLaMA 3.3 70B |
| `POST` | `/api/chat-invest` | `{email, symbol, model, action, amount}` | `{success, price}` | Enregistrement investissement |
| `POST` | `/api/chat-detect-invest` | `{messages: [...]}` | `{invest: {...}}` | Extraction JSON investissement |
| `GET`  | `/api/model-compare` | `?email=&symbol=` | `{models, best_model}` | Comparaison sur trades personnels |
| `GET`  | `/api/backtest-compare` | `?symbol=TSLA` | `{models, best_model, start}` | Backtests 180j en parallèle |
| `GET`  | `/api/ohlcv/<symbol>` | — | `[{time, open, high, low, close}]` | Chandeliers pour Lightweight-charts |
| `POST` | `/api/face-login` | `{image: "base64..."}` | `{match, email, session}` | Authentification faciale |

---

## 11. Pipeline de données et sources

### Données de marché (prix OHLCV)

```
Source primaire : yfinance
   → yf.Ticker(symbol).history(period, interval)
   → DataFrame OHLCV (Open, High, Low, Close, Volume)
   → Utilisé pour : prédictions temps réel, backtest, graphiques

Source secondaire : Alpha Vantage (si clé configurée)
   → Données intraday (1min, 5min, 15min, 60min)
   → Utilisé comme fallback si yfinance retourne données insuffisantes
```

### Données de sentiment (articles de presse)

```
Source : GitHub CSV (ALL_ARTICLES_MASTER.csv)
   → Téléchargé à chaque requête (timeout 15s)
   → Cache mémoire : 5 minutes (variable globale dans transformer_service.py)
   → Colonnes : symbol, date_publication, score_sentiment, score_pondere, confiance
   → Mis à jour quotidiennement par un pipeline externe
```

### Backtest rolling window (180 jours)

```
1. Téléchargement données brutes (180 + SEQ_LEN + 50 jours de sécurité)
2. Feature engineering sur l'ensemble de la période (pas de fuite de données)
3. Normalisation globale (scaler fitted hors ligne lors de l'entraînement)

4. Pour chaque jour i de bt_start à N-1 :
   a. Fenêtre [i-SEQ_LEN : i] → inférence → signal
   b. Rendement réel [i → i+1] → PnL selon signal
   c. Mise à jour portefeuille et buy & hold

5. Retour : {
      portfolio: [valeur jour 1, ..., valeur jour 180],
      buy_hold:  [valeur buy&hold jour 1, ..., jour 180],
      final_value, total_return, win_rate, n_trades, wins, losses
   }
```

---

## 12. Installation et démarrage

### Prérequis

- Python 3.11+
- Clé API Groq (gratuite sur [console.groq.com](https://console.groq.com))

### Installation locale

```bash
# 1. Cloner le dépôt
git clone <url-du-depot>
cd Projet4A_PredictionsBoursieres-main

# 2. Installer les dépendances Python
pip install -r requirements.txt

# 3. Créer le fichier d'environnement
cd "Interface Graphique"
cat > .env << EOF
GROQ_API_KEY=votre_cle_groq_ici
ALPHA_VANTAGE_KEY=optionnel
EOF

# 4. Lancer l'application
python app.py
```

Accès : **http://localhost:8050**

### Compte administrateur par défaut

Créé automatiquement au premier démarrage par `init_db()` :
- **Email :** `admin@ensim.fr`
- **Mot de passe :** `Admin1234!`

### Variables d'environnement

| Variable | Obligatoire | Description |
|----------|-------------|-------------|
| `GROQ_API_KEY` | Oui | Clé API Groq pour le chatbot LLaMA 3.3 70B |
| `ALPHA_VANTAGE_KEY` | Non | Clé Alpha Vantage (backup données intraday) |

### Déploiement Docker

```bash
# Build
docker build -t predictions-boursieres .

# Run (port 7860 par défaut dans le Dockerfile)
docker run -p 7860:7860 -e GROQ_API_KEY=votre_cle predictions-boursieres
```

---

## 13. Architecture Dash — Comment les modèles sont connectés au frontend

### 13.1 Principe de Dash : callbacks réactifs

Dash est un framework Python qui permet de construire des interfaces web **entièrement en Python**, sans écrire de JavaScript côté applicatif. Son mécanisme central est le **callback** : une fonction Python décorée avec `@callback` qui se déclenche automatiquement quand un composant de l'interface change.

```
Composant A change (Input)
        ↓
Dash envoie une requête HTTP POST au serveur Flask
        ↓
La fonction Python @callback s'exécute
        ↓
La valeur de retour met à jour le composant B (Output)
```

#### Exemple concret : sélection d'un modèle sur la page d'accueil

```python
# pages/home.py

@callback(
    Output("home-pred-mode", "data"),       # → met à jour le store du mode
    Output("home-btn-lstm", "className"),   # → change la classe CSS du bouton
    Input("home-btn-lstm", "n_clicks"),     # ← déclenché au clic
    prevent_initial_call=True,
)
def toggle_mode(n_clicks):
    return "lstm", "home-mode-btn home-mode-active"
```

Quand l'utilisateur clique sur "LSTM" :
1. Dash détecte le clic → requête POST vers Flask
2. La fonction `toggle_mode()` s'exécute côté serveur Python
3. Elle retourne `"lstm"` → stocké dans `dcc.Store(id="home-pred-mode")`
4. Ce changement de store déclenche automatiquement le callback suivant

---

### 13.2 Mécanisme dcc.Store — Partage d'état entre callbacks

`dcc.Store` est un composant invisible dans le DOM qui stocke des données JSON dans le navigateur. Il permet de transmettre des données entre plusieurs callbacks sans les afficher.

| Type de store | Stockage navigateur | Durée de vie |
|---------------|--------------------|-|
| `storage_type="session"` | `sessionStorage` | Jusqu'à fermeture de l'onglet |
| `storage_type="local"` | `localStorage` | Persistant entre sessions |
| `storage_type="memory"` | RAM JavaScript | Jusqu'au rechargement de la page |

**Exemple : session utilisateur**
```python
# app.py — layout
dcc.Store(id="session-store", storage_type="session")

# Après login réussi — pages/login.py
@callback(
    Output("session-store", "data"),   # Stocke l'email + is_admin dans sessionStorage
    Input("login-btn", "n_clicks"),
    State("login-email", "value"),
    State("login-password", "value"),
)
def process_login(n_clicks, email, password):
    user = verify_user(email, password)    # bcrypt check
    if user:
        return {"email": email, "is_admin": user["is_admin"]}
    return no_update
```

**Le chatbot JS lit ce store pour récupérer l'email :**
```javascript
// assets/chatbot.js
function _getUserEmail() {
    const raw = sessionStorage.getItem("session-store");  // clé Dash = id du Store
    const d   = JSON.parse(raw);
    return d?.email ?? null;
}
```

---

### 13.3 Mécanisme dcc.Interval — Rafraîchissement automatique

`dcc.Interval` est un composant qui génère des événements à intervalle régulier. Il permet de déclencher des callbacks périodiquement sans action utilisateur.

```python
# app.py
dcc.Interval(id="interval-component", interval=5*60*1000, n_intervals=0)
#                                              ↑ 5 minutes en millisecondes

# home.py
dcc.Interval(id="home-init", interval=300, max_intervals=1)
#                                   ↑ 300ms après chargement, une seule fois

# mon_suivi.py
dcc.Interval(id="suivi-auto", interval=5 * 60 * 1000)  # refresh toutes les 5 min
```

Ces composants génèrent des `n_intervals` croissants → utilisés comme `Input` dans les callbacks de chargement de données.

---

### 13.4 Chargement parallèle avec ThreadPoolExecutor

Puisque chaque prédiction nécessite un appel réseau (yfinance) ET une inférence modèle, les 7 actifs sont traités en **parallèle** pour réduire le temps de chargement :

```python
# pages/home.py — render_home_predictions()

from concurrent.futures import ThreadPoolExecutor, as_completed
from services.lstm_service import predict as lstm_predict

def _fetch(ticker):
    return ticker, lstm_predict(ticker)    # appel réseau + inférence

with ThreadPoolExecutor(max_workers=7) as ex:
    futures = {ex.submit(_fetch, t): t for t in _COMPANIES}
    preds   = {}
    for f in as_completed(futures):
        ticker, result = f.result()
        preds[ticker]  = result

# Rendu des cartes Dash avec les résultats
cards = [_lstm_card(ticker, company, preds.get(ticker))
         for ticker, company in _COMPANIES.items()]
return cards   # → Output("home-pred-grid", "children")
```

Sans parallélisme : 7 × ~2s = **14s** de chargement  
Avec ThreadPoolExecutor : max(2s) ≈ **2-3s** de chargement

---

## 14. Flux d'intégration complets bout en bout

### Flux 1 — Prédictions IA vers la page d'accueil

```
UTILISATEUR charge /
        ↓
[Dash] page d'accueil rendue côté serveur Python
       → Layout HTML envoyé au navigateur
       → dcc.Interval(id="home-init", interval=300ms, max_intervals=1) créé
        ↓
300ms plus tard : n_intervals passe de 0 à 1 → déclenche :
        ↓
@callback(
    Output("home-pred-grid", "children"),   ← les cartes de prédiction
    Input("home-init", "n_intervals"),      ← déclencheur
    Input("home-pred-mode", "data"),        ← mode actuel (sentiment/lstm/transformer)
    State("session-store", "data"),         ← email utilisateur
)
def render_home_predictions(_, mode, session):
        ↓
[Vérification session] — si non connecté → mur de connexion
        ↓
[Choix du service selon mode]
   mode == "lstm" :
      ThreadPoolExecutor(max_workers=7)
         → 7 threads en parallèle
         → chacun appelle lstm_service.predict(ticker)
              → yf.Ticker(ticker).history(period="120d")   [réseau]
              → _build_features(hist)                       [calcul 14 features]
              → scaler.transform(window[-30:])              [normalisation]
              → model.predict([seq, sym_id])                [inférence Keras BiLSTM]
              → retourne {signal, probability, return_pct, entry_price, current_price}
         → preds = {ticker: result, ...}
      → [_lstm_card(ticker, ...) for ticker in COMPANIES]   [rendu HTML Dash]

   mode == "transformer" :
      ThreadPoolExecutor(max_workers=7)
         → chacun appelle transformer_service.predict(ticker)
              → yf.Ticker(ticker).history(period="150d")   [réseau]
              → _get_articles()                             [GitHub CSV, cache 5min]
              → _build_features(ticker, df_price, articles) [44 features]
              → scaler.transform(feat[-60:])                [normalisation]
              → torch.no_grad() → model(seq, sym_id)        [inférence PyTorch]
              → retourne {signal, direction_prob, return_pct, predicted_price, ...}

   mode == "sentiment" :
      → _load_articles()                                    [GitHub CSV]
      → [_compute_signal(df, ticker) for ticker in COMPANIES]
              → filtrage 48h, calcul score_pondere
              → retourne {rec: "ACHETER"/"VENDRE"/"SURVEILLER", ...}
        ↓
RETOUR : liste de html.Div (cartes Dash) → injectés dans Output("home-pred-grid")
        ↓
[Navigateur] Dash React reçoit les nouveaux composants → re-render DOM
```

---

### Flux 2 — Backtest "Et si j'avais suivi les conseils ?" (Mon Suivi)

```
UTILISATEUR clique sur une carte actif → modal s'ouvre → clique "Voir si j'avais suivi"
        ↓
@callback(
    Output("suivi-backtest-bg", "className"),         ← afficher la modal backtest
    Output("suivi-backtest-ticker-store", "data"),    ← stocker le ticker sélectionné
    Input({"type": "suivi-bt-open", "index": ALL}, "n_clicks"),
)
def toggle_backtest_modal(card_clicks, close_n):
    ticker = triggered["index"]   # ex: "TSLA"
    return "suivi-modal-visible", ticker
        ↓
[Changement de suivi-backtest-ticker-store déclenche :]
        ↓
@callback(
    Output("suivi-backtest-chart", "figure"),         ← graphique Plotly
    Output("suivi-backtest-summary", "children"),     ← texte explicatif
    Output("suivi-backtest-stats", "children"),       ← métriques (valeur finale, etc.)
    Input("suivi-backtest-ticker-store", "data"),     ← ticker sélectionné
    State("suivi-mode", "data"),                      ← modèle actif
    State("suivi-backtest-amount-input", "value"),    ← montant de référence
)
def render_backtest(ticker, mode, amount):
    amount = float(amount) or 500.0

    if mode == "lstm":
        bt = _run_backtest_lstm(ticker, start_amount=amount, days=180)
        # → yf.Ticker(ticker).history(period="230d")
        # → feature engineering 14 features sur tout l'historique
        # → batch predict sur toutes les fenêtres [i-30:i]
        # → simulation portefeuille jour par jour

    elif mode == "transformer":
        from services.transformer_service import predict_backtest as trans_backtest
        bt = trans_backtest(ticker, start_amount=amount, days=180)
        # → yf.Ticker(ticker).history(period="300d")
        # → articles GitHub CSV
        # → 44 features sur tout l'historique
        # → batch predict PyTorch sur toutes les fenêtres [i-60:i]

    else:  # sentiment
        bt = _run_backtest(ticker, start_amount=amount, days=180)
        # → prix GitHub CSV
        # → articles → signal tous les 3 jours (step=3)
        # → simulation portefeuille

    # Construction graphique Plotly
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=dates, y=bt["portfolio"], name="Modèle IA", line=dict(color="#00d4ff")))
    fig.add_trace(go.Scatter(x=dates, y=bt["buy_hold"], name="Sans IA", line=dict(dash="dot")))
    return fig, summary_html, stats_html
        ↓
[Navigateur] Graphique Plotly rendu dans le DOM
```

---

### Flux 3 — Chatbot : streaming SSE bout en bout

Ce flux illustre comment un message de l'utilisateur voyage du navigateur jusqu'au modèle LLaMA 3.3 70B et revient en streaming.

```
UTILISATEUR tape un message → clique Envoyer
        ↓
[chatbot.js] sendMessage()
    input.value → text
    _history.push({role:"user", content: text})
    addMessage("user", text)          → bulle utilisateur dans le DOM
    showTyping()                      → indicateur "..." dans le DOM
        ↓
fetch('/api/chat', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({ messages: _history })   ← 6 derniers messages
})
        ↓
[Flask — app.py] @app.server.route('/api/chat', methods=['POST'])
def api_chat():
    messages = request.get_json()["messages"]
    from services.chat_service import stream_chat

    def generate():
        for chunk in stream_chat(messages):         ← générateur Python
            payload = json.dumps({"text": chunk})
            yield f"data: {payload}\n\n"            ← format SSE
        yield "data: [DONE]\n\n"

    return Response(
        stream_with_context(generate()),
        content_type='text/event-stream'            ← en-tête SSE
    )
        ↓
[services/chat_service.py] stream_chat(messages)
    full_messages = [{"role":"system", "content": SYSTEM_PROMPT}] + messages
    client = Groq(api_key=GROQ_API_KEY)
    stream = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=full_messages,
        max_tokens=1024,
        stream=True,                                ← streaming activé
        temperature=0.0,
    )
    for chunk in stream:
        delta = chunk.choices[0].delta
        if delta.content:
            yield delta.content                     ← envoyé token par token
        ↓
[Réseau] Chaque token traverse :
   Groq Cloud → Flask (stream_with_context) → HTTP SSE → Navigateur
        ↓
[chatbot.js] — lecture du ReadableStream
    const reader  = response.body.getReader()
    const decoder = new TextDecoder()
    while (true) {
        const { done, value } = await reader.read()
        if (done) break
        for (const line of decoder.decode(value).split('\n')) {
            if (!line.startsWith('data: ')) continue
            const chunk = line.slice(6).trim()
            if (chunk === '[DONE]') break
            const p = JSON.parse(chunk)
            if (p.text) {
                fullText += p.text
                botBubble.textContent = fullText    ← mise à jour DOM à chaque token
                scrollBottom()
            }
        }
    }
        ↓
[POST-STREAMING] analyse de la réponse complète
    botBubble.textContent = _stripInvestMarker(fullText)   ← suppression marqueur si présent
    _history.push({role:"assistant", content: fullText})
    _saveCurrentConversation()                              ← localStorage
        ↓
    Vérification marqueur ##INVEST## → si présent → _showInvestConfirm()
    Vérification comparaison modèles → si compareSymbol → _loadAndShowCompare()
```

---

### Flux 4 — Enregistrement d'investissement via le chatbot

```
UTILISATEUR : "J'ai investi 500€ sur TSLA avec le Transformer"
        ↓
[chatbot.js] sendMessage()
    _INTENT_RE.test(text) → true    (détection intention d'investissement)
    _extractInvestment(text, _history) → {symbol:"TSLA", model:"transformer", amount:500, action:"ACHETER"}
        ↓
[LLM génère (après streaming)] :
"Voici le récapitulatif de votre investissement :
##INVEST##{"symbol":"TSLA","model":"transformer","action":"ACHETER","amount":500}##"
        ↓
[chatbot.js] — post-streaming
    INVEST_RE.exec(savedText) → markerData = {symbol:"TSLA", model:"transformer", ...}
    botBubble.textContent = _stripInvestMarker(savedText)    ← marqueur invisible
    hadInvestIntent = true
    _showInvestConfirm(botBubble, markerData)
        ↓
    Carte de confirmation apparaît dans le chatbot :
    [Symbole: TSLA] [Modèle: Transformer] [Action: ACHETER] [Montant: 500€]
    [Bouton "Enregistrer dans Mon Suivi"]
        ↓
UTILISATEUR clique "Enregistrer"
        ↓
[chatbot.js] — listener click
    email = _getUserEmail()   ← depuis sessionStorage["session-store"]
    fetch('/api/chat-invest', {
        method: 'POST',
        body: JSON.stringify({email, symbol:"TSLA", model:"transformer", action:"ACHETER", amount:500})
    })
        ↓
[Flask — app.py] /api/chat-invest
    email, symbol, model, action, amount = request.get_json()
    # Validation : email non vide, symbol valide, montant > 0
        ↓
    # Récupération prix d'entrée actuel
    hist = yf.Ticker(symbol).history(period="5d", interval="1d")
    entry_price = float(hist["Close"].iloc[-1])
        ↓
    from services.tracking_service import save_followed_trade
    save_followed_trade(
        user_email=email,
        symbol="TSLA",
        signal="HAUSSIER",
        entry_price=entry_price,
        current_price=entry_price,
        amount=500,
        action="ACHETER",
        model_type="transformer"
    )
        ↓
    [database.py] INSERT INTO user_trades (user_email, symbol, entry_price, quantity,
                  prediction_direction, model_type, status) VALUES (...)
        ↓
    return jsonify({"success": True, "price": entry_price})
        ↓
[chatbot.js]
    card.innerHTML = "Investissement enregistré · TSLA · 500€ à $XXX.XX"
    _history.push({role:"user", content:"[Système] Investissement TSLA enregistré..."})
    _saveCurrentConversation()
```

---

### Flux 5 — Comparaison de modèles : du chatbot à la modal SVG

```
UTILISATEUR : "quel modèle tu me conseilles pour Tesla ?"
        ↓
[chatbot.js] sendMessage() — avant le fetch LLM
    _COMPARE_RE.test(text) → true
    _extractCompareSymbol(text, _history) :
        lo = " quel modèle tu me conseilles pour tesla "
        _findSymbol(lo) → cherche dans _SYMBOL_MAP → "tesla" → "TSLA"
    compareSymbol = "TSLA"
        ↓
[LLM répond en streaming] (réponse générique basée sur connaissance générale)
        ↓
[POST-STREAMING — chatbot.js]
    _loadAndShowCompare("TSLA", botBubble)
        ↓
    _openCompareModal("TSLA") :
        modal = document.createElement("div")
        modal.style.cssText = "left:XXpx; top:XXpx"  ← positionné à gauche du chatbot
        modal.innerHTML = "... spinner 'Simulation en cours...' ..."
        document.body.appendChild(modal)              ← ajouté au body (pas au chatbot)
        _makeDraggable(modal, header)                 ← drag & drop activé
        ↓
    fetch('/api/backtest-compare?symbol=TSLA')
        ↓
[Flask — app.py] /api/backtest-compare
    symbol = "TSLA"

    def _run_lstm():
        from pages.mon_suivi import _run_backtest_lstm
        return 'lstm', _run_backtest_lstm("TSLA", start_amount=500, days=180)

    def _run_transformer():
        from services.transformer_service import predict_backtest
        return 'transformer', predict_backtest("TSLA", start_amount=500, days=180)

    def _run_sentiment():
        from pages.mon_suivi import _run_backtest
        return 'sentiment', _run_backtest("TSLA", start_amount=500, days=180)

    with ThreadPoolExecutor(max_workers=3) as ex:
        futures = [ex.submit(f) for f in [_run_lstm, _run_transformer, _run_sentiment]]
        for f in as_completed(futures):
            key, bt = f.result()
            if bt:
                results[key] = {
                    'final':      bt['final_value'],    # ex: 547.23
                    'return_pct': bt['total_return'],   # ex: +9.4
                    'win_rate':   bt['win_rate'],        # ex: 55
                    'bh_final':   bt['buy_hold'][-1],   # ex: 523.10
                    'series':     _downsample(bt['portfolio'], n=30),  # 30 points
                    'bh_series':  _downsample(bt['buy_hold'], n=30),
                    ...
                }

    best = max(results.items(), key=lambda x: x[1]['return_pct'])[0]
    return jsonify({'symbol':'TSLA', 'models': results, 'best_model': best})
        ↓
[chatbot.js] — réponse JSON reçue (~15s plus tard)
    _populateCompareModal(body, "TSLA", data)
        pour chaque modèle k dans ["lstm", "transformer", "sentiment"] :
            gain    = m.final - 500
            gainCls = gain >= 0 ? 'cb-cmp-pos' : 'cb-cmp-neg'
            spark   = _makeSpark(m.series, m.bh_series, 400, 80)
            # SVG inline généré en JavaScript :
            # <svg viewBox="0 0 400 80">
            #   <polyline points="0,70 13,65 ..." stroke="#3ef5a0" />  ← portefeuille IA
            #   <polyline points="0,70 13,67 ..." stroke-dasharray="4,3" />  ← buy&hold
            # </svg>
        modal mis à jour avec HTML complet
        ↓
    _addBacktestSummaryToChat("TSLA", data) :
        addMessage("bot", "Voici les résultats réels sur 180 jours pour TSLA :
            • Actualités : +X€ (+Y%)
            • LSTM : -Z€ (-W%)
            • Transformer : ...
            Recommandation : [meilleur modèle]")
        _history.push({role:"assistant", content: ...})   ← LLM connaît maintenant les vraies données
```

---

### Flux 6 — Reconnaissance faciale : de la webcam à la session

```
UTILISATEUR va sur /face-login
        ↓
[pages/face_login.py] layout Dash
    html.Div(id="camera-container")
    html.Canvas(id="camera-canvas")
    dcc.Interval(id="face-interval", interval=2000)  ← capture toutes les 2s
        ↓
[assets/camera.js] — chargé par Dash
    navigator.mediaDevices.getUserMedia({video: true})
        → stream webcam → affiché dans <video> HTML
        ↓
    setInterval(() => {
        ctx.drawImage(video, 0, 0, 100, 100)    ← dessin frame 100×100 sur canvas
        const base64 = canvas.toDataURL("image/jpeg", 0.8)
        // Envoi au serveur via fetch
        fetch('/api/face-login', {
            method: 'POST',
            body: JSON.stringify({image: base64})
        })
        .then(r => r.json())
        .then(result => {
            if (result.match) {
                window.location.href = "/"   ← redirection si visage reconnu
            }
        })
    }, 2000)
        ↓
[Flask — app.py] /api/face-login (POST)
    image_b64 = request.get_json()["image"]
        ↓
    # Décodage base64 → numpy array (OpenCV)
    img_bytes = base64.b64decode(image_b64.split(",")[1])
    nparr     = np.frombuffer(img_bytes, np.uint8)
    frame     = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    gray      = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        ↓
    # Détection Haar Cascade
    face_cascade = cv2.CascadeClassifier("haarcascade_frontalface_default.xml")
    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.3, minNeighbors=5)
    if len(faces) > 0:
        x, y, w, h = faces[0]
        face_roi   = cv2.resize(gray[y:y+h, x:x+w], (100, 100))
    else:
        face_roi = cv2.resize(gray, (100, 100))
        ↓
    # Comparaison contre tous les utilisateurs ayant face_image != NULL
    conn = get_connection()
    users_with_face = conn.execute(
        "SELECT email, face_image FROM users WHERE face_image IS NOT NULL"
    ).fetchall()
        ↓
    best_score, best_email = 0, None
    for email, face_b64 in users_with_face:
        score = face_comparator.compare(face_roi, face_b64)
        # score = corr×0.5 + sobel×0.3 + mse×0.1 + hist×0.1
        if score > best_score:
            best_score  = score
            best_email  = email
        ↓
    if best_score >= 0.50:
        # Création de la session Flask
        session["email"]    = best_email
        session["is_admin"] = user["is_admin"]
        return jsonify({"match": True, "email": best_email})
    else:
        return jsonify({"match": False, "score": best_score})
        ↓
[camera.js] — si match=True
    window.location.href = "/"   ← accueil
    ↓
[Dash — app.py] mise à jour du dcc.Store session-store via callback Dash
```

---

### Flux 7 — Rendu des prédictions : du modèle aux composants HTML Dash

Ce flux montre comment une sortie numérique du modèle devient une carte visuelle dans le navigateur.

```python
# Sortie brute du modèle BiLSTM
prob = 0.63   # probabilité de hausse
return_pct = (0.63 - 0.5) * 2 * 0.018 * 100 = +0.47%
signal = "ACHETER"

# ─── services/lstm_service.py ───
predict("TSLA") → {
    "signal":        "ACHETER",
    "probability":   0.63,
    "return_pct":    0.47,
    "entry_price":   247.30,
    "current_price": 251.15,
    "change_pct":    +1.56,
    "confidence":    72.0,
    "signal_valid_to": "30 mai à 23h",
    "name": "Tesla",
    "is_lstm": True
}

# ─── pages/home.py — _lstm_card() ───
# Construit un html.Div Dash à partir du dictionnaire :
html.Div(className="home-pred-card home-pred-buy", children=[   # ← classe CSS selon signal
    html.Div(className="home-pred-top", children=[
        html.Div("TSLA", className="home-pred-ticker"),
        html.Div("Tesla", className="home-pred-company"),
    ]),
    html.Div(className="home-pred-rec home-pred-rec-buy", children="ACHETER"),  # badge coloré
    html.Div([
        html.Span("Prix d'entrée : "),
        html.Strong("$247.30"),
        html.Span(" → "),
        html.Strong("$251.15", style={"color": "#00ff87"}),   # vert car en hausse
    ]),
    html.Div(f"Rendement prédit : +0.47% · LSTM"),             # pied de carte
    # Tooltip au survol (html.Div caché, affiché par CSS :hover)
    html.Div(className="home-pred-tooltip", children=[
        html.Div("Bonne nouvelle — c'est le moment d'acheter", className="tooltip-title"),
        html.Div("Notre IA a analysé 30 jours de données...", className="tooltip-body"),
    ]),
    dcc.Link("Calculer mon gain", href="/mon-suivi?mode=lstm"),
])

# ─── Dash ───
# ce html.Div Python est sérialisé en JSON et envoyé au navigateur
# React (Dash frontend) le convertit en nœuds DOM :
# <div class="home-pred-card home-pred-buy">
#   <div class="home-pred-ticker">TSLA</div>
#   <div class="home-pred-rec home-pred-rec-buy">ACHETER</div>
#   ...
# </div>
```

---

### 14.1 Résumé : tableau des flux d'intégration

| Flux | Déclencheur | Traitement Python | Retour vers le navigateur |
|------|------------|-------------------|--------------------------|
| Prédictions accueil | `dcc.Interval` (300ms) | `lstm/transformer/sentiment_service.predict()` × 7 en parallèle | `html.Div[]` composants Dash |
| Backtest Mon Suivi | Clic card → `dcc.Store` → `@callback` | `_run_backtest_lstm/transformer/sentiment()` 180j | `go.Figure` Plotly + html.Div stats |
| Chatbot streaming | `fetch('/api/chat')` JS | `stream_chat()` → Groq LLaMA → `yield chunk` | SSE `data: {"text":"..."}` |
| Enregistrement invest | `fetch('/api/chat-invest')` JS | `save_followed_trade()` → SQLite INSERT | JSON `{"success": true, "price": X}` |
| Comparaison backtest | `fetch('/api/backtest-compare')` JS | 3 backtests `ThreadPoolExecutor` + downsample | JSON `{models, best_model, series[]}` |
| Reconnaissance faciale | `fetch('/api/face-login')` JS (2s) | OpenCV Haar + `face_comparator.compare()` | JSON `{"match": bool, "email": str}` |
| Chandeliers marché | `fetch('/api/ohlcv/TSLA')` JS | `yf.Ticker().history()` → format OHLCV | JSON `[{time, open, high, low, close}]` |

---

## Tableau récapitulatif des fonctionnalités

| Domaine | Fonctionnalité | Technologie |
|---------|----------------|-------------|
| **Prédiction IA** | 3 modèles distincts, 8 actifs, signaux ACHETER/VENDRE | TF/Keras, PyTorch, NLP |
| **Backtest** | Simulation portefeuille 180j glissants vs buy & hold | NumPy, Pandas, yfinance |
| **Comparaison modèles** | Modal flottante déplaçable, courbes SVG, recommandation | JavaScript, Flask, ThreadPool |
| **Trades utilisateur** | Enregistrement, historique, KPIs, export PDF | SQLite, Flask |
| **Chatbot IA** | LLaMA 3.3 70B, streaming SSE, enregistrement via marqueur | Groq, JavaScript |
| **Biométrie** | Connexion sans mot de passe, 4 métriques de comparaison | OpenCV, JavaScript |
| **Analyse sentiment** | Articles presse, scores agrégés, évolution temporelle | pandas, GitHub CSV |
| **Graphiques marché** | Chandeliers japonais, 2 ans d'historique, 8 actifs | Lightweight-charts |
| **Profil** | KPIs trading, visibilité publique, gestion faciale | Dash, SQLite |
| **Témoignages** | Soumission, workflow modération, stats plateforme | Flask, SQLite |
| **Admin** | CRUD utilisateurs, stats, logs connexion, modération | Flask, Plotly |
| **Authentification** | Email/bcrypt + reconnaissance faciale | bcrypt, OpenCV |
| **Déploiement** | Docker Python 3.11, port configurable | Docker |

---

*Projet réalisé dans le cadre de la 4ème année à l'ENSIM — École Nationale Supérieure d'Ingénieurs du Mans*
*Technologies principales : Python 3.11 · Dash/Flask · TensorFlow · PyTorch · Groq LLaMA 3.3 · OpenCV · SQLite*
