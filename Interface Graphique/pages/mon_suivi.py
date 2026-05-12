import dash
from dash import html, dcc, Input, Output, State, callback, ALL, ctx, no_update
import plotly.graph_objects as go
import yfinance as yf
import pandas as pd
import requests
import os
import struct
import zlib
from io import StringIO
from datetime import datetime, timedelta

from services.tracking_service import get_user_trades, get_user_stats, save_followed_trade
from services.auth_service import get_user_by_email

dash.register_page(__name__, path="/mon-suivi", name="Mon Suivi")

GITHUB_BASE = "https://raw.githubusercontent.com/adam-hassen/stock-auto-update/main/data/articles_sentiment"
MASTER_URL = f"{GITHUB_BASE}/ALL_ARTICLES_MASTER.csv"

COMPANIES = {
    'AAPL': 'Apple Inc.',
    'MSFT': 'Microsoft',
    'TSLA': 'Tesla',
    'NVDA': 'NVIDIA',
    'GOOGL': 'Alphabet',
    'AMZN': 'Amazon',
    'META': 'Meta',
}

GITHUB_DATA_BASE = "https://raw.githubusercontent.com/adam-hassen/stock-auto-update/main/data"


def _load_price_history(ticker, days=90):
    # Essaye d'abord le GitHub du projet (workflow quotidien)
    try:
        url = f"{GITHUB_DATA_BASE}/{ticker}.csv"
        resp = requests.get(url, timeout=8)
        if resp.status_code == 200:
            df = pd.read_csv(StringIO(resp.text))
            if 'date' in df.columns and 'Close' in df.columns:
                df['date'] = pd.to_datetime(df['date'], errors='coerce')
                df = df.dropna(subset=['date', 'Close'])
                cutoff = datetime.now() - timedelta(days=days)
                df = df[df['date'] >= cutoff].sort_values('date')
                if not df.empty:
                    print(f"[SUIVI] Prix {ticker} chargés depuis GitHub ({len(df)} jours)")
                    return df[['date', 'Close']]
    except Exception as e:
        print(f"[SUIVI] GitHub indisponible pour {ticker}: {e}")

    # Fallback : yfinance
    try:
        hist = yf.Ticker(ticker).history(period=f"{days}d", interval="1d")
        if not hist.empty:
            df = hist[['Close']].copy().reset_index()
            df.columns = ['date', 'Close']
            df['date'] = pd.to_datetime(df['date']).dt.normalize().dt.tz_localize(None)
            df = df.dropna().sort_values('date')
            print(f"[SUIVI] Prix {ticker} chargés depuis yfinance ({len(df)} jours)")
            return df
    except Exception as e:
        print(f"[SUIVI] yfinance indisponible pour {ticker}: {e}")

    return pd.DataFrame()


def _run_backtest(ticker, start_amount=500.0, days=180):
    """
    Simule un portefeuille de start_amount € qui suit les signaux IA sur les
    `days` derniers jours.
    Retourne les séries temporelles + métriques.
    """
    prices_df = _load_price_history(ticker, days=days + 10)
    if prices_df.empty or len(prices_df) < 5:
        return None

    articles_df = _load_articles_for_backtest()
    prices_df = prices_df.sort_values('date').reset_index(drop=True)

    portfolio = start_amount
    buy_hold_ref = float(prices_df.iloc[0]['Close'])

    dates_out, port_vals, bh_vals, trade_log = [], [], [], []
    wins = losses = 0
    step = 3

    for i in range(0, len(prices_df) - step, step):
        row_s = prices_df.iloc[i]
        row_e = prices_df.iloc[i + step]
        date_s = pd.Timestamp(row_s['date'])
        p_start = float(row_s['Close'])
        p_end = float(row_e['Close'])

        signal, pnl_pct = 'SURVEILLER', 0.0

        if not articles_df.empty:
            col = next((c for c in ['symbol', 'ticker'] if c in articles_df.columns), None)
            if col:
                arts = articles_df[
                    (articles_df[col] == ticker) &
                    (articles_df['date_publication'] >= date_s - timedelta(days=2)) &
                    (articles_df['date_publication'] <= date_s + timedelta(hours=24))
                ]
                if not arts.empty:
                    sc = float(arts['score_sentiment'].mean())
                    if sc > 0.15:
                        signal = 'ACHETER'
                        pnl_pct = (p_end - p_start) / p_start
                    elif sc < -0.15:
                        signal = 'VENDRE'
                        pnl_pct = (p_start - p_end) / p_start

        portfolio *= (1 + pnl_pct)
        bh = start_amount * (p_end / buy_hold_ref)

        dates_out.append(date_s)
        port_vals.append(round(portfolio, 2))
        bh_vals.append(round(bh, 2))

        if signal != 'SURVEILLER':
            (wins if pnl_pct > 0 else losses).__class__  # type hint trick
            if pnl_pct > 0:
                wins += 1
            else:
                losses += 1
            trade_log.append({
                'date': date_s.strftime('%d %b %Y'),
                'signal': signal,
                'return_pct': round(pnl_pct * 100, 2),
                'pnl_eur': round(portfolio * pnl_pct / (1 + pnl_pct) if abs(1 + pnl_pct) > 0.001 else 0, 2),
            })

    # Ajoute le dernier point
    if len(prices_df) > 0:
        last = prices_df.iloc[-1]
        dates_out.append(pd.Timestamp(last['date']))
        port_vals.append(round(portfolio, 2))
        bh_vals.append(round(start_amount * float(last['Close']) / buy_hold_ref, 2))

    n = wins + losses
    return {
        'dates': dates_out,
        'portfolio': port_vals,
        'buy_hold': bh_vals,
        'final_value': round(portfolio, 2),
        'total_return': round((portfolio - start_amount) / start_amount * 100, 2),
        'buy_hold_return': round((bh_vals[-1] - start_amount) / start_amount * 100, 2) if bh_vals else 0,
        'start_amount': start_amount,
        'n_trades': n,
        'wins': wins,
        'losses': losses,
        'win_rate': round(wins / n * 100) if n > 0 else 0,
        'trades': trade_log[-15:],
        # Date du premier signal réel (pas du début de la fenêtre de prix)
        'start_date': trade_log[0]['date'] if trade_log else (dates_out[0].strftime('%d %b %Y') if dates_out else '—'),
        'data_start': dates_out[0].strftime('%d %b %Y') if dates_out else '—',
        # Timestamp du premier signal pour aligner le graphique
        'first_signal_ts': trade_log[0]['date'] if trade_log else None,
    }


def _load_articles_for_backtest():
    """Charge tous les articles sans filtre de date (pour backtesting)."""
    try:
        resp = requests.get(MASTER_URL, timeout=12)
        if resp.status_code == 200:
            df = pd.read_csv(StringIO(resp.text))
            df['date_publication'] = pd.to_datetime(df['date_publication'], errors='coerce', utc=True).dt.tz_localize(None)
            return df.dropna(subset=['date_publication', 'score_sentiment'])
    except Exception as e:
        print(f"[BACKTEST] Articles: {e}")
    return pd.DataFrame()


def _load_articles():
    try:
        resp = requests.get(MASTER_URL, timeout=15)
        if resp.status_code == 200:
            df = pd.read_csv(StringIO(resp.text))
            df['date_publication'] = pd.to_datetime(df['date_publication'], errors='coerce')
            return df.dropna(subset=['date_publication', 'score_sentiment'])
    except Exception as e:
        print(f"[SUIVI] Erreur chargement articles: {e}")
    return pd.DataFrame()


_SIGNAL_EMPTY = {
    'signal': 'NEUTRE', 'score': 0.0, 'confidence': 0.0, 'articles': 0,
    'signal_valid_to': '—', 'horizon_label': '~48h',
}


def _compute_signal(df, ticker):
    if df.empty:
        return {**_SIGNAL_EMPTY}

    ticker_col = next((c for c in ['ticker', 'Ticker', 'TICKER', 'symbol'] if c in df.columns), None)
    if ticker_col is None:
        return {**_SIGNAL_EMPTY}

    df_co = df[df[ticker_col] == ticker].copy()
    if df_co.empty:
        return {**_SIGNAL_EMPTY}

    try:
        df_co['date_publication'] = (
            pd.to_datetime(df_co['date_publication'], errors='coerce', utc=True)
            .dt.tz_localize(None)
        )
        df_co = df_co.dropna(subset=['date_publication'])
        cutoff = datetime.now() - timedelta(days=2)
        recent = df_co[df_co['date_publication'] >= cutoff]
        df_co = recent if not recent.empty else df_co.tail(15)
    except Exception:
        df_co = df_co.tail(15)

    if 'score_pondere' in df_co.columns:
        score = float(df_co['score_pondere'].mean())
    elif 'confiance' in df_co.columns:
        score = float((df_co['score_sentiment'] * df_co['confiance']).mean())
    else:
        score = float(df_co['score_sentiment'].mean())

    confidence = round(min(abs(score) * min(len(df_co) / 10, 1.0) * 100, 95), 1)

    if score > 0.15:
        signal = 'HAUSSIER'
    elif score < -0.15:
        signal = 'BAISSIER'
    else:
        signal = 'NEUTRE'

    latest_dt = None
    try:
        latest_dt = df_co['date_publication'].max()
        oldest_dt = df_co['date_publication'].min()
        expires_dt = latest_dt + timedelta(hours=48)
        window_h = max(1, round((latest_dt - oldest_dt).total_seconds() / 3600))
        signal_valid_to = expires_dt.strftime('%d %b %Y à %Hh')
        horizon_label = f"~{window_h}h de données · valide ~48h"
    except Exception:
        signal_valid_to = (datetime.now() + timedelta(days=2)).strftime('%d %b %Y')
        horizon_label = '~48h'

    return {
        'signal': signal, 'score': round(score, 3),
        'confidence': confidence, 'articles': len(df_co),
        'signal_valid_to': signal_valid_to, 'horizon_label': horizon_label,
        'latest_dt': latest_dt.isoformat() if latest_dt is not None else None,
    }


