"""
ml_engine.py
------------
Machine Learning auf Trade-Daten.

Funktionen:
  - Random Forest Training mit chronologischem Split
  - Feature Importance
  - Trade-Predictions
  - K-Means Clustering

Wichtig: Chronologischer Split (nie random), weil Zeitreihen
autokorreliert sind.
"""

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.preprocessing import StandardScaler


# =========================================================
# RANDOM FOREST
# =========================================================

def train_random_forest(
    df: pd.DataFrame,
    feature_cols: list,
    target_col: str = "win",
    test_size: float = 0.3,
    n_estimators: int = 200,
    max_depth: int = 8,
    random_state: int = 42,
) -> dict:
    """
    Trainiert einen Random Forest mit chronologischem Split.

    Rückgabe
    --------
    dict mit:
        model:           trainiertes Modell
        feature_importance: DataFrame (feature, importance)
        metrics:         dict mit AUC, Accuracy, Precision, Recall
        predictions:     DataFrame mit echten + vorhergesagten Werten
        X_train_cols:    Liste der verwendeten Features
    """

    # Nur Zeilen mit vollständigen Features
    valid_cols = [c for c in feature_cols if c in df.columns]
    df_clean = df[valid_cols + [target_col]].dropna().copy()

    if len(df_clean) < 50:
        return {"error": "Zu wenige Trades für ML (min. 50)"}

    X = df_clean[valid_cols].values
    y = df_clean[target_col].values

    # Chronologischer Split
    split_idx = int(len(X) * (1 - test_size))
    X_train, X_test = X[:split_idx], X[split_idx:]
    y_train, y_test = y[:split_idx], y[split_idx:]

    # Modell
    model = RandomForestClassifier(
        n_estimators=n_estimators,
        max_depth=max_depth,
        random_state=random_state,
        n_jobs=-1,
        class_weight="balanced",
    )

    model.fit(X_train, y_train)

    # Predictions
    y_pred = model.predict(X_test)
    y_proba = model.predict_proba(X_test)[:, 1]

    # Metriken
    try:
        auc = roc_auc_score(y_test, y_proba)
    except Exception:
        auc = 0.0

    metrics = {
        "auc": float(auc),
        "accuracy": float(accuracy_score(y_test, y_pred)),
        "precision": float(precision_score(y_test, y_pred, zero_division=0)),
        "recall": float(recall_score(y_test, y_pred, zero_division=0)),
        "n_train": len(X_train),
        "n_test": len(X_test),
        "baseline_win_rate": float(y.mean()),
    }

    # Feature Importance
    importance = pd.DataFrame({
        "feature": valid_cols,
        "importance": model.feature_importances_,
    }).sort_values("importance", ascending=False).reset_index(drop=True)

    # Predictions-Tabelle
    # Wichtig: Original-DataFrame für Kontext-Spalten (einstieg, rendite)
    original_idx = df_clean.index
    predictions = df.loc[original_idx[split_idx:]].copy()
    predictions["prediction"] = y_pred
    predictions["probability"] = y_proba
    predictions["actual"] = y_test

    return {
        "model": model,
        "feature_importance": importance,
        "metrics": metrics,
        "predictions": predictions,
        "feature_cols": valid_cols,
    }


# =========================================================
# K-MEANS CLUSTERING
# =========================================================

def cluster_trades(
    df: pd.DataFrame,
    feature_cols: list,
    n_clusters: int = 3,
    random_state: int = 42,
) -> dict:
    """
    Clustert Trades in n Gruppen.

    Rückgabe
    --------
    dict mit:
        labels:    Cluster-Zuordnung pro Trade
        summary:   DataFrame mit Kennzahlen je Cluster
        df_with_clusters: Original-DF + cluster-Spalte
    """

    valid_cols = [c for c in feature_cols if c in df.columns]
    df_clean = df[valid_cols].dropna().copy()

    if len(df_clean) < n_clusters * 10:
        return {"error": f"Zu wenige Trades (min. {n_clusters * 10})"}

    # Skalieren (K-Means ist distanzbasiert)
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(df_clean.values)

    # K-Means
    kmeans = KMeans(
        n_clusters=n_clusters,
        random_state=random_state,
        n_init=10,
    )
    labels = kmeans.fit_predict(X_scaled)

    # Original-DF + Cluster-Label
    df_with_clusters = df.loc[df_clean.index].copy()
    df_with_clusters["cluster"] = labels

    # Kennzahlen pro Cluster
    summary = df_with_clusters.groupby("cluster").agg(
        n_trades=("win", "count"),
        win_rate=("win", "mean"),
        avg_return=("rendite", "mean"),
        sum_return=("rendite", "sum"),
        avg_hold=("haltetage", "mean"),
    ).reset_index()

    summary["win_rate"] = (summary["win_rate"] * 100).round(2)
    summary["avg_return"] = (summary["avg_return"] * 100).round(3)
    summary["sum_return"] = (summary["sum_return"] * 100).round(2)

    return {
        "labels": labels,
        "summary": summary,
        "df_with_clusters": df_with_clusters,
    }


# =========================================================
# FILTER-VORSCHLÄGE
# =========================================================

def suggest_filters(
    df: pd.DataFrame,
    feature_cols: list,
    target_col: str = "win",
    top_n: int = 10,
) -> pd.DataFrame:
    """
    Schlägt Filter vor basierend auf einfachen Schwellenwerten.

    Für jedes Feature: prüfen ob ein einfacher Cutoff die Win Rate
    signifikant verbessert.

    Rückgabe
    --------
    DataFrame mit Spalten: feature, threshold, direction,
                           n_affected, win_rate_before,
                           win_rate_after, improvement
    """

    valid_cols = [c for c in feature_cols if c in df.columns]
    df_clean = df[valid_cols + [target_col]].dropna().copy()

    if len(df_clean) < 100:
        return pd.DataFrame()

    baseline_wr = df_clean[target_col].mean()
    results = []

    for feat in valid_cols:
        values = df_clean[feat]

        # Drei Quantile testen: 10 %, 25 %, 75 %, 90 %
        for q in [0.1, 0.25, 0.75, 0.9]:
            try:
                threshold = float(values.quantile(q))
            except Exception:
                continue

            # Richtung: unter oder über Schwelle
            for direction in ["above", "below"]:
                if direction == "above":
                    mask = values > threshold
                else:
                    mask = values < threshold

                n_affected = int(mask.sum())
                if n_affected < 30 or n_affected > len(df_clean) - 30:
                    continue

                # Win Rate nach Filter (= nur behalten was NICHT mask ist)
                keep_mask = ~mask
                wr_after = df_clean.loc[keep_mask, target_col].mean()
                improvement = wr_after - baseline_wr

                if improvement > 0.02:  # mind. 2 Prozentpunkte besser
                    results.append({
                        "feature": feat,
                        "direction": direction,
                        "threshold": round(threshold, 4),
                        "n_affected": n_affected,
                        "n_kept": int(keep_mask.sum()),
                        "win_rate_before": round(baseline_wr * 100, 2),
                        "win_rate_after": round(wr_after * 100, 2),
                        "improvement": round(improvement * 100, 2),
                    })

    if not results:
        return pd.DataFrame()

    result_df = pd.DataFrame(results)
    result_df = result_df.sort_values("improvement", ascending=False)
    result_df = result_df.head(top_n).reset_index(drop=True)

    return result_df
