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
