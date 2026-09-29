"""
ml_engine.py
------------
Machine Learning auf Trade-Daten.

Funktionen:
  - Random Forest Training mit chronologischem Split
  - Feature Importance
  - Trade-Predictions
  - K-Means Clustering
  - Permutations-Test

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
    """Trainiert einen Random Forest mit chronologischem Split."""

    valid_cols = [c for c in feature_cols if c in df.columns]
    df_clean = df[valid_cols + [target_col]].dropna().copy()

    if len(df_clean) < 50:
        return {"error": "Zu wenige Trades für ML (min. 50)"}

    X = df_clean[valid_cols].values
    y = df_clean[target_col].values

    split_idx = int(len(X) * (1 - test_size))
    X_train, X_test = X[:split_idx], X[split_idx:]
    y_train, y_test = y[:split_idx], y[split_idx:]

    model = RandomForestClassifier(
        n_estimators=n_estimators,
        max_depth=max_depth,
        random_state=random_state,
        n_jobs=-1,
        class_weight="balanced",
    )

    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    y_proba = model.predict_proba(X_test)[:, 1]

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

    importance = pd.DataFrame({
        "feature": valid_cols,
        "importance": model.feature_importances_,
    }).sort_values("importance", ascending=False).reset_index(drop=True)

    # Predictions aus Original-DataFrame (voller Kontext)
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
    """Clustert Trades in n Gruppen."""

    valid_cols = [c for c in feature_cols if c in df.columns]
    df_clean = df[valid_cols].dropna().copy()

    if len(df_clean) < n_clusters * 10:
        return {"error": f"Zu wenige Trades (min. {n_clusters * 10})"}

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(df_clean.values)

    kmeans = KMeans(
        n_clusters=n_clusters,
        random_state=random_state,
        n_init=10,
    )
    labels = kmeans.fit_predict(X_scaled)

    df_with_clusters = df.loc[df_clean.index].copy()
    df_with_clusters["cluster"] = labels

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
    """Schlägt Filter vor basierend auf einfachen Schwellenwerten."""

    valid_cols = [c for c in feature_cols if c in df.columns]
    df_clean = df[valid_cols + [target_col]].dropna().copy()

    if len(df_clean) < 100:
        return pd.DataFrame()

    baseline_wr = df_clean[target_col].mean()
    results = []

    for feat in valid_cols:
        values = df_clean[feat]

        for q in [0.1, 0.25, 0.75, 0.9]:
            try:
                threshold = float(values.quantile(q))
            except Exception:
                continue

            for direction in ["above", "below"]:
                if direction == "above":
                    mask = values > threshold
                else:
                    mask = values < threshold

                n_affected = int(mask.sum())
                if n_affected < 30 or n_affected > len(df_clean) - 30:
                    continue

                keep_mask = ~mask
                wr_after = df_clean.loc[keep_mask, target_col].mean()
                improvement = wr_after - baseline_wr

                if improvement > 0.02:
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


# =========================================================
# PERMUTATIONS-TEST
# =========================================================

def permutation_test(
    df: pd.DataFrame,
    feature_cols: list,
    target_col: str = "win",
    n_permutations: int = 100,
    test_size: float = 0.3,
    random_state: int = 42,
) -> dict:
    """
    Prüft, ob die echte AUC signifikant besser ist als Zufall.
    """

    valid_cols = [c for c in feature_cols if c in df.columns]
    df_clean = df[valid_cols + [target_col]].dropna().copy()

    if len(df_clean) < 100:
        return {"error": "Zu wenige Trades (min. 100)"}

    X = df_clean[valid_cols].values
    y = df_clean[target_col].values

    split_idx = int(len(X) * (1 - test_size))
    X_train, X_test = X[:split_idx], X[split_idx:]
    y_train, y_test = y[:split_idx], y[split_idx:]

    # Echte AUC
    model = RandomForestClassifier(
        n_estimators=100,
        max_depth=8,
        random_state=random_state,
        n_jobs=-1,
        class_weight="balanced",
    )
    model.fit(X_train, y_train)
    y_proba = model.predict_proba(X_test)[:, 1]

    try:
        real_auc = float(roc_auc_score(y_test, y_proba))
    except Exception:
        real_auc = 0.5

    # Permutationen
    rng = np.random.default_rng(random_state)
    perm_aucs = []

    for i in range(n_permutations):
        y_train_perm = rng.permutation(y_train)

        model_perm = RandomForestClassifier(
            n_estimators=50,
            max_depth=8,
            random_state=int(rng.integers(0, 2**31)),
            n_jobs=-1,
            class_weight="balanced",
        )
        model_perm.fit(X_train, y_train_perm)
        y_proba_perm = model_perm.predict_proba(X_test)[:, 1]

        try:
            auc_perm = float(roc_auc_score(y_test, y_proba_perm))
        except Exception:
            auc_perm = 0.5

        perm_aucs.append(auc_perm)

    perm_aucs = np.array(perm_aucs)

    n_better = int((perm_aucs >= real_auc).sum())
    p_value = (n_better + 1) / (n_permutations + 1)

    percentiles = {
        "5": float(np.percentile(perm_aucs, 5)),
        "25": float(np.percentile(perm_aucs, 25)),
        "50": float(np.percentile(perm_aucs, 50)),
        "75": float(np.percentile(perm_aucs, 75)),
        "95": float(np.percentile(perm_aucs, 95)),
    }

    if p_value < 0.01:
        verdict = "Sehr starkes Signal (p < 0,01)"
    elif p_value < 0.05:
        verdict = "Signifikantes Signal (p < 0,05)"
    elif p_value < 0.10:
        verdict = "Schwaches Signal (p < 0,10)"
    else:
        verdict = "Kein Signal – Zufall nicht ausschließbar"

    return {
        "real_auc": real_auc,
        "perm_aucs": perm_aucs.tolist(),
        "p_value": float(p_value),
        "percentiles": percentiles,
        "verdict": verdict,
        "n_better": n_better,
        "n_permutations": n_permutations,
    }
