"""
data_loader.py
--------------
Lädt Trading-Daten aus CSV- und Excel-Dateien und gibt einen
sauberen Pandas DataFrame zurück.
"""

from pathlib import Path
from typing import Union, IO

import pandas as pd


# =========================================================
# UNTERSTÜTZTE DATEIFORMATE
# =========================================================

CSV_EXTENSIONS = {".csv"}
EXCEL_EXTENSIONS = {".xlsx", ".xls"}


# =========================================================
# HILFSFUNKTION: DATEIENDUNG ERMITTELN
# =========================================================

def _get_extension(source: Union[str, Path, IO]) -> str:
    """
    Ermittelt die Dateiendung einer Quelle.

    - Bei einem Pfad (str/Path): Endung aus dem Dateinamen.
    - Bei einem Datei-Objekt (z.B. Streamlit UploadedFile):
      Endung aus dem .name-Attribut.
    """
    if isinstance(source, (str, Path)):
        return Path(source).suffix.lower()

    # Streamlit UploadedFile oder ähnliche Objekte
    name = getattr(source, "name", "")
    return Path(name).suffix.lower()


# =========================================================
# HAUPTFUNKTION: DATEN LADEN
# =========================================================

def load_trading_data(source: Union[str, Path, IO]) -> pd.DataFrame:
    """
    Lädt Trading-Daten aus einer CSV- oder Excel-Datei.

    Parameter
    ---------
    source : str | Path | IO
        - Pfad zur Datei (z.B. "data/imports/trades.csv")
        - ODER ein Datei-Objekt (z.B. st.file_uploader)

    Rückgabe
    --------
    pd.DataFrame
        Die geladenen Trading-Daten als DataFrame.

    Fehler
    ------
    ValueError
        Wenn die Dateiendung nicht unterstützt wird.
    FileNotFoundError
        Wenn der angegebene Pfad nicht existiert.
    """

    extension = _get_extension(source)

    # ---------- CSV ----------
    if extension in CSV_EXTENSIONS:
        df = pd.read_csv(source)
        return df

    # ---------- EXCEL ----------
    if extension in EXCEL_EXTENSIONS:
        df = pd.read_excel(source)
        return df

    # ---------- UNBEKANNT ----------
    raise ValueError(
        f"Nicht unterstütztes Dateiformat: '{extension}'. "
        f"Erlaubt: {CSV_EXTENSIONS | EXCEL_EXTENSIONS}"
    )


# =========================================================
# SHEET-NAMEN (Quantitativo/TradingView Excel)
# =========================================================

SHEET_TRADES = "Handelsgeschäfte"
SHEET_PERFORMANCE = "Performance"
SHEET_PROPERTIES = "Eigenschaften"
SHEET_ANALYSIS = "Analyse der Trades"
SHEET_RISK = "Risikogewichtete Performance"


# =========================================================
# TRADES LADEN (nur Ausstiegs-Zeilen mit finalem P&L)
# =========================================================

def load_trades(source: Union[str, Path, IO]) -> pd.DataFrame:
    """
    Lädt die einzelnen Trades aus dem Sheet 'Handelsgeschäfte'.

    Jeder Trade erscheint im Sheet zweimal:
      - Einstiegs-Zeile (Typ: 'Long-Einstieg' / 'Short-Einstieg')
      - Ausstiegs-Zeile (Typ: 'Long-Ausstieg' / 'Short-Ausstieg')

    Nur die **Ausstiegs-Zeilen** enthalten den finalen P&L –
    diese Funktion gibt ausschließlich die Ausstiegs-Zeilen zurück.
    """

    df = pd.read_excel(source, sheet_name=SHEET_TRADES)

    # Nur Ausstiegs-Zeilen behalten
    exit_mask = df["Typ"].str.contains("Ausstieg", na=False)
    df = df[exit_mask].copy()

    # Nach Trade-Nummer sortieren
    df = df.sort_values("Trade-Nummer").reset_index(drop=True)

    return df


# =========================================================
# PERFORMANCE LADEN (Kennzahlen-Tabelle)
# =========================================================

def load_performance(source: Union[str, Path, IO]) -> pd.DataFrame:
    """
    Lädt das Sheet 'Performance' mit den Kennzahlen.

    Spalte A enthält den Namen der Kennzahl, die weiteren
    Spalten die Werte (Alle USD, Alle %, Long USD, ...).
    """

    df = pd.read_excel(source, sheet_name=SHEET_PERFORMANCE)

    # Erste Spalte als Index setzen (Kennzahl-Name)
    first_col = df.columns[0]
    df = df.set_index(first_col)
    df.index.name = "Kennzahl"

    return df


# =========================================================
# PROPERTIES LADEN (Backtest-Einstellungen)
# =========================================================

def load_properties(source: Union[str, Path, IO]) -> pd.DataFrame:
    """
    Lädt das Sheet 'Eigenschaften' mit den Backtest-Einstellungen.
    """

    df = pd.read_excel(source, sheet_name=SHEET_PROPERTIES)
    return df


# =========================================================
# ANALYSE-TRADES LADEN
# =========================================================

def load_trade_analysis(source: Union[str, Path, IO]) -> pd.DataFrame:
    """
    Lädt das Sheet 'Analyse der Trades' (Win Rate, Avg Win/Loss, ...).
    """

    df = pd.read_excel(source, sheet_name=SHEET_ANALYSIS)

    first_col = df.columns[0]
    df = df.set_index(first_col)
    df.index.name = "Kennzahl"

    return df


# =========================================================
# RISIKO-KENNZAHLEN LADEN
# =========================================================

def load_risk_metrics(source: Union[str, Path, IO]) -> pd.DataFrame:
    """
    Lädt das Sheet 'Risikogewichtete Performance'
    (Sharpe, Sortino, Profit Factor, Margin Calls).
    """

    df = pd.read_excel(source, sheet_name=SHEET_RISK)

    first_col = df.columns[0]
    df = df.set_index(first_col)
    df.index.name = "Kennzahl"

    return df
