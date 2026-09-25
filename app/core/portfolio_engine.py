"""
portfolio_engine.py
-------------------
Kombiniert mehrere Strategien zu einem Portfolio.

Jede Strategie ist ein Trade-Level-DataFrame (siehe load_trades).
Die Kombination erfolgt über die kumulierten Renditen (Equal Weight).
"""

import pandas as pd


# =========================================================
# KONSTANTEN
# =========================================================

COL_DATE = "Datum und Uhrzeit"
COL_EQUITY = "Kumulierter G&V %"


# =========================================================
# EQUITY-MATRIX BAUEN
# =========================================================

def build_equity_matrix(strategies: dict) -> pd.DataFrame:
    """
    Baut eine Matrix mit:
        Index   = Datum (Tagesbasis)
        Spalten = Strategie-Namen
        Werte   = Kumulierter G&V % (forward-filled)

    Parameter
    ---------
    strategies : dict
        { "Strategie A": DataFrame, "Strategie B": DataFrame, ... }

    Rückgabe
    --------
    pd.DataFrame
    """

    series_list = []

    for name, df in strategies.items():

        if COL_DATE not in df.columns or COL_EQUITY not in df.columns:
            continue

        s = df[[COL_DATE, COL_EQUITY]].copy()
        s = s.set_index(COL_DATE)

        s.index = pd.to_datetime(s.index, errors="coerce")
        s = s[s.index.notna()]

        s = s.sort_index()
        s = s.rename(columns={COL_EQUITY: name})

        series_list.append(s)

    if not series_list:
        return pd.DataFrame()

    matrix = pd.concat(series_list, axis=1)

    # Auf Tagesbasis und forward-fill (Strategien handeln nicht jeden Tag)
    matrix = matrix.resample("D").last()
    matrix = matrix.ffill().fillna(0)

    return matrix


# =========================================================
# KOMBINIERTE EQUITY (EQUAL WEIGHT)
# =========================================================

def combine_equity(strategies: dict) -> pd.Series:
    """
    Kombinierte Portfolio-Equity als durchschnittliche Rendite
    aller Strategien (Equal Weight).

    Rückgabe
    --------
    pd.Series mit Index = Datum, Werte = kombinierte Rendite in %
    """

    matrix = build_equity_matrix(strategies)

    if matrix.empty:
        return pd.Series(dtype=float)

    # Equal Weight: jede Strategie zählt 1/n
    combined = matrix.mean(axis=1)
    combined.name = "Portfolio %"

    return combined


# =========================================================
# PORTFOLIO-KENNZAHLEN
# =========================================================

def analyze_portfolio(strategies: dict) -> dict:
    """
    Aggregiert die wichtigsten Kennzahlen über alle Strategien.

    Rückgabe
    --------
    dict mit:
        total_strategies     Anzahl Strategien
        total_trades         Gesamtzahl Trades
        total_winners        Gesamtzahl Gewinner
        total_losers         Gesamtzahl Verlierer
        overall_win_rate     Win Rate über alle Trades
        total_net_profit     Summe der Netto-Gewinne
        by_strategy          dict: je Strategie { net_profit, win_rate, ... }
    """

    total_trades = 0
    total_winners = 0
    total_losers = 0
    total_net_profit = 0.0
    by_strategy = {}

    for name, df in strategies.items():

        if df is None or df.empty:
            continue

        pnl = df["Netto G&V USD"]

        winners = int((pnl > 0).sum())
        losers = int((pnl < 0).sum())
        net = float(pnl.sum())

        total_trades += len(df)
        total_winners += winners
        total_losers += losers
        total_net_profit += net

        by_strategy[name] = {
            "total_trades": len(df),
            "winners": winners,
            "losers": losers,
            "net_profit": net,
            "win_rate": (winners / len(df) * 100) if len(df) else 0.0,
        }

    overall_win_rate = (
        (total_winners / total_trades * 100) if total_trades else 0.0
    )

    return {
        "total_strategies": len(strategies),
        "total_trades": total_trades,
        "total_winners": total_winners,
        "total_losers": total_losers,
        "overall_win_rate": overall_win_rate,
        "total_net_profit": total_net_profit,
        "by_strategy": by_strategy,
    }