def _get_prices(ticker, signal_date=None):
    try:
        hist = yf.Ticker(ticker).history(period="60d", interval="1d")
        if not hist.empty:
            try:
                hist.index = pd.to_datetime(hist.index).tz_localize(None)
            except Exception:
                hist.index = pd.to_datetime(hist.index).tz_convert(None)

            current = round(float(hist['Close'].iloc[-1]), 2)
            current_date = hist.index[-1].strftime('%d %b').lstrip('0')

            if signal_date:
                target = pd.Timestamp(signal_date).tz_localize(None) if pd.Timestamp(signal_date).tzinfo else pd.Timestamp(signal_date)
                diffs = abs(hist.index - target)
                closest_idx = int(diffs.argmin())
                entry = round(float(hist['Close'].iloc[closest_idx]), 2)
                entry_date = hist.index[closest_idx].strftime('%d %b').lstrip('0')
            else:
                idx = -3 if len(hist) >= 3 else -2
                entry = round(float(hist['Close'].iloc[idx]), 2)
                entry_date = hist.index[idx].strftime('%d %b').lstrip('0')

            return {
                'entry_price': entry,
                'current_price': current,
                'change_pct': round((current - entry) / entry * 100, 2),
                'entry_date': entry_date,
                'current_date': current_date,
            }
    except Exception as e:
        print(f"[SUIVI] Prix {ticker}: {e}")
    return {'entry_price': 0.0, 'current_price': 0.0, 'change_pct': 0.0, 'entry_date': '', 'current_date': ''}


def _simulate(signal, entry, current, amount):
    if entry == 0 or amount <= 0:
        return 0.0, 0.0
    if signal == 'HAUSSIER':
        pnl = (current - entry) / entry * amount
    elif signal == 'BAISSIER':
        pnl = (entry - current) / entry * amount
    else:
        pnl = 0.0
    return round(pnl, 2), round((pnl / amount * 100) if amount else 0, 2)


def _parse_amount(value):
    if value is None:
        return None
    cleaned = str(value).replace(" ", "").replace(",", ".").strip()
    try:
        amount = float(cleaned)
    except ValueError:
        return None
    return amount if amount > 0 else None


def _money(value, suffix="EUR"):
    return f"{float(value or 0):+,.2f} {suffix}"


def _pct(value):
    return f"{float(value or 0):+,.2f}%"


def _pdf_color(hex_color):
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i:i + 2], 16) / 255 for i in (0, 2, 4))


def _pdf_escape(text):
    return str(text).replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _pdf_text_width(text, size):
    return len(str(text)) * size * 0.52


def _pdf_wrap(text, max_width, size):
    words = str(text).split()
    lines = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if current and _pdf_text_width(candidate, size) > max_width:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines or [""]


