"""
strategies_store.py
-------------------
Persistente Verwaltung der Strategie-Bibliothek.

Speichert Strategien als JSON-Datei in data/strategies/strategies.json.
Excel-Uploads landen in data/strategies/uploads/.
"""

import json
import uuid
from datetime import datetime
from pathlib import Path


# =========================================================
# PFADE
# =========================================================

STRATEGIES_DIR = Path("data/strategies")
UPLOADS_DIR = STRATEGIES_DIR / "uploads"
JSON_FILE = STRATEGIES_DIR / "strategies.json"


# =========================================================
# VERZEICHNISSE
# =========================================================

def _ensure_dirs():
    STRATEGIES_DIR.mkdir(parents=True, exist_ok=True)
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)


# =========================================================
# LADEN / SPEICHERN
# =========================================================

def load_all() -> list[dict]:
    """Lädt alle Strategien aus der JSON-Datei."""

    _ensure_dirs()

    if not JSON_FILE.exists():
        return _seed_default_strategies()

    try:
        return json.loads(JSON_FILE.read_text(encoding="utf-8"))
    except Exception:
        return []


def save_all(strategies: list[dict]):
    """Schreibt die Liste zurück in die JSON-Datei."""

    _ensure_dirs()
    JSON_FILE.write_text(
        json.dumps(strategies, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


# =========================================================
# CRUD
# =========================================================

def add_strategy(data: dict) -> dict:
    """Fügt eine neue Strategie hinzu."""

    strategies = load_all()
    data["id"] = str(uuid.uuid4())
    data["created_at"] = datetime.now().isoformat(timespec="seconds")
    strategies.append(data)
    save_all(strategies)
    return data


def update_strategy(strategy_id: str, changes: dict):
    """Aktualisiert eine Strategie anhand ihrer ID."""

    strategies = load_all()
    for s in strategies:
        if s.get("id") == strategy_id:
            s.update(changes)
            break
    save_all(strategies)


def delete_strategy(strategy_id: str):
    """Löscht eine Strategie."""

    strategies = [s for s in load_all() if s.get("id") != strategy_id]
    save_all(strategies)


def get_strategy(strategy_id: str) -> dict | None:
    for s in load_all():
        if s.get("id") == strategy_id:
            return s
    return None


# =========================================================
# FILE-UPLOAD
# =========================================================

def save_uploaded_file(uploaded_file) -> str:
    """
    Speichert eine hochgeladene Datei persistent und gibt den
    relativen Pfad zurück (z. B. "data/strategies/uploads/abc.xlsx").
    """

    _ensure_dirs()

    ext = Path(uploaded_file.name).suffix.lower()
    filename = f"{uuid.uuid4().hex[:12]}{ext}"
    target = UPLOADS_DIR / filename

    target.write_bytes(uploaded_file.getvalue())

    return str(target)


# =========================================================
# DEFAULT-STRATEGIEN (beim ersten Start)
# =========================================================

def _seed_default_strategies() -> list[dict]:
    """Legt beim ersten Start die 3 bekannten Strategien an."""

    defaults = [
        {
            "id": str(uuid.uuid4()),
            "name": "TurnTue QQQ",
            "symbol": "NASDAQ:QQQ",
            "timeframe": "1 Stunde",
            "typ": "Mean Reversion · Wochentag",
            "beschreibung": (
                "Long-Einstieg Montag, wenn der Kurs mindestens 1 % unter dem "
                "Vortagesschluss liegt. Ausstieg am nächsten Tag, wenn der Close "
                "über dem Vortageshoch liegt."
            ),
            "regeln": [
                "Einstieg: Montag + Close < Vortag − 1 %",
                "Ausstieg: Close > Vortages-Hoch",
                "Long only, 100 % Kapital, kein Stop",
            ],
            "pine_code": "",
            "excel_path": "data/imports/TurnTue_NASDAQ_QQQ_2026-09-24.xlsx",
            "created_at": datetime.now().isoformat(timespec="seconds"),
        },
        {
            "id": str(uuid.uuid4()),
            "name": "TLT Season",
            "symbol": "NASDAQ:TLT",
            "timeframe": "1 Stunde",
            "typ": "Saisonal",
            "beschreibung": (
                "Long-Einstieg im letzten Drittel des Monats (ab Kalendertag 15, "
                "Handelstag 11). Ausstieg am ersten Handelstag des neuen Monats."
            ),
            "regeln": [
                "Einstieg: Kalendertag ≥ 15 und Handelstag ≥ 11",
                "Ausstieg: erster Handelstag des neuen Monats",
                "Long only, 100 % Kapital",
            ],
            "pine_code": "",
            "excel_path": "data/imports/TLT_Season_NASDAQ_TLT_2026-09-24.xlsx",
            "created_at": datetime.now().isoformat(timespec="seconds"),
        },
        {
            "id": str(uuid.uuid4()),
            "name": "SPY RSI Long-Only",
            "symbol": "BATS:SPY",
            "timeframe": "1 Tag",
            "typ": "Mean Reversion",
            "beschreibung": (
                "Long-Einstieg, wenn RSI(3) unter 18 liegt. Ausstieg am nächsten "
                "Handelstag zum Close."
            ),
            "regeln": [
                "Einstieg: RSI(3) < 18",
                "Ausstieg: nächster Handelstag zum Close",
                "Long only, 100 % Kapital",
            ],
            "pine_code": "",
            "excel_path": "data/imports/SPY_RSI_Long-Only_BATS_SPY_2026-09-24.xlsx",
            "created_at": datetime.now().isoformat(timespec="seconds"),
        },
    ]

    save_all(defaults)
    return defaults


# =========================================================
# EXCEL-KENNZAHLEN
# =========================================================

def load_excel_summary(excel_path: str) -> dict:
    """
    Flexibler Parser für Performance-Dateien.

    Liest alle relevanten Sheets:
      - Performance
      - Analyse der Trades
      - Risikogewichtete Performance

    Unterstützt Excel und CSV.
    """

    if not excel_path:
        return {}

    path = Path(excel_path)
    if not path.exists():
        return {}

    try:
        import pandas as pd
    except ImportError:
        return {}

    # =========================================================
    # ALLE SHEETS EINLESEN
    # =========================================================

    frames = {}  # Sheet-Name → DataFrame

    suffix = path.suffix.lower()

    if suffix == ".csv":
        try:
            frames["default"] = pd.read_csv(path)
        except Exception:
            return {}

    else:
        try:
            xls = pd.ExcelFile(path)
            for sheet in xls.sheet_names:
                try:
                    frames[sheet] = pd.read_excel(path, sheet_name=sheet)
                except Exception:
                    continue
        except Exception:
            return {}

    if not frames:
        return {}

    # =========================================================
    # HILFSFUNKTION: KEY/VALUE IN DATAFRAME NORMALISIEREN
    # =========================================================

    def _as_keyvalue(df):
        """Erste Spalte → Index, falls Struktur Key/Value."""
        if df.empty:
            return df
        first = df.columns[0]
        if first == "Unnamed: 0" or not pd.api.types.is_numeric_dtype(df[first]):
            return df.set_index(first)
        return df

    # =========================================================
    # HILFSFUNKTION: KENNZAHL SUCHEN
    # =========================================================

    def _search(keywords, sheets_to_search, prefer_col=None, exclude=None):
        """
        Sucht eine Kennzahl in den angegebenen Sheets.

        keywords: Liste von Substring-Suchbegriffen (case-insensitive)
        sheets_to_search: Liste von Sheet-Namen, in denen gesucht wird
        prefer_col: bevorzugte Spalte (z.B. 'Alle %' oder 'Alle USD')
        exclude: Liste von Begriffen, die NICHT im Namen vorkommen dürfen
        """
        exclude = exclude or []

        for sheet_name in sheets_to_search:
            if sheet_name not in frames:
                continue

            df = _as_keyvalue(frames[sheet_name])

            for idx in df.index:
                idx_lower = str(idx).lower().strip()

                # Ausschluss prüfen
                if any(ex.lower() in idx_lower for ex in exclude):
                    continue

                for kw in keywords:
                    if kw.lower() in idx_lower:
                        # Bevorzugte Spalte zuerst
                        if prefer_col:
                            for col in df.columns:
                                if prefer_col.lower() in str(col).lower():
                                    val = df.loc[idx, col]
                                    if pd.notna(val):
                                        try:
                                            return float(val)
                                        except (ValueError, TypeError):
                                            pass

                        # Fallback: erste numerische Spalte
                        for col in df.columns:
                            val = df.loc[idx, col]
                            if pd.notna(val):
                                try:
                                    return float(val)
                                except (ValueError, TypeError):
                                    continue
        return None

    # =========================================================
    # SHEETS DEFINIEREN
    # =========================================================

    SHEET_PERF = ["Performance"]
    SHEET_TRADES = ["Analyse der Trades", "Trades Analysis", "Trades"]
    SHEET_RISK = ["Risikogewichtete Performance", "Risk-Adjusted Performance", "Risk"]

    # Alle Sheets, in denen wir überhaupt suchen
    ALL_SHEETS = list(frames.keys())

    # =========================================================
    # KENNZAHLEN EXTRAHIEREN
    # =========================================================

    summary = {
        # ---------- Net Profit ----------
        "nettogewinn": _search(
            ["nettogewinn", "net profit", "net p&l", "net pnl"],
            SHEET_PERF + ALL_SHEETS,
            prefer_col="alle usd",
            exclude=["offener", "brutto", "als %"],
        ),

        # ---------- Return % ----------
        "nettogewinn_pct": _search(
            ["kapitalrendite", "total return", "return on capital"],
            SHEET_PERF + ALL_SHEETS,
            prefer_col="alle %",
        ) or _search(
            ["nettogewinn", "net profit"],
            SHEET_PERF + ALL_SHEETS,
            prefer_col="alle %",
            exclude=["offener", "brutto", "als %"],
        ),

        # ---------- CAGR ----------
        "cagr": _search(
            ["annualisierte rendite", "cagr", "compound annual"],
            SHEET_PERF + ALL_SHEETS,
            prefer_col="alle %",
        ),

        # ---------- Max Drawdown (Intraday wie TradingView) ----------
        "max_dd": _search(
            ["max. drawdown (innerhalb balken)"],
            SHEET_PERF + ALL_SHEETS,
            prefer_col="alle %",
            exclude=["als % des startkapitals"],
        ) or _search(
            ["max. drawdown (schlusskurs zu schlusskurs)"],
            SHEET_PERF + ALL_SHEETS,
            prefer_col="alle %",
        ),

        # ---------- Max Drawdown (Close-to-Close, Zusatz) ----------
        "max_dd_close": _search(
            ["max. drawdown (schlusskurs zu schlusskurs)"],
            SHEET_PERF + ALL_SHEETS,
            prefer_col="alle %",
        ),

        # ---------- Trades ----------
        "trades": _search(
            ["trades insgesamt"],
            SHEET_TRADES + ALL_SHEETS,
            exclude=["offene"],
        ),

        # ---------- Win Rate ----------
        "win_rate": _search(
            ["prozentsatz gewinnbringend", "win rate", "percent profitable",
             "gewinnquote"],
            SHEET_TRADES + ALL_SHEETS,
            prefer_col="alle %",
        ),

        # ---------- Profit Factor ----------
        "profit_factor": _search(
            ["profitfaktor", "profit factor"],
            SHEET_RISK + ALL_SHEETS,
        ),

        # ---------- Sharpe ----------
        "sharpe": _search(
            ["sharpe-ratio", "sharpe ratio", "sharpe"],
            SHEET_RISK + ALL_SHEETS,
        ),

        # ---------- Sortino ----------
        "sortino": _search(
            ["sortino-ratio", "sortino ratio", "sortino"],
            SHEET_RISK + ALL_SHEETS,
        ),
    }

    return summary