# =========================================================
# KORRELATIONS-MATRIX
# =========================================================

def correlation_matrix(strategies: dict, freq: str = "ME") -> pd.DataFrame:
    """
    Berechnet die Korrelation zwischen den Strategien.

    Parameter
    ---------
    freq : str
        "D"  = täglich
        "W"  = wöchentlich
        "ME" = monatlich (Monatsende, Standard)
    """

    matrix = build_equity_matrix(strategies)

    if matrix.empty or matrix.shape[1] < 2:
        return pd.DataFrame()

    # Auf gewünschte Frequenz bringen und Differenzen berechnen
    resampled = matrix.resample(freq).last().diff().dropna()

    if resampled.empty:
        return pd.DataFrame()

    return resampled.corr()


# =========================================================
# GEWICHTETE EQUITY
# =========================================================

def combine_equity_weighted(strategies: dict, weights: dict) -> pd.Series:
    """
    Kombinierte Equity mit benutzerdefinierten Gewichten.

    Parameter
    ---------
    weights : dict
        { "Strategie A": 0.5, "Strategie B": 0.3, ... }
        Summe sollte 1.0 sein.
    """

    matrix = build_equity_matrix(strategies)

    if matrix.empty:
        return pd.Series(dtype=float)

    # Nur Strategien berücksichtigen, die in weights stehen
    cols = [c for c in matrix.columns if c in weights]

    if not cols:
        return pd.Series(dtype=float)

    weighted = matrix[cols].mul(
        pd.Series(weights), axis=1
    )

    combined = weighted.sum(axis=1)
    combined.name = "Portfolio (gewichtet) %"

    return combined



# =========================================================
# ASSET-SYMBOL AUS STRATEGIE-NAMEN EXTRAHIEREN
# =========================================================

# Börsen-Präfixe, die wir ignorieren
_EXCHANGE_PREFIXES = {
    "NASDAQ", "NYSE", "AMEX", "BATS", "ARCA", "CBOE", "TSX", "LSE",
    "XETRA", "FWB", "EURONEXT", "TSE", "HKEX",
}


def extract_symbol(strategy_name: str) -> str:
    """
    Versucht, aus einem Strategie-Namen ein Ticker-Symbol zu extrahieren.

    Beispiel:
        "TurnTue_NASDAQ_QQQ_2026-09-24"          → "QQQ"
        "TLT_Season_NASDAQ_TLT_2026-09-24"       → "TLT"
        "SPY_RSI_Long-Only_BATS_SPY_2026-09-24"  → "SPY"

    Fallback: der Strategie-Name selbst, falls nichts erkannt wird.
    """

    import re

    tokens = re.split(r"[_\-\s]+", strategy_name)

    candidates = [
        t for t in tokens
        if 2 <= len(t) <= 5
        and t.isalpha()
        and t.isupper()
        and t not in _EXCHANGE_PREFIXES
    ]

    if not candidates:
        return strategy_name

    return candidates[-1]


# =========================================================
# ASSET-KORRELATION (Preise der gehandelten Assets)
# =========================================================