def _png_to_pdf_rgb(path):
    try:
        with open(path, "rb") as file:
            data = file.read()
        if data[:8] != b"\x89PNG\r\n\x1a\n":
            return None

        pos = 8
        width = height = bit_depth = color_type = None
        idat = bytearray()
        while pos < len(data):
            length = struct.unpack(">I", data[pos:pos + 4])[0]
            chunk_type = data[pos + 4:pos + 8]
            chunk_data = data[pos + 8:pos + 8 + length]
            pos += 12 + length

            if chunk_type == b"IHDR":
                width, height, bit_depth, color_type, _, _, _ = struct.unpack(">IIBBBBB", chunk_data)
            elif chunk_type == b"IDAT":
                idat.extend(chunk_data)
            elif chunk_type == b"IEND":
                break

        if bit_depth != 8 or color_type not in (2, 6):
            return None

        channels = 4 if color_type == 6 else 3
        stride = width * channels
        raw = zlib.decompress(bytes(idat))
        rows = []
        cursor = 0
        previous = [0] * stride

        for _ in range(height):
            filter_type = raw[cursor]
            cursor += 1
            row = list(raw[cursor:cursor + stride])
            cursor += stride

            for i, value in enumerate(row):
                left = row[i - channels] if i >= channels else 0
                up = previous[i]
                upper_left = previous[i - channels] if i >= channels else 0

                if filter_type == 1:
                    row[i] = (value + left) & 0xFF
                elif filter_type == 2:
                    row[i] = (value + up) & 0xFF
                elif filter_type == 3:
                    row[i] = (value + ((left + up) // 2)) & 0xFF
                elif filter_type == 4:
                    p = left + up - upper_left
                    pa = abs(p - left)
                    pb = abs(p - up)
                    pc = abs(p - upper_left)
                    predictor = left if pa <= pb and pa <= pc else up if pb <= pc else upper_left
                    row[i] = (value + predictor) & 0xFF

            rows.append(row)
            previous = row

        bg = (255, 255, 255)
        rgb = bytearray()
        for row in rows:
            for i in range(0, len(row), channels):
                if channels == 4:
                    alpha = row[i + 3]
                    rgb.extend(
                        ((row[i + c] * alpha + bg[c] * (255 - alpha)) // 255)
                        for c in range(3)
                    )
                else:
                    rgb.extend(row[i:i + 3])

        return width, height, zlib.compress(bytes(rgb))
    except Exception as e:
        print(f"[SUIVI] Logo PDF indisponible: {e}")
        return None


class _SimplePdf:
    def __init__(self):
        self.width = 595
        self.height = 842
        self.pages = []
        self.commands = []
        self.images = []
        self.image_cache = {}
        self.new_page()

    def new_page(self):
        if self.commands:
            self.pages.append("\n".join(self.commands))
        self.commands = []
        self.rect(0, 0, self.width, self.height, fill="#ffffff")

    def finish(self):
        if self.commands:
            self.pages.append("\n".join(self.commands))
            self.commands = []

        image_count = len(self.images)
        page_start = 4 + image_count
        kids = " ".join(f"{page_start + i * 2} 0 R" for i in range(len(self.pages)))
        xobjects = " ".join(
            f"/{image['name']} {4 + index} 0 R"
            for index, image in enumerate(self.images)
        )
        xobject_resource = f"/XObject << {xobjects} >>" if xobjects else ""

        objects = [
            "<< /Type /Catalog /Pages 2 0 R >>",
            f"<< /Type /Pages /Kids [{kids}] /Count {len(self.pages)} >>",
            "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        ]

        for image in self.images:
            objects.append(
                f"<< /Type /XObject /Subtype /Image /Width {image['width']} /Height {image['height']} "
                f"/ColorSpace /DeviceRGB /BitsPerComponent 8 /Filter /FlateDecode /Length {len(image['data'])} >>\n"
                f"stream\n{image['data'].decode('latin-1')}\nendstream"
            )

        for index, content in enumerate(self.pages):
            page_obj = page_start + index * 2
            stream_obj = page_obj + 1
            objects.append(
                f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {self.width} {self.height}] "
                f"/Resources << /Font << /F1 3 0 R >> {xobject_resource} >> /Contents {stream_obj} 0 R >>"
            )
            data = content.encode("latin-1", "replace")
            objects.append(f"<< /Length {len(data)} >>\nstream\n{content}\nendstream")

        pdf = bytearray(b"%PDF-1.4\n")
        offsets = [0]
        for obj_num, obj in enumerate(objects, start=1):
            offsets.append(len(pdf))
            pdf.extend(f"{obj_num} 0 obj\n".encode("latin-1"))
            pdf.extend(obj.encode("latin-1", "replace"))
            pdf.extend(b"\nendobj\n")

        xref = len(pdf)
        pdf.extend(f"xref\n0 {len(objects) + 1}\n".encode("latin-1"))
        pdf.extend(b"0000000000 65535 f \n")
        for offset in offsets[1:]:
            pdf.extend(f"{offset:010d} 00000 n \n".encode("latin-1"))
        pdf.extend(
            f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
            f"startxref\n{xref}\n%%EOF\n".encode("latin-1")
        )
        return bytes(pdf)

    def _rgb(self, hex_color, operator):
        r, g, b = _pdf_color(hex_color)
        self.commands.append(f"{r:.3f} {g:.3f} {b:.3f} {operator}")

    def rect(self, x, y, w, h, fill=None, stroke=None, line_width=1):
        if fill:
            self._rgb(fill, "rg")
            self.commands.append(f"{x:.2f} {y:.2f} {w:.2f} {h:.2f} re f")
        if stroke:
            self._rgb(stroke, "RG")
            self.commands.append(f"{line_width:.2f} w {x:.2f} {y:.2f} {w:.2f} {h:.2f} re S")

    def line(self, x1, y1, x2, y2, color="#00f0ff", line_width=1):
        self._rgb(color, "RG")
        self.commands.append(f"{line_width:.2f} w {x1:.2f} {y1:.2f} m {x2:.2f} {y2:.2f} l S")

    def text(self, x, y, text, size=10, color="#e0e8ff"):
        self._rgb(color, "rg")
        self.commands.append(f"BT /F1 {size:.1f} Tf {x:.2f} {y:.2f} Td ({_pdf_escape(text)}) Tj ET")

    def image(self, path, x, y, w, h):
        if path in self.image_cache:
            name = self.image_cache[path]
        else:
            parsed = _png_to_pdf_rgb(path)
            if not parsed:
                return

            width, height, data = parsed
            name = f"Im{len(self.images) + 1}"
            self.images.append({"name": name, "width": width, "height": height, "data": data})
            self.image_cache[path] = name
        self.commands.append(f"q {w:.2f} 0 0 {h:.2f} {x:.2f} {y:.2f} cm /{name} Do Q")


def _build_tracking_report_pdf(email):
    stats = get_user_stats(email)
    trades = get_user_trades(email, 1000)
    user = get_user_by_email(email) or {}
    generated_at = datetime.now().strftime("%d/%m/%Y %H:%M")
    pdf = _SimplePdf()
    logo_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "assets", "logo.png"))
    full_name = " ".join(filter(None, [user.get("prenom", ""), user.get("nom", "")])).strip()
    display_name = full_name or email.split("@")[0].capitalize()
    total_pnl = float(stats.get("total_pnl", 0) or 0)
    total_trades = int(stats.get("total_trades", 0) or 0)
    wins = int(stats.get("wins", 0) or 0)
    losses = int(stats.get("losses", 0) or 0)
    win_rate = float(stats.get("win_rate", 0) or 0)
    avg_return = float(stats.get("avg_pnl", 0) or 0)
    open_trades = int(stats.get("open_trades", 0) or 0)
    positive_color = "#00ff87" if total_pnl >= 0 else "#ff4d6d"
    sig_display = {'up': 'HAUSSIER', 'down': 'BAISSIER', 'neutral': 'NEUTRE'}

    signal_counts = {"HAUSSIER": 0, "BAISSIER": 0, "NEUTRE": 0}
    best_trade = None
    worst_trade = None
    total_invested = 0.0
    for trade in trades:
        pred_dir = sig_display.get(trade[8] or "neutral", "NEUTRE")
        signal_counts[pred_dir] = signal_counts.get(pred_dir, 0) + 1
        total_invested += float(trade[7] or 0)
        pnl = float(trade[10] or 0)
        if best_trade is None or pnl > float(best_trade[10] or 0):
            best_trade = trade
        if worst_trade is None or pnl < float(worst_trade[10] or 0):
            worst_trade = trade

    def footer(page_num):
        pdf.line(40, 54, 555, 54, color="#d9e2ec", line_width=0.8)
        pdf.text(40, 36, "ENSIM - Rapport personnel de suivi", size=7.5, color="#667085")
        pdf.text(486, 36, f"Page {page_num}", size=7.5, color="#667085")

    def header(page_title, page_num):
        pdf.image(logo_path, 44, 772, 84, 28)
        pdf.text(150, 789, page_title, size=12, color="#15264a")
        pdf.text(150, 771, "Rapport personnel de performance", size=8.5, color="#667085")
        pdf.text(420, 789, generated_at, size=8, color="#667085")
        pdf.text(420, 771, display_name, size=8.5, color="#15264a")
        pdf.line(40, 754, 555, 754, color="#d9e2ec", line_width=0.9)

    def section_title(y, number, title, subtitle=None):
        pdf.text(54, y, number, size=18, color="#0097b2")
        pdf.text(92, y + 2, title, size=13.5, color="#15264a")
        pdf.line(92, y - 6, 541, y - 6, color="#d9e2ec", line_width=0.9)
        if subtitle:
            pdf.text(92, y - 22, subtitle, size=8.5, color="#667085")

    def metric_card(x, y, w, label, value, color="#e0e8ff", note=None):
        pdf.rect(x, y, w, 72, fill="#f7fafc", stroke="#d9e2ec")
        pdf.rect(x, y + 68, w, 4, fill=color)
        pdf.text(x + 14, y + 49, label.upper(), size=7.5, color="#667085")
        pdf.text(x + 14, y + 25, value, size=15, color=color)
        if note:
            pdf.text(x + 14, y + 10, note, size=7.5, color="#667085")

    def insight_box(x, y, w, title, body, color="#00f0ff"):
        pdf.rect(x, y, w, 78, fill="#f7fafc", stroke="#d9e2ec")
        pdf.rect(x, y, 5, 78, fill=color)
        pdf.text(x + 18, y + 55, title, size=10.5, color="#15264a")
        text_y = y + 38
        for line in _pdf_wrap(body, w - 34, 8.2)[:3]:
            pdf.text(x + 18, text_y, line, size=8.2, color="#344054")
            text_y -= 12

    def trade_label(trade):
        if not trade:
            return "-"
        return f"{trade[2] or '-'} / {_money(trade[10] or 0)}"

    # Page 1: cover
    pdf.rect(0, 0, 595, 842, fill="#ffffff")
    pdf.image(logo_path, 54, 760, 116, 38)
    pdf.text(54, 706, "Rapport professionnel de suivi", size=23, color="#15264a")
    pdf.text(54, 682, "Performance, historique et synthese de vos trades suivis", size=10, color="#667085")
    pdf.line(54, 662, 541, 662, color="#0097b2", line_width=1.2)

    pdf.rect(54, 584, 487, 62, fill="#f7fafc", stroke="#d9e2ec")
    pdf.text(74, 622, "UTILISATEUR", size=8, color="#667085")
    pdf.text(74, 602, display_name, size=13, color="#15264a")
    pdf.text(332, 622, "DATE D'EDITION", size=8, color="#667085")
    pdf.text(332, 602, generated_at, size=10, color="#15264a")

    metric_card(54, 478, 232, "Performance nette", _money(total_pnl), positive_color, "P&L cumule")
    metric_card(309, 478, 232, "Taux de reussite", f"{win_rate:.1f}%", "#0097b2", f"{wins} gagnants / {losses} perdants")
    metric_card(54, 378, 150, "Trades", str(total_trades), "#15264a")
    metric_card(222, 378, 150, "Capital simule", f"{total_invested:,.0f} EUR", "#15264a")
    metric_card(390, 378, 151, "Positions", str(open_trades), "#15264a")

    summary = (
        "Votre portefeuille suivi affiche une performance positive sur la periode analysee."
        if total_pnl >= 0 else
        "Votre portefeuille suivi affiche une performance negative sur la periode analysee."
    )
    insight_box(54, 250, 487, "Resume executif", f"{summary} Le rapport consolide vos trades enregistres, leur rendement et les signaux IA associes.", positive_color)
    pdf.text(54, 104, "Confidentialite", size=10, color="#15264a")
    pdf.text(54, 86, "Document personnel genere depuis votre espace Mon Suivi. Aucune garantie de performance future.", size=8, color="#667085")
    footer(1)

    # Page 2: analysis
    pdf.new_page()
    header("Synthese analytique", 2)
    section_title(700, "01", "Tableau de bord", "Indicateurs consolides a partir de votre historique de suivi.")
    metric_card(54, 596, 150, "P&L total", _money(total_pnl), positive_color)
    metric_card(222, 596, 150, "Rend. moyen", _pct(avg_return), "#0097b2")
    metric_card(390, 596, 151, "Win rate", f"{win_rate:.1f}%", "#0097b2")
    metric_card(54, 496, 150, "Gagnants", str(wins), "#00ff87")
    metric_card(222, 496, 150, "Perdants", str(losses), "#ff4d6d")
    metric_card(390, 496, 151, "Neutres", str(max(total_trades - wins - losses, 0)), "#e0e8ff")

    section_title(420, "02", "Lecture rapide", "Points cles utiles pour interpreter le suivi.")
    insight_box(54, 314, 232, "Meilleur trade", trade_label(best_trade), "#00ff87")
    insight_box(309, 314, 232, "Trade le plus faible", trade_label(worst_trade), "#ff4d6d" if worst_trade else "#7a8aaa")
    dominant_signal = max(signal_counts, key=signal_counts.get) if trades else "NEUTRE"
    insight_box(
        54,
        212,
        487,
        "Repartition des signaux",
        f"HAUSSIER: {signal_counts.get('HAUSSIER', 0)} | BAISSIER: {signal_counts.get('BAISSIER', 0)} | NEUTRE: {signal_counts.get('NEUTRE', 0)}. Signal dominant: {dominant_signal}.",
        "#0097b2",
    )
    insight_box(
        54,
        110,
        487,
        "Commentaire",
        "Ce rapport mesure les simulations ou suivis confirmes dans l'application. Il sert de support de pilotage et non de conseil financier.",
        "#15264a",
    )
    footer(2)

    # Page 3+: history
    pdf.new_page()
    header("Historique detaille", 3)
    section_title(700, "03", "Trades enregistres", "Detail des positions suivies et performances realisees.")

    def table_header(y):
        pdf.rect(40, y, 515, 24, fill="#eef6fb", stroke="#d9e2ec")
        cols = [("Actif", 50), ("Signal", 112), ("Investi", 184), ("Entree", 260), ("Sortie", 324), ("P&L", 386), ("Rend.", 462), ("Date", 512)]
        for label, x in cols:
            pdf.text(x, y + 8, label, size=8.5, color="#15264a")

    table_header(650)
    y = 624
    page_num = 3
    if not trades:
        pdf.text(50, y, "Aucun trade suivi pour le moment.", size=10, color="#7a8aaa")
    else:
        for trade in trades:
            if y < 72:
                footer(page_num)
                pdf.new_page()
                page_num += 1
                header("Historique detaille", page_num)
                table_header(690)
                y = 664

            symbol = trade[2] or "-"
            amount = float(trade[7] or 0)
            pred_dir = sig_display.get(trade[8] or "neutral", str(trade[8] or "NEUTRE").upper())
            entry = float(trade[3] or 0)
            exit_price = trade[4]
            pnl = float(trade[10] or 0)
            pnl_pct = float(trade[11] or 0)
            entry_date = str(trade[5])[:10] if trade[5] else "-"
            pnl_color = "#00ff87" if pnl >= 0 else "#ff4d6d"

            pdf.rect(40, y - 4, 515, 22, fill="#ffffff", stroke="#e6edf3")
            pdf.text(50, y + 3, symbol, size=8.5, color="#15264a")
            pdf.text(112, y + 3, pred_dir, size=7.8, color="#344054")
            pdf.text(184, y + 3, f"{amount:,.0f}", size=7.8, color="#344054")
            pdf.text(260, y + 3, f"${entry:,.2f}", size=7.8, color="#344054")
            pdf.text(324, y + 3, f"${float(exit_price):,.2f}" if exit_price else "-", size=7.8, color="#344054")
            pdf.text(386, y + 3, _money(pnl), size=7.8, color=pnl_color)
            pdf.text(462, y + 3, _pct(pnl_pct), size=7.8, color=pnl_color)
            pdf.text(512, y + 3, entry_date, size=7.5, color="#667085")
            y -= 24

    footer(page_num)
    return pdf.finish()


# ==================== LAYOUT ====================

layout = html.Div(className="suivi-page", children=[
    dcc.Store(id="suivi-pred-store"),
    dcc.Store(id="suivi-modal-ticker"),
    dcc.Store(id="suivi-modal-action", data="ACHAT"),
    dcc.Store(id="suivi-refresh", data=0),
    dcc.Store(id="suivi-backtest-ticker-store", data="AAPL"),
    dcc.Download(id="suivi-report-download"),
    dcc.Interval(id="suivi-init", interval=300, n_intervals=0, max_intervals=1),
    dcc.Interval(id="suivi-auto", interval=5 * 60 * 1000, n_intervals=0),

    # ===== HERO =====
    html.Div(className="suivi-hero", children=[
        html.Div(className="suivi-hero-badge", children=[
            html.Span(className="suivi-pulse-dot"),
            html.Span("MON SUIVI PERSONNALISE"),
        ]),
        html.H1("Mon Espace Investissement", className="suivi-title"),
        html.Div(className="suivi-neon-line"),
        html.P(
            "Notre IA vous dit quoi faire — vous choisissez, on calcule combien vous auriez gagné ou perdu",
            className="suivi-hero-sub"
        ),
        html.Div(id="suivi-welcome"),
    ]),

    html.Div(className="suivi-main", children=[

        # ===== KPIs =====
        html.Div(id="suivi-kpis", className="suivi-kpi-row"),

        # ===== PREDICTIONS =====
        html.Div(className="suivi-section", children=[
            html.Div(className="suivi-section-hdr", children=[
                html.Span("01", className="suivi-num"),
                html.Div([
                    html.H2("Que faire aujourd'hui ?", className="suivi-section-title"),
                    html.P("Cliquez sur une action pour calculer combien vous pourriez gagner", className="suivi-section-sub"),
                ]),
            ]),
            html.Div(id="suivi-pred-grid", className="suivi-pred-grid",
                     children=html.Div("Chargement des predictions...", className="suivi-loading")),
        ]),

        # ===== HISTORIQUE =====
        html.Div(className="suivi-section", children=[
            html.Div(className="suivi-section-hdr", children=[
                html.Span("02", className="suivi-num"),
                html.Div([
                    html.H2("Mes investissements passés", className="suivi-section-title"),
                    html.P("Ce que vous avez investi et ce que ça a rapporté", className="suivi-section-sub"),
                ]),
                html.Button(
                    [html.I(className="fas fa-file-pdf"), "  Télécharger mon rapport"],
                    id="suivi-export-report-btn",
                    className="suivi-export-btn",
                    n_clicks=0,
                ),
            ]),
            html.Div(id="suivi-history", className="suivi-history"),
        ]),

        # ===== COURBE PREDICTIONS VS REEL =====
        html.Div(className="suivi-section", children=[
            html.Div(className="suivi-section-hdr", children=[
                html.Span("03", className="suivi-num"),
                html.Div([
                    html.H2("Historique du prix et de vos investissements", className="suivi-section-title"),
                    html.P("La ligne montre l'évolution du prix. Les triangles ▲▼ indiquent quand vous avez investi — vert = vous avez gagné, rouge = vous avez perdu.", className="suivi-section-sub"),
                ]),
                html.Div(
                    dcc.Dropdown(
                        id="suivi-ticker-select",
                        options=[],
                        value=None,
                        clearable=False,
                        placeholder="Choisir une action...",
                        className="suivi-ticker-dd",
                    ),
                    style={
                        "minWidth": "240px",
                        "background": "rgba(5,15,40,0.92)",
                        "borderRadius": "10px",
                        "border": "1px solid rgba(0,240,255,0.3)",
                    },
                ),
            ]),
            dcc.Graph(
                id="suivi-perf-chart",
                config={"displayModeBar": False},
                style={"marginTop": "16px"},
            ),
        ]),
    ]),

    # ===== MODAL =====
    html.Div(id="suivi-modal-bg", className="suivi-modal-hidden", children=[
        html.Div(className="suivi-modal", children=[
            html.Div(className="suivi-modal-hdr", children=[
                html.Div(id="suivi-modal-heading"),
                html.Button(
                    html.I(className="fas fa-xmark"),
                    id="suivi-close-btn",
                    className="suivi-close-btn",
                    n_clicks=0,
                ),
            ]),
            html.Div(className="suivi-modal-body", children=[
                html.Div(id="suivi-modal-info"),

                # ── Sélecteur d'opération ──
                html.Div(className="suivi-action-section", children=[
                    html.Span("Ce que je veux faire", className="suivi-label"),
                    html.Div(className="suivi-action-btns", children=[
                        html.Button(
                            [html.I(className="fas fa-arrow-trend-up"), "  ACHAT"],
                            id="suivi-action-buy",
                            className="suivi-action-btn suivi-action-buy active",
                            n_clicks=0,
                        ),
                        html.Button(
                            [html.I(className="fas fa-arrow-trend-down"), "  VENTE"],
                            id="suivi-action-sell",
                            className="suivi-action-btn suivi-action-sell",
                            n_clicks=0,
                        ),
                    ]),
                    html.Div(id="suivi-action-hint", className="suivi-action-hint"),
                ]),

                html.Div(className="suivi-amount-row", children=[
                    html.Label("Combien je veux investir (€)", className="suivi-label"),
                    html.Div(className="suivi-input-grp", children=[
                        html.Span("€", className="suivi-input-euro"),
                        dcc.Input(
                            id="suivi-amount",
                            type="text",
                            inputMode="numeric",
                            debounce=True,
                            placeholder="ex: 1 000",
                            className="suivi-input",
                        ),
                    ]),
                ]),
                html.Div(id="suivi-sim-result"),
                html.Div(className="suivi-modal-btns", children=[
                    html.Button(
                        [html.I(className="fas fa-check"), " J'ai fait cet investissement"],
                        id="suivi-btn-followed",
                        className="suivi-btn-green",
                        n_clicks=0,
                    ),
                    html.Button(
                        [html.I(className="fas fa-eye"), " Juste voir le résultat"],
                        id="suivi-btn-sim",
                        className="suivi-btn-ghost",
                        n_clicks=0,
                    ),
                ]),
                html.Div(id="suivi-feedback"),
            ]),
        ]),
    ]),

    # ===== MODAL BACKTEST =====
    html.Div(id="suivi-backtest-bg", className="suivi-modal-hidden", children=[
        html.Div(className="suivi-backtest-modal", children=[
            # Header
            html.Div(className="suivi-backtest-hdr", children=[
                html.Div([
                    html.Div(className="suivi-backtest-live", children=[
                        html.Span(className="suivi-pulse-dot"),
                        "ET SI J'AVAIS SUIVI LES CONSEILS ?",
                    ]),
                    html.H2(id="suivi-backtest-title", className="suivi-backtest-title",
                            children="Simulation sur l'historique"),
                    html.P(
                        id="suivi-backtest-sub",
                        className="suivi-backtest-sub",
                        children="Voici ce que vous auriez gagné ou perdu en suivant nos conseils IA depuis le début",
                    ),
                ]),
                html.Button(
                    html.I(className="fas fa-xmark"),
                    id="suivi-backtest-close",
                    className="suivi-close-btn",
                    n_clicks=0,
                ),
            ]),
            # Montant simulé (contrôlé par l'utilisateur)
            html.Div(className="suivi-backtest-controls", children=[
                html.Label("Si j'avais investi (€)", className="suivi-label"),
                html.Div(className="suivi-input-grp", children=[
                    html.Span("€", className="suivi-input-euro"),
                    dcc.Input(
                        id="suivi-backtest-amount-input",
                        type="number",
                        placeholder="ex: 500",
                        min=1,
                        value=500,
                        className="suivi-input",
                        style={"maxWidth": "180px"},
                    ),
                ]),
                html.Button(
                    [html.I(className="fas fa-calculator"), "  Recalculer"],
                    id="suivi-backtest-recalc-btn",
                    className="suivi-bt-recalc-btn",
                    n_clicks=0,
                ),
            ]),
            # Résumé en langage simple
            html.Div(id="suivi-backtest-summary"),
            # Stats résumé
            html.Div(id="suivi-backtest-stats", className="suivi-backtest-stats"),
            # Graphique
            dcc.Graph(id="suivi-backtest-chart", config={"displayModeBar": False}),
            # Derniers trades simulés
            html.Div(id="suivi-backtest-trades"),
        ]),
    ]),
])


# ==================== CALLBACKS ====================

@callback(
    Output("suivi-pred-store", "data"),
    Input("suivi-init", "n_intervals"),
    Input("suivi-auto", "n_intervals"),
)
def load_pred_data(_init, _auto):
    df = _load_articles()
    result = {}
    for ticker, name in COMPANIES.items():
        sig = _compute_signal(df, ticker)
        prices = _get_prices(ticker, signal_date=sig.get('latest_dt'))
        result[ticker] = {**sig, **prices, 'name': name}
    return result


@callback(
    Output("suivi-welcome", "children"),
    Output("suivi-pred-grid", "children"),
    Input("suivi-pred-store", "data"),
    State("session-store", "data"),
)
def render_predictions(pred_data, session):
    if not pred_data:
        return "", html.Div("Chargement...", className="suivi-loading")

    prenom = ""
    if session:
        prenom = session.get("prenom") or session.get("email", "").split("@")[0].capitalize()
    welcome = html.Span(f"Bonjour {prenom} — voici les predictions du jour", className="suivi-welcome-text") if prenom else ""

    # HAUSSIER/BAISSIER/NEUTRE → recommandation lisible pour l'utilisateur
    _rec_label = {'HAUSSIER': 'ACHETER', 'BAISSIER': 'VENDRE', 'NEUTRE': 'SURVEILLER'}
    _rec_cls   = {'HAUSSIER': 'suivi-badge-bull', 'BAISSIER': 'suivi-badge-bear', 'NEUTRE': 'suivi-badge-neutral'}
    _rec_icon  = {'HAUSSIER': 'fas fa-arrow-trend-up', 'BAISSIER': 'fas fa-arrow-trend-down', 'NEUTRE': 'fas fa-minus'}
    _tip_icon  = {'HAUSSIER': 'fas fa-circle-up', 'BAISSIER': 'fas fa-circle-down', 'NEUTRE': 'fas fa-circle-pause'}
    _tip_color = {'HAUSSIER': '#00f0a0', 'BAISSIER': '#ff4d6d', 'NEUTRE': '#f0c040'}
    _tip_title = {
        'HAUSSIER': "C'est le moment d'acheter",
        'BAISSIER': "Attention — signal négatif",
        'NEUTRE': "Pas encore — attendez",
    }
    _tip_body = {
        'HAUSSIER': "Notre IA a analysé les dernières actualités et les signaux sont positifs. Les investisseurs réagissent bien — c'est un bon moment pour investir.",
        'BAISSIER': "Les actualités récentes sont mauvaises pour cette entreprise. Notre IA a repéré des signaux négatifs — le cours risque de baisser. Mieux vaut attendre.",
        'NEUTRE': "Les signaux sont encore flous. Notre IA n'est pas assez sûre pour te donner un conseil clair. Reviens dans quelques heures.",
    }

    cards = []
    for ticker, data in pred_data.items():
        signal = data.get('signal', 'NEUTRE')
        entry = data.get('entry_price', 0)
        current = data.get('current_price', 0)
        change = data.get('change_pct', 0)
        articles = data.get('articles', 0)
        name = data.get('name', ticker)
        entry_date = data.get('entry_date', '')
        current_date = data.get('current_date', '')

        rec_label = _rec_label.get(signal, signal)

        tip_color = _tip_color.get(signal, '#f0c040')
        _tip_border = {'HAUSSIER': 'rgba(0,255,135,0.35)', 'BAISSIER': 'rgba(255,77,109,0.35)', 'NEUTRE': 'rgba(240,192,64,0.35)'}
        tip_border = _tip_border.get(signal, 'rgba(0,240,255,0.35)')

        cards.append(html.Div(className="suivi-pred-card", children=[
            html.Div(className="suivi-card-top", children=[
                html.Div(className="suivi-card-id", children=[
                    html.Span(ticker, className="suivi-card-ticker"),
                    html.Span(name, className="suivi-card-name"),
                ]),
                html.Span(className=f"suivi-badge {_rec_cls.get(signal, '')}", children=[
                    html.I(className=_rec_icon.get(signal, 'fas fa-minus')),
                    f"  {rec_label}",
                ]),
            ]),
            html.Div(className="suivi-date-row", children=[
                html.I(className="fas fa-clock"),
                html.Span(f"Conseil valable jusqu'au {data.get('signal_valid_to', '—')}", className="suivi-date-valid"),
                html.Span(data.get('horizon_label', '~48h'), className="suivi-date-horizon"),
            ]),
            html.Div(className="suivi-card-footer", children=[
                html.Span([html.I(className="fas fa-newspaper"), f"  {articles} articles"],
                          className="suivi-card-meta"),
                html.Div(className="suivi-card-btns", children=[
                    html.Button(
                        [html.I(className="fas fa-chart-area"), "  Voir l'historique"],
                        id={"type": "suivi-bt-open", "index": ticker},
                        className="suivi-evo-btn",
                        n_clicks=0,
                    ),
                    html.Button(
                        [html.I(className="fas fa-calculator"), "  Calculer mon gain"],
                        id={"type": "suivi-open", "index": ticker},
                        className="suivi-sim-btn",
                        n_clicks=0,
                    ),
                ]),
            ]),

            # Tooltip cursor-following
            html.Div(className="suivi-pred-tooltip", style={"borderColor": tip_border}, children=[
                html.Div(className="suivi-pred-tooltip-inner", children=[
                    html.I(
                        className=_tip_icon.get(signal, 'fas fa-circle-info'),
                        style={"fontSize": "1.8rem", "color": tip_color, "marginBottom": "8px"},
                    ),
                    html.Div(_tip_title.get(signal, ''), className="suivi-pred-tooltip-title",
                             style={"color": tip_color}),
                    html.Div(f"{name} — {ticker}", className="suivi-pred-tooltip-company"),
                    html.P(_tip_body.get(signal, ''), className="suivi-pred-tooltip-body"),
                    html.Div(className="suivi-pred-tooltip-prices", children=[
                        html.Span(f"Le {entry_date} : ${entry:,.2f}" if entry_date else f"Conseil : ${entry:,.2f}",
                                  className="suivi-pred-tooltip-price-item"),
                        html.I(className="fas fa-arrow-right", style={"color": "#4a5c7a", "fontSize": "0.7rem"}),
                        html.Span(f"Auj. ({current_date}) : ${current:,.2f}" if current_date else f"Maintenant : ${current:,.2f}",
                                  className="suivi-pred-tooltip-price-item"),
                    ]),
                    html.Div(className="suivi-pred-tooltip-footer", children=[
                        html.I(className="fas fa-clock"),
                        html.Span(f" Valable jusqu'au {data.get('signal_valid_to', '—')}"),
                        html.Span(f" · {articles} articles analysés", style={"opacity": "0.5"}),
                    ]),
                ]),
            ]),
        ]))

    return welcome, cards


@callback(
    Output("suivi-kpis", "children"),
    Input("suivi-refresh", "data"),
    Input("suivi-pred-store", "data"),
    State("session-store", "data"),
)
def render_kpis(_trigger, _pred, session):
    if not session:
        return []

    stats = get_user_stats(session.get("email"))
    total_pnl = stats.get('total_pnl', 0)

    items = [
        {
            "icon": "fas fa-chart-line",
            "label": "Mes gains / pertes au total",
            "value": f"{total_pnl:+,.2f} €",
            "cls": "suivi-kpi-pos" if total_pnl >= 0 else "suivi-kpi-neg",
            "detail": f"{stats.get('win_rate', 0):.1f}% de réussite",
        },
        {
            "icon": "fas fa-list-check",
            "label": "Investissements enregistrés",
            "value": str(stats.get('total_trades', 0)),
            "cls": "",
            "detail": f"{stats.get('wins', 0)} réussis  •  {stats.get('losses', 0)} perdants",
        },
        {
            "icon": "fas fa-trophy",
            "label": "Décisions gagnantes",
            "value": f"{stats.get('win_rate', 0):.1f}%",
            "cls": "suivi-kpi-pos" if stats.get('win_rate', 0) >= 50 else "suivi-kpi-neg",
            "detail": "sur les investissements terminés",
        },
        {
            "icon": "fas fa-bolt",
            "label": "En cours de suivi",
            "value": str(stats.get('open_trades', 0)),
            "cls": "",
            "detail": "investissements actifs",
        },
    ]

    return [
        html.Div(className="suivi-kpi-card", children=[
            html.Div(className="suivi-kpi-icon", children=html.I(className=k["icon"])),
            html.Div(className="suivi-kpi-body", children=[
                html.Span(k["label"], className="suivi-kpi-lbl"),
                html.Span(k["value"], className=f"suivi-kpi-val {k['cls']}"),
                html.Span(k["detail"], className="suivi-kpi-detail"),
            ]),
        ])
        for k in items
    ]


def _action_classes(action):
    buy = "suivi-action-btn suivi-action-buy" + (" active" if action == "ACHAT" else "")
    sell = "suivi-action-btn suivi-action-sell" + (" active" if action == "VENTE" else "")
    return buy, sell


def _action_hint(action, signal):
    follows = (action == "ACHAT" and signal == "HAUSSIER") or (action == "VENTE" and signal == "BAISSIER")
    if action == "ACHAT":
        label = "Vous achetez — vous misez sur une hausse du prix"
    else:
        label = "Vous vendez — vous misez sur une baisse du prix"
    icon_cls = "fas fa-circle-check suivi-hint-ok" if follows else "fas fa-triangle-exclamation suivi-hint-warn"
    suffix = " (suit le conseil IA ✓)" if follows else " (à l'opposé du conseil IA)"
    return html.Span([html.I(className=icon_cls), f"  {label}{suffix}"], className="suivi-action-hint-inner")


@callback(
    Output("suivi-modal-bg", "className"),
    Output("suivi-modal-ticker", "data"),
    Output("suivi-modal-heading", "children"),
    Output("suivi-modal-info", "children"),
    Output("suivi-amount", "value"),
    Output("suivi-sim-result", "children"),
    Output("suivi-feedback", "children"),
    Output("suivi-modal-action", "data"),
    Output("suivi-action-buy", "className"),
    Output("suivi-action-sell", "className"),
    Output("suivi-action-hint", "children"),
    Input({"type": "suivi-open", "index": ALL}, "n_clicks"),
    Input("suivi-close-btn", "n_clicks"),
    Input("suivi-btn-sim", "n_clicks"),
    State("suivi-pred-store", "data"),
    prevent_initial_call=True,
)
def handle_modal(open_clicks, _close, _sim, pred_data):
    _nu = dash.no_update
    triggered = ctx.triggered_id

    if triggered in ("suivi-close-btn", "suivi-btn-sim"):
        buy_cls, sell_cls = _action_classes("ACHAT")
        return "suivi-modal-hidden", None, "", "", None, "", "", "ACHAT", buy_cls, sell_cls, ""

    if not any(n for n in (open_clicks or []) if n):
        return (_nu,) * 11

    if not isinstance(triggered, dict) or triggered.get("type") != "suivi-open":
        return (_nu,) * 11

    ticker = triggered["index"]
    if not pred_data or ticker not in pred_data:
        return (_nu,) * 11

    data = pred_data[ticker]
    signal = data['signal']
    entry = data['entry_price']
    current = data['current_price']
    change = data['change_pct']
    conf = data['confidence']
    name = data['name']
    entry_date = data.get('entry_date', '')
    current_date = data.get('current_date', '')

    # Action par défaut : suit le signal IA
    default_action = "ACHAT" if signal in ("HAUSSIER", "NEUTRE") else "VENTE"
    buy_cls, sell_cls = _action_classes(default_action)
    hint = _action_hint(default_action, signal)

    sig_cls = {'HAUSSIER': 'suivi-badge-bull', 'BAISSIER': 'suivi-badge-bear', 'NEUTRE': 'suivi-badge-neutral'}.get(signal, '')
    chg_cls = "suivi-pos" if change > 0 else "suivi-neg" if change < 0 else ""

    heading = [
        html.Span(ticker, className="suivi-modal-ticker-txt"),
        html.Span(f"  —  {name}", className="suivi-modal-name-txt"),
    ]

    tip_map = {
        'HAUSSIER': f"L'IA pense que le prix va monter — elle conseille d'acheter {ticker}",
        'BAISSIER': f"L'IA pense que le prix va baisser — elle conseille de vendre {ticker}",
        'NEUTRE':   f"L'IA n'est pas sûre pour {ticker} — mieux vaut attendre",
    }

    info = html.Div(className="suivi-modal-info-grid", children=[
        html.Div(className="suivi-modal-signal-row", children=[
            html.Span("Conseil IA :", className="suivi-modal-lbl"),
            html.Span(signal, className=f"suivi-badge {sig_cls}"),
            html.Span(f"Fiabilité : {conf:.0f}%", className="suivi-modal-conf"),
        ]),
        html.Div(className="suivi-modal-prices-row", children=[
            html.Div(className="suivi-mpi", children=[
                html.Span(f"Prix réel le {entry_date}" if entry_date else "Prix au conseil", className="suivi-modal-lbl"),
                html.Span(f"${entry:,.2f}", className="suivi-modal-price"),
            ]),
            html.I(className="fas fa-arrow-right suivi-modal-arrow"),
            html.Div(className="suivi-mpi", children=[
                html.Span(f"Prix réel le {current_date}" if current_date else "Prix aujourd'hui", className="suivi-modal-lbl"),
                html.Span(f"${current:,.2f}", className="suivi-modal-price"),
            ]),
            html.Div(className="suivi-mpi", children=[
                html.Span("Évolution", className="suivi-modal-lbl"),
                html.Span(f"{change:+.2f}%", className=f"suivi-modal-price {chg_cls}"),
            ]),
        ]),
        html.Div(className="suivi-modal-tip", children=[
            html.I(className="fas fa-lightbulb"),
            f"  {tip_map.get(signal, '')}",
        ]),
    ])

    return (
        "suivi-modal-visible", {"ticker": ticker},
        heading, info, None, "", "",
        default_action, buy_cls, sell_cls, hint,
    )


@callback(
    Output("suivi-modal-action", "data", allow_duplicate=True),
    Output("suivi-action-buy", "className", allow_duplicate=True),
    Output("suivi-action-sell", "className", allow_duplicate=True),
    Output("suivi-action-hint", "children", allow_duplicate=True),
    Input("suivi-action-buy", "n_clicks"),
    Input("suivi-action-sell", "n_clicks"),
    State("suivi-modal-ticker", "data"),
    State("suivi-pred-store", "data"),
    prevent_initial_call=True,
)
def toggle_action(_buy, _sell, modal_ticker, pred_data):
    triggered = ctx.triggered_id
    action = "ACHAT" if triggered == "suivi-action-buy" else "VENTE"
    signal = ""
    if modal_ticker and pred_data:
        signal = (pred_data.get(modal_ticker.get("ticker", "")) or {}).get("signal", "")
    buy_cls, sell_cls = _action_classes(action)
    return action, buy_cls, sell_cls, _action_hint(action, signal)


@callback(
    Output("suivi-sim-result", "children", allow_duplicate=True),
    Input("suivi-amount", "value"),
    Input("suivi-modal-action", "data"),
    State("suivi-modal-ticker", "data"),
    State("suivi-pred-store", "data"),
    prevent_initial_call=True,
)
def update_simulation(amount, action, modal_ticker, pred_data):
    if not amount or not modal_ticker or not pred_data:
        return ""

    ticker = modal_ticker.get("ticker", "")
    if ticker not in pred_data:
        return ""

    data = pred_data[ticker]
    signal = data['signal']
    entry = data['entry_price']
    current = data['current_price']
    name = data['name']

    if entry == 0:
        return html.Div("Donnees de prix non disponibles", className="suivi-sim-error")

    amount = _parse_amount(amount)
    if not amount:
        return ""

    action = action or "ACHAT"

    # Calcul du P&L selon l'action réelle (indépendant du signal)
    if entry == 0:
        return html.Div("Données de prix non disponibles", className="suivi-sim-error")

    if action == "ACHAT":
        pnl = (current - entry) / entry * amount
        action_lbl = "ACHAT (position longue)"
    else:
        pnl = (entry - current) / entry * amount
        action_lbl = "VENTE (position courte)"

    pnl_pct = (pnl / amount * 100) if amount else 0
    is_gain = pnl >= 0
    result_cls = "suivi-sim-gain" if is_gain else "suivi-sim-loss"

    return html.Div(className=f"suivi-sim-box {result_cls}", children=[
        html.Div(className="suivi-sim-title", children=[
            html.I(className="fas fa-calculator"),
            f"  Résultat — {action_lbl}",
        ]),
        html.Div(className="suivi-sim-main", children=[
            html.Span(f"Si vous aviez fait un {action} de {amount:,.0f} € :", className="suivi-sim-lbl"),
            html.Div(className="suivi-sim-values", children=[
                html.Span(f"{pnl:+,.2f} €", className="suivi-sim-pnl"),
                html.Span(f"( {pnl_pct:+.2f}% )", className="suivi-sim-pct"),
            ]),
        ]),
        html.Div(className="suivi-sim-details", children=[
            html.Span([html.I(className="fas fa-arrow-right-to-bracket"), f"  Montant investi : {amount:,.0f} €"]),
            html.Span([html.I(className="fas fa-arrow-right-from-bracket"), f"  Ce que vous auriez maintenant : {amount + pnl:,.2f} €"]),
        ]),
        html.P(
            f"{name} — prix au conseil : ${entry:,.2f} · prix actuel : ${current:,.2f}",
            className="suivi-sim-note",
        ),
    ])


@callback(
    Output("suivi-feedback", "children", allow_duplicate=True),
    Output("suivi-refresh", "data", allow_duplicate=True),
    Output("suivi-modal-bg", "className", allow_duplicate=True),
    Input("suivi-btn-followed", "n_clicks"),
    State("suivi-amount", "value"),
    State("suivi-modal-ticker", "data"),
    State("suivi-pred-store", "data"),
    State("session-store", "data"),
    State("suivi-refresh", "data"),
    State("suivi-modal-action", "data"),
    prevent_initial_call=True,
)
def save_trade(n_clicks, amount, modal_ticker, pred_data, session, refresh_count, action):
    if not n_clicks or not amount or not modal_ticker or not session:
        return dash.no_update, dash.no_update, dash.no_update

    amount = _parse_amount(amount)
    if not amount:
        return html.Div("Montant invalide", className="suivi-feedback-err"), refresh_count, dash.no_update

    ticker = modal_ticker.get("ticker", "")
    if not ticker or ticker not in pred_data:
        return html.Div("Erreur : donnees manquantes", className="suivi-feedback-err"), refresh_count, dash.no_update

    data = pred_data[ticker]
    ok = save_followed_trade(
        user_email=session.get("email"),
        symbol=ticker,
        signal=data['signal'],
        entry_price=data['entry_price'],
        current_price=data['current_price'],
        amount=amount,
        action=action or "ACHAT",
    )

    if ok:
        return "", refresh_count + 1, "suivi-modal-hidden"

    return html.Div("Erreur lors de l'enregistrement", className="suivi-feedback-err"), refresh_count, dash.no_update


@callback(
    Output("suivi-report-download", "data"),
    Input("suivi-export-report-btn", "n_clicks"),
    State("session-store", "data"),
    prevent_initial_call=True,
)
def export_tracking_report(n_clicks, session):
    if not n_clicks or not session:
        return dash.no_update

    email = session.get("email", "")
    if not email:
        return dash.no_update

    report = _build_tracking_report_pdf(email)
    stamp = datetime.now().strftime("%Y%m%d_%H%M")
    return dcc.send_bytes(
        lambda buffer: buffer.write(report),
        filename=f"rapport_mon_suivi_{stamp}.pdf",
    )


@callback(
    Output("suivi-history", "children"),
    Input("suivi-refresh", "data"),
    Input("suivi-init", "n_intervals"),
    State("session-store", "data"),
)
def render_history(_trigger, _init, session):
    if not session:
        return html.Div("Connectez-vous pour voir votre historique", className="suivi-empty")

    trades = get_user_trades(session.get("email"), 20)

    if not trades:
        return html.Div(className="suivi-empty", children=[
            html.I(className="fas fa-inbox", style={"fontSize": "2.5rem", "display": "block", "marginBottom": "12px"}),
            html.P("Vous n'avez pas encore enregistré d'investissement"),
            html.P(
                "Cliquez sur 'Calculer mon gain' puis 'J'ai fait cet investissement' pour le sauvegarder ici",
                className="suivi-empty-sub",
            ),
        ])

    sig_display = {'up': 'HAUSSIER', 'down': 'BAISSIER', 'neutral': 'NEUTRE'}
    sig_cls = {'HAUSSIER': 'suivi-badge-bull', 'BAISSIER': 'suivi-badge-bear', 'NEUTRE': 'suivi-badge-neutral'}

    rows = []
    for t in trades:
        # id(0) user_email(1) symbol(2) entry_price(3) exit_price(4)
        # entry_date(5) exit_date(6) quantity(7) prediction_direction(8)
        # actual_direction(9) pnl(10) pnl_percentage(11) status(12)
        symbol = t[2]
        entry = t[3] or 0
        exit_p = t[4]
        entry_date = str(t[5])[:10] if t[5] else '-'
        qty = t[7] or 0
        pred_dir = t[8] or 'neutral'
        actual_dir = t[9] or 'up'
        pnl = t[10] or 0
        pnl_pct = t[11] or 0

        pnl_cls = "suivi-td-pos" if pnl > 0 else "suivi-td-neg" if pnl < 0 else ""
        signal_lbl = sig_display.get(pred_dir, pred_dir.upper())
        badge = sig_cls.get(signal_lbl, '')

        # ACHAT si actual_direction='up', VENTE si 'down'
        op_label = "ACHAT" if actual_dir == 'up' else "VENTE"
        op_cls = "suivi-op-buy" if actual_dir == 'up' else "suivi-op-sell"
        op_icon = "fas fa-arrow-trend-up" if actual_dir == 'up' else "fas fa-arrow-trend-down"

        rows.append(html.Tr([
            html.Td(html.Span(symbol, className="suivi-td-ticker")),
            html.Td(html.Span(signal_lbl, className=f"suivi-badge-sm {badge}")),
            html.Td(html.Span(
                [html.I(className=op_icon), f"  {op_label}"],
                className=f"suivi-op-badge {op_cls}",
            )),
            html.Td(f"{qty:,.0f} €" if qty else '-'),
            html.Td(f"${entry:,.2f}"),
            html.Td(f"${exit_p:,.2f}" if exit_p else '—'),
            html.Td(html.Span(f"{pnl:+,.2f} €", className=pnl_cls)),
            html.Td(html.Span(f"{pnl_pct:+.2f}%", className=pnl_cls)),
            html.Td(entry_date),
        ]))

    return html.Div(className="suivi-table-wrap", children=[
        html.Table(className="suivi-table", children=[
            html.Thead(html.Tr([
                html.Th([html.I(className="fas fa-coins"), "  Action"]),
                html.Th([html.I(className="fas fa-robot"), "  Conseil IA"]),
                html.Th([html.I(className="fas fa-exchange-alt"), "  Achat / Vente"]),
                html.Th([html.I(className="fas fa-wallet"), "  Montant"]),
                html.Th("Prix d'achat"),
                html.Th("Prix de vente"),
                html.Th([html.I(className="fas fa-chart-simple"), "  Gain / Perte"]),
                html.Th("En %"),
                html.Th([html.I(className="fas fa-calendar"), "  Date"]),
            ])),
            html.Tbody(rows),
        ]),
    ])


@callback(
    Output("suivi-ticker-select", "options"),
    Output("suivi-ticker-select", "value"),
    Input("suivi-refresh", "data"),
    Input("suivi-init", "n_intervals"),
    State("session-store", "data"),
    State("suivi-ticker-select", "value"),
)
def update_ticker_options(_refresh, _init, session, current_value):
    if not session:
        return [], None
    trades = get_user_trades(session.get('email'), 200)
    # Tickers uniques dans l'ordre d'apparition (plus récent en premier)
    seen = {}
    for t in trades:
        sym = t[2]
        if sym and sym not in seen:
            seen[sym] = COMPANIES.get(sym, sym)
    if not seen:
        return [], None
    options = [{'label': f"{sym} — {name}", 'value': sym} for sym, name in seen.items()]
    # Garder la sélection courante si elle est toujours valide, sinon prendre le premier
    default = current_value if current_value and current_value in seen else list(seen.keys())[0]
    return options, default


@callback(
    Output("suivi-perf-chart", "figure"),
    Input("suivi-ticker-select", "value"),
    Input("suivi-refresh", "data"),
    State("session-store", "data"),
)
def render_perf_chart(ticker, _refresh, session):
    _empty = go.Figure().update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(5,10,30,0.5)',
        height=400,
        margin=dict(l=60, r=20, t=20, b=50),
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        annotations=[dict(
            text="Aucune donnee disponible pour ce ticker",
            xref="paper", yref="paper", x=0.5, y=0.5,
            showarrow=False, font=dict(color="#7a8aaa", size=14),
        )],
    )

    if not ticker or not session:
        return _empty

    # Récupérer les trades de l'utilisateur sur ce ticker
    all_trades = get_user_trades(session.get('email'), 200)
    ticker_trades = [t for t in all_trades if t[2] == ticker]

    if not ticker_trades:
        return _empty

    # Calculer la date du premier trade pour ce ticker (± 5 jours avant pour contexte)
    first_dates = []
    for t in ticker_trades:
        d = str(t[5])[:10] if t[5] else None
        if d:
            try:
                first_dates.append(pd.to_datetime(d))
            except Exception:
                pass
    start_date = (min(first_dates) - timedelta(days=5)) if first_dates else (datetime.now() - timedelta(days=90))
    days_needed = max(30, (datetime.now() - start_date).days + 5)

    df = _load_price_history(ticker, days=days_needed)
    if df.empty:
        return _empty

    # Filtrer depuis start_date
    df = df[df['date'] >= pd.Timestamp(start_date)]
    if df.empty:
        return _empty

    fig = go.Figure()

    # Zone de remplissage sous la courbe
    fig.add_trace(go.Scatter(
        x=df['date'], y=df['Close'],
        fill='tozeroy',
        fillcolor='rgba(0,240,255,0.04)',
        line=dict(width=0),
        showlegend=False,
        hoverinfo='skip',
    ))

    # Courbe des prix reels
    fig.add_trace(go.Scatter(
        x=df['date'], y=df['Close'],
        mode='lines',
        name='Prix réel',
        line=dict(color='rgba(0,240,255,0.75)', width=2),
        hovertemplate='%{x|%d %b %Y}<br>Prix : $%{y:,.2f}<extra></extra>',
    ))

    # Points d'investissement utilisateur
    win_x, win_y, win_text = [], [], []
    loss_x, loss_y, loss_text = [], [], []
    annotations = []

    for t in ticker_trades:
        entry_date_str = str(t[5])[:10] if t[5] else None
        if not entry_date_str:
            continue
        try:
            entry_dt = pd.to_datetime(entry_date_str)
        except Exception:
            continue

        entry_price = float(t[3] or 0)
        pnl = float(t[10] or 0)
        pnl_pct = float(t[11] or 0)
        qty = float(t[7] or 0)
        exit_price = t[4]
        action = "Vous avez acheté" if (t[8] or '') == 'up' else "Vous avez vendu"

        hover = (
            f"<b>{action} le {entry_date_str}</b><br>"
            f"Prix : ${entry_price:,.2f}"
            + (f" → ${float(exit_price):,.2f}" if exit_price else "")
            + f"<br>Montant : {qty:,.0f} €"
            + f"<br><b>Résultat : {'+' if pnl >= 0 else ''}{pnl:,.2f} € ({pnl_pct:+.2f}%)</b>"
        )

        label = f"{'✓ Gagné' if pnl >= 0 else '✗ Perdu'} {pnl:+.0f}€"
        color = '#00ff87' if pnl >= 0 else '#ff4d6d'

        # Ligne verticale au moment de l'investissement
        fig.add_vline(
            x=entry_dt.timestamp() * 1000,
            line=dict(color=color, width=1, dash='dot'),
            opacity=0.4,
        )

        # Annotation texte au-dessus du point
        annotations.append(dict(
            x=entry_dt, y=entry_price,
            text=label,
            showarrow=True,
            arrowhead=2,
            arrowcolor=color,
            arrowsize=1,
            arrowwidth=1.5,
            ax=0, ay=-38,
            font=dict(color=color, size=10, family='Inter, sans-serif'),
            bgcolor='rgba(2,6,22,0.85)',
            bordercolor=color,
            borderwidth=1,
            borderpad=4,
        ))

        if pnl >= 0:
            win_x.append(entry_dt)
            win_y.append(entry_price)
            win_text.append(hover)
        else:
            loss_x.append(entry_dt)
            loss_y.append(entry_price)
            loss_text.append(hover)

    if win_x:
        fig.add_trace(go.Scatter(
            x=win_x, y=win_y,
            mode='markers',
            name='✓ Vous avez gagné',
            marker=dict(color='#00ff87', size=14, symbol='triangle-up',
                        line=dict(color='#010214', width=1.5)),
            hovertemplate='%{customdata}<extra></extra>',
            customdata=win_text,
        ))

    if loss_x:
        fig.add_trace(go.Scatter(
            x=loss_x, y=loss_y,
            mode='markers',
            name='✗ Vous avez perdu',
            marker=dict(color='#ff4d6d', size=14, symbol='triangle-down',
                        line=dict(color='#010214', width=1.5)),
            hovertemplate='%{customdata}<extra></extra>',
            customdata=loss_text,
        ))

    if annotations:
        fig.update_layout(annotations=annotations)

    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(5,10,30,0.55)',
        font=dict(color='#eaf6ff', family='Inter, sans-serif', size=11),
        height=420,
        margin=dict(l=65, r=20, t=20, b=50),
        showlegend=True,
        legend=dict(
            bgcolor='rgba(1,2,20,0.7)',
            bordercolor='rgba(0,240,255,0.15)',
            borderwidth=1,
            font=dict(color='#b8dff0', size=11),
            x=0.01, y=0.98,
        ),
        xaxis=dict(
            gridcolor='rgba(0,240,255,0.06)',
            tickfont=dict(color='#7a8aaa', size=10),
            tickformat='%d %b',
            showgrid=True,
            linecolor='rgba(0,240,255,0.1)',
            zeroline=False,
        ),
        yaxis=dict(
            gridcolor='rgba(0,240,255,0.06)',
            tickfont=dict(color='#7a8aaa', size=10),
            tickprefix='$',
            showgrid=True,
            linecolor='rgba(0,240,255,0.1)',
            zeroline=False,
        ),
        hovermode='x unified',
    )

    return fig


# ==================== BACKTEST CALLBACKS ====================

@callback(
    Output("suivi-backtest-bg", "className"),
    Output("suivi-backtest-ticker-store", "data"),
    Input({"type": "suivi-bt-open", "index": ALL}, "n_clicks"),
    Input("suivi-backtest-close", "n_clicks"),
    prevent_initial_call=True,
)
def toggle_backtest_modal(card_clicks, close_n):
    triggered = ctx.triggered_id

    if triggered == "suivi-backtest-close":
        return "suivi-modal-hidden", no_update

    if isinstance(triggered, dict) and triggered.get("type") == "suivi-bt-open":
        if not any(n for n in (card_clicks or []) if n):
            return no_update, no_update
        return "suivi-modal-visible", triggered["index"]

    return no_update, no_update


@callback(
    Output("suivi-backtest-title", "children"),
    Output("suivi-backtest-sub", "children"),
    Output("suivi-backtest-summary", "children"),
    Output("suivi-backtest-stats", "children"),
    Output("suivi-backtest-chart", "figure"),
    Output("suivi-backtest-trades", "children"),
    Input("suivi-backtest-ticker-store", "data"),
    Input("suivi-backtest-recalc-btn", "n_clicks"),
    State("suivi-backtest-amount-input", "value"),
    prevent_initial_call=True,
)
def render_backtest(ticker, _recalc, user_amount):
    try:
        amount = float(user_amount) if user_amount and float(user_amount) > 0 else 500.0
    except (TypeError, ValueError):
        amount = 500.0

    _empty_fig = go.Figure().update_layout(
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(5,10,30,0.5)',
        height=360, margin=dict(l=55, r=15, t=15, b=40),
        xaxis=dict(visible=False), yaxis=dict(visible=False),
        annotations=[dict(
            text="Données insuffisantes pour ce ticker",
            xref="paper", yref="paper", x=0.5, y=0.5,
            showarrow=False, font=dict(color="#7a8aaa", size=14),
        )],
    )

    company = COMPANIES.get(ticker, ticker) if ticker else "—"
    title = f"{ticker} — {company}" if ticker else "Backtest IA"
    sub = f"{amount:,.0f} € investis en suivant nos signaux IA sur {company} — évolution historique réelle"

    if not ticker:
        return title, "Sélectionnez une action depuis les cartes de prédiction", "", [], _empty_fig, []

    bt = _run_backtest(ticker, start_amount=amount, days=180)
    if not bt:
        return title, sub, "", [], _empty_fig, []

    # ── Stats ──
    final = bt['final_value']
    ret = bt['total_return']
    bh_ret = bt['buy_hold_return']
    gain = final - amount
    ret_cls = "suivi-bt-pos" if ret >= 0 else "suivi-bt-neg"
    bh_cls = "suivi-bt-pos" if bh_ret >= 0 else "suivi-bt-neg"
    gain_color = "#00ff87" if gain >= 0 else "#ff4d6d"
    verb = "gagné" if gain >= 0 else "perdu"
    vs_bh = final - bt['buy_hold'][-1]
    bh_final = bt['buy_hold'][-1]
    if vs_bh >= 0:
        vs_bh_txt = (
            f"En suivant nos conseils, vous avez gagné {abs(vs_bh):,.2f} € de plus "
            f"que quelqu'un qui aurait juste acheté et rien fait (qui aurait eu {bh_final:,.2f} €)."
        )
    else:
        vs_bh_txt = (
            f"À titre de comparaison, quelqu'un qui aurait juste acheté et attendu sans rien faire "
            f"aurait eu {bh_final:,.2f} € — soit {abs(vs_bh):,.2f} € de plus que la stratégie IA sur cette période."
        )

    first_signal = bt['start_date']
    data_window = bt['data_start']
    summary = html.Div(className="suivi-bt-summary", children=[
        html.I(className="fas fa-lightbulb"),
        html.Span([
            "Si vous aviez investi ",
            html.Strong(f"{amount:,.0f} €", style={"color": "#eaf6ff"}),
            f" sur {company} à partir du ",
            html.Strong(first_signal, style={"color": "#eaf6ff"}),
            " (premier conseil IA disponible) et suivi tous nos conseils jusqu'à aujourd'hui, vous auriez ",
            html.Strong(f"{final:,.2f} €", style={"color": gain_color}),
            " — soit ",
            html.Strong(f"{gain:+,.2f} € ({ret:+.1f}%)", style={"color": gain_color}),
            f". {vs_bh_txt}",
        ]),
    ])

    stats = html.Div(className="suivi-bt-stats-grid", children=[
        html.Div(className="suivi-bt-stat", children=[
            html.Div("Montant de départ", className="suivi-bt-slbl"),
            html.Div(f"{amount:,.0f} €", className="suivi-bt-sval"),
        ]),
        html.Div(className="suivi-bt-stat suivi-bt-stat-main", children=[
            html.Div("Ce que vous auriez maintenant", className="suivi-bt-slbl"),
            html.Div(f"{final:,.2f} €", className=f"suivi-bt-sval {ret_cls}"),
            html.Div(f"{gain:+,.2f} € ({ret:+.1f}%)", className=f"suivi-bt-sdiff {ret_cls}"),
        ]),
        html.Div(className="suivi-bt-stat", children=[
            html.Div("Sans suivre les conseils", className="suivi-bt-slbl"),
            html.Div(f"{bt['buy_hold'][-1]:,.2f} €", className=f"suivi-bt-sval {bh_cls}"),
            html.Div(f"{bh_ret:+.1f}%", className=f"suivi-bt-sdiff {bh_cls}"),
        ]),
        html.Div(className="suivi-bt-stat", children=[
            html.Div("Décisions IA prises", className="suivi-bt-slbl"),
            html.Div(str(bt['n_trades']), className="suivi-bt-sval"),
            html.Div(f"{bt['wins']} réussies / {bt['losses']} perdantes", className="suivi-bt-sdiff"),
        ]),
        html.Div(className="suivi-bt-stat", children=[
            html.Div("Décisions gagnantes", className="suivi-bt-slbl"),
            html.Div(f"{bt['win_rate']}%", className=f"suivi-bt-sval {'suivi-bt-pos' if bt['win_rate'] >= 50 else 'suivi-bt-neg'}"),
            html.Div(f"1er signal : {bt['start_date']}", className="suivi-bt-sdiff"),
        ]),
    ])

    # ── Graphique : aligner sur le premier signal réel ──
    chart_dates = bt['dates']
    chart_portfolio = bt['portfolio']
    chart_bh = bt['buy_hold']

    if bt.get('first_signal_ts') and chart_dates:
        try:
            from datetime import datetime as _dt
            first_sig_dt = pd.Timestamp(_dt.strptime(bt['first_signal_ts'], '%d %b %Y'))
            chart_from = first_sig_dt - timedelta(days=7)
            mask = [d >= chart_from for d in chart_dates]
            if any(mask):
                chart_dates = [d for d, m in zip(chart_dates, mask) if m]
                chart_portfolio = [v for v, m in zip(chart_portfolio, mask) if m]
                chart_bh = [v for v, m in zip(chart_bh, mask) if m]
                # Recaler les deux courbes sur le même point de départ (amount €)
                if chart_portfolio and chart_bh:
                    port_offset = amount - chart_portfolio[0]
                    bh_offset = amount - chart_bh[0]
                    chart_portfolio = [v + port_offset for v in chart_portfolio]
                    chart_bh = [v + bh_offset for v in chart_bh]
        except Exception:
            pass

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=chart_dates, y=chart_bh,
        mode='lines', name='Sans suivre les conseils',
        line=dict(color='rgba(140,180,220,0.4)', width=1.5, dash='dot'),
        hovertemplate='%{x|%d %b %Y}<br>Sans conseils : %{y:,.2f} €<extra></extra>',
    ))
    fig.add_trace(go.Scatter(
        x=chart_dates, y=chart_portfolio,
        mode='lines', name='En suivant les conseils IA',
        line=dict(color='#00f0ff', width=2.5),
        fill='tonexty',
        fillcolor='rgba(0,240,255,0.04)',
        hovertemplate='%{x|%d %b %Y}<br>Avec les conseils : %{y:,.2f} €<extra></extra>',
    ))

    # Ligne de départ
    fig.add_hline(
        y=amount, line_dash="dash",
        line_color="rgba(255,255,255,0.2)", line_width=1,
        annotation_text=f"Départ : {amount:.0f} €",
        annotation_font_color="#7a8aaa", annotation_font_size=10,
    )

    fig.update_layout(
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(5,10,30,0.55)',
        font=dict(color='#eaf6ff', family='Inter, sans-serif', size=11),
        height=360,
        margin=dict(l=65, r=15, t=15, b=45),
        showlegend=True,
        legend=dict(
            bgcolor='rgba(1,2,20,0.7)', bordercolor='rgba(0,240,255,0.15)',
            borderwidth=1, font=dict(color='#b8dff0', size=11), x=0.01, y=0.98,
        ),
        xaxis=dict(gridcolor='rgba(0,240,255,0.06)', tickfont=dict(color='#7a8aaa', size=10),
                   tickformat='%d %b', showgrid=True, zeroline=False),
        yaxis=dict(gridcolor='rgba(0,240,255,0.06)', tickfont=dict(color='#7a8aaa', size=10),
                   tickprefix='', ticksuffix=' €', showgrid=True, zeroline=False),
        hovermode='x unified',
    )

    # ── Tableau des derniers trades ──
    if not bt['trades']:
        trades_el = html.Div("Aucun trade détecté sur cette période", className="suivi-bt-no-trades")
    else:
        _icon = {'ACHETER': 'fas fa-arrow-trend-up', 'VENDRE': 'fas fa-arrow-trend-down'}
        _cls = {'ACHETER': 'suivi-bt-buy', 'VENDRE': 'suivi-bt-sell'}
        rows = [
            html.Tr([
                html.Td(tr['date']),
                html.Td(html.Span(
                    [html.I(className=_icon.get(tr['signal'], '')), f"  {tr['signal']}"],
                    className=f"suivi-op-badge {_cls.get(tr['signal'], '')}",
                )),
                html.Td(
                    html.Span(
                        f"{tr['return_pct']:+.2f}%",
                        className="suivi-td-pos" if tr['return_pct'] >= 0 else "suivi-td-neg",
                    )
                ),
                html.Td(
                    html.Span(
                        f"{tr['pnl_eur']:+.2f} €",
                        className="suivi-td-pos" if tr['pnl_eur'] >= 0 else "suivi-td-neg",
                    )
                ),
            ])
            for tr in reversed(bt['trades'])
        ]
        trades_el = html.Div(className="suivi-bt-trades-wrap", children=[
            html.H4("Dernières décisions IA", className="suivi-bt-trades-title"),
            html.Table(className="suivi-table", children=[
                html.Thead(html.Tr([
                    html.Th("Date"), html.Th("Conseil"), html.Th("Gain / Perte %"), html.Th("Gain / Perte €"),
                ])),
                html.Tbody(rows),
            ]),
        ])

    return title, sub, summary, stats, fig, trades_el