def asset_correlation_matrix(strategies: dict, period: str = "2y") -> pd.DataFrame:
    """
    Korrelation der täglichen Renditen der gehandelten Assets.

    Beispiel: QQQ-Preis vs. TLT-Preis.

    Parameter
    ---------
    strategies : dict
        { "Strategie A": DataFrame, ... }
    period : str
        Zeitraum für yfinance: "1y", "2y", "5y", "max"

    Rückgabe
    --------
    pd.DataFrame : Korrelationsmatrix der Assets, oder leeres DF wenn
                   weniger als 2 Assets erkannt wurden.
    """

    import yfinance as yf

    # Symbole aus Strategie-Namen extrahieren
    symbols = {}
    for name in strategies.keys():
        sym = extract_symbol(name)
        symbols[name] = sym

    unique_symbols = sorted(set(symbols.values()))

    if len(unique_symbols) < 2:
        return pd.DataFrame()

    # Preisdaten von Yahoo holen
    try:
        data = yf.download(
            unique_symbols,
            period=period,
            interval="1d",
            progress=False,
            auto_adjust=True,
            threads=False,
        )
    except Exception:
        return pd.DataFrame()

    if data is None or data.empty:
        return pd.DataFrame()

    # 'Close'-Spalte extrahieren
    if isinstance(data.columns, pd.MultiIndex):
        prices = data["Close"]
    else:
        prices = data[["Close"]]

    # Tägliche Renditen (nicht die Preise selbst!)
    returns = prices.pct_change().dropna()

    if returns.empty or returns.shape[1] < 2:
        return pd.DataFrame()

    corr = returns.corr()
    corr.index.name = "Asset"
    corr.columns.name = "Asset"

    return corr



# =========================================================
# SYMBOL-NORMALISIERUNG (Yahoo Finance Format)
# =========================================================

# Gängige Währungscodes für Forex-Erkennung
_CURRENCIES = {
    "EUR", "USD", "GBP", "JPY", "CHF", "AUD", "CAD", "NZD",
    "SEK", "NOK", "DKK", "PLN", "CZK", "HUF", "MXN", "TRY",
    "ZAR", "SGD", "HKD", "CNY",
}


def normalize_symbol(symbol: str) -> str:
    """
    Bringt ein Nutzer-eingegebenes Symbol ins Yahoo-Finance-Format.

    Beispiele:
        "EURUSD"    → "EURUSD=X"
        "eur/usd"   → "EURUSD=X"
        "AAPL"      → "AAPL"
        "BTC-USD"   → "BTC-USD"
        "^GDAXI"    → "^GDAXI"
    """

    s = symbol.strip().upper().replace("/", "").replace(" ", "")

    if not s:
        return ""

    # Schon im Yahoo-Format?
    if "=" in s or "-" in s or s.startswith("^"):
        return s

    # Forex-Pair? (6 Buchstaben, beide Hälften Währungen)
    if len(s) == 6 and s.isalpha():
        base, quote = s[:3], s[3:]
        if base in _CURRENCIES and quote in _CURRENCIES:
            return f"{s}=X"

    return s


# =========================================================
# KORRELATION FREI WÄHLBARER SYMBOLE
# =========================================================

def custom_asset_correlation(symbols: list, period: str = "2y") -> pd.DataFrame:
    """
    Korrelation zwischen frei gewählten Symbolen (Yahoo Finance).

    Parameter
    ---------
    symbols : list[str]
        Bereits normalisierte Symbole (z. B. ["EURUSD=X", "AAPL"])
    period : str
        "1y", "2y", "5y", "max"

    Rückgabe
    --------
    pd.DataFrame : Korrelationsmatrix, oder leeres DF bei Fehler
    """

    import yfinance as yf

    if not symbols or len(symbols) < 2:
        return pd.DataFrame()

    try:
        data = yf.download(
            symbols,
            period=period,
            interval="1d",
            progress=False,
            auto_adjust=True,
            threads=False,
        )
    except Exception:
        return pd.DataFrame()

    if data is None or data.empty:
        return pd.DataFrame()

    # Close-Preise extrahieren
    if isinstance(data.columns, pd.MultiIndex):
        prices = data["Close"]
    else:
        prices = data[["Close"]]

    # Falls Spalten fehlen (Symbol nicht gefunden)
    valid_cols = [c for c in prices.columns if not prices[c].isna().all()]
    if len(valid_cols) < 2:
        return pd.DataFrame()

    prices = prices[valid_cols]

    returns = prices.pct_change().dropna()
    if returns.empty:
        return pd.DataFrame()

    corr = returns.corr()
    corr.index.name = "Symbol"
    corr.columns.name = "Symbol"

    return corr