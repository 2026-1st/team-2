"""Model training utilities for the surrender prediction dataset."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import GroupShuffleSplit
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

FEATURE_COLUMNS = [
    "gold_diff_15",
    "kill_diff_15",
    "tower_diff_15",
    "dragon_diff_15",
    "rift_herald_diff_15",
    "cs_diff_15",
    "avg_level_diff_15",
    "first_blood",
    "first_tower",
    "ward_placed_diff_15",
    "ward_kill_diff_15",
]
TARGET_COLUMN = "team_surrendered"
GROUP_COLUMN = "match_id"


@dataclass(frozen=True)
class DatasetSplit:
    train_idx: np.ndarray
    valid_idx: np.ndarray
    test_idx: np.ndarray


def validate_modeling_frame(df: pd.DataFrame, group_col: str = GROUP_COLUMN, target_col: str = TARGET_COLUMN) -> None:
    missing = [col for col in [group_col, target_col, *FEATURE_COLUMNS] if col not in df.columns]
    if missing:
        raise ValueError("Dataset is missing required columns: " + ", ".join(missing))
    if df.empty:
        raise ValueError("Dataset is empty")
    if df[group_col].nunique() < 3:
        raise ValueError("At least 3 unique match groups are required for train/valid/test split")
    if df[target_col].nunique() < 2:
        raise ValueError("Target must contain both classes")


def make_group_split(
    df: pd.DataFrame,
    group_col: str = GROUP_COLUMN,
    test_size: float = 0.2,
    valid_size: float = 0.2,
    random_state: int = 42,
) -> DatasetSplit:
    """Split rows by group so a match never appears in more than one split."""
    groups = df[group_col].astype(str).to_numpy()
    all_idx = np.arange(len(df))

    first = GroupShuffleSplit(n_splits=1, test_size=test_size, random_state=random_state)
    train_valid_idx, test_idx = next(first.split(all_idx, groups=groups))

    train_valid_groups = groups[train_valid_idx]
    second = GroupShuffleSplit(n_splits=1, test_size=valid_size, random_state=random_state + 1)
    rel_train_idx, rel_valid_idx = next(second.split(train_valid_idx, groups=train_valid_groups))

    train_idx = train_valid_idx[rel_train_idx]
    valid_idx = train_valid_idx[rel_valid_idx]
    return DatasetSplit(train_idx=train_idx, valid_idx=valid_idx, test_idx=test_idx)


def assert_no_group_leakage(df: pd.DataFrame, split: DatasetSplit, group_col: str = GROUP_COLUMN) -> None:
    train = set(df.iloc[split.train_idx][group_col].astype(str))
    valid = set(df.iloc[split.valid_idx][group_col].astype(str))
    test = set(df.iloc[split.test_idx][group_col].astype(str))
    overlaps = {
        "train_valid": train & valid,
        "train_test": train & test,
        "valid_test": valid & test,
    }
    bad = {name: sorted(values) for name, values in overlaps.items() if values}
    if bad:
        raise ValueError(f"Group leakage detected: {bad}")


def build_models(random_state: int = 42) -> dict[str, Pipeline]:
    numeric_preprocess = ColumnTransformer(
        transformers=[
            ("num", Pipeline([("imputer", SimpleImputer(strategy="median")), ("scaler", StandardScaler())]), FEATURE_COLUMNS),
        ],
        remainder="drop",
    )
    tree_preprocess = ColumnTransformer(
        transformers=[("num", SimpleImputer(strategy="median"), FEATURE_COLUMNS)],
        remainder="drop",
    )
    return {
        "dummy_most_frequent": Pipeline([
            ("preprocess", tree_preprocess),
            ("model", DummyClassifier(strategy="most_frequent")),
        ]),
        "logistic_regression": Pipeline([
            ("preprocess", numeric_preprocess),
            ("model", LogisticRegression(max_iter=2000, class_weight="balanced", random_state=random_state)),
        ]),
        "random_forest": Pipeline([
            ("preprocess", tree_preprocess),
            ("model", RandomForestClassifier(n_estimators=300, class_weight="balanced", min_samples_leaf=2, random_state=random_state)),
        ]),
        "hist_gradient_boosting": Pipeline([
            ("preprocess", tree_preprocess),
            ("model", HistGradientBoostingClassifier(random_state=random_state, max_iter=200)),
        ]),
    }


def _positive_scores(model: Pipeline, x: pd.DataFrame) -> np.ndarray | None:
    if hasattr(model, "predict_proba"):
        proba = model.predict_proba(x)
        if proba.shape[1] >= 2:
            return proba[:, 1]
        return np.zeros(len(x))
    if hasattr(model, "decision_function"):
        scores = model.decision_function(x)
        return np.asarray(scores)
    return None


def evaluate_model(model: Pipeline, x: pd.DataFrame, y_true: pd.Series) -> dict[str, Any]:
    y_pred = model.predict(x)
    y_true_arr = np.asarray(y_true).astype(int)
    y_pred_arr = np.asarray(y_pred).astype(int)
    metrics: dict[str, Any] = {
        "accuracy": float(accuracy_score(y_true_arr, y_pred_arr)),
        "f1": float(f1_score(y_true_arr, y_pred_arr, zero_division=0)),
        "precision": float(precision_score(y_true_arr, y_pred_arr, zero_division=0)),
        "recall": float(recall_score(y_true_arr, y_pred_arr, zero_division=0)),
        "confusion_matrix": confusion_matrix(y_true_arr, y_pred_arr, labels=[0, 1]).tolist(),
    }
    scores = _positive_scores(model, x)
    if scores is not None and len(set(y_true_arr.tolist())) == 2:
        metrics["roc_auc"] = float(roc_auc_score(y_true_arr, scores))
        metrics["pr_auc"] = float(average_precision_score(y_true_arr, scores))
    else:
        metrics["roc_auc"] = None
        metrics["pr_auc"] = None
    return metrics


def train_models(
    df: pd.DataFrame,
    group_col: str = GROUP_COLUMN,
    target_col: str = TARGET_COLUMN,
    random_state: int = 42,
) -> tuple[dict[str, Pipeline], dict[str, Any]]:
    validate_modeling_frame(df, group_col=group_col, target_col=target_col)
    split = make_group_split(df, group_col=group_col, random_state=random_state)
    assert_no_group_leakage(df, split, group_col=group_col)

    y = df[target_col].astype(bool).astype(int)
    x = df[FEATURE_COLUMNS]
    models = build_models(random_state=random_state)

    results: dict[str, Any] = {
        "row_count": int(len(df)),
        "group_count": int(df[group_col].nunique()),
        "positive_rate": float(y.mean()),
        "feature_columns": FEATURE_COLUMNS,
        "split": {
            "train_rows": int(len(split.train_idx)),
            "valid_rows": int(len(split.valid_idx)),
            "test_rows": int(len(split.test_idx)),
            "train_groups": int(df.iloc[split.train_idx][group_col].nunique()),
            "valid_groups": int(df.iloc[split.valid_idx][group_col].nunique()),
            "test_groups": int(df.iloc[split.test_idx][group_col].nunique()),
        },
        "models": {},
    }

    fitted: dict[str, Pipeline] = {}
    for name, model in models.items():
        model.fit(x.iloc[split.train_idx], y.iloc[split.train_idx])
        fitted[name] = model
        results["models"][name] = {
            "valid": evaluate_model(model, x.iloc[split.valid_idx], y.iloc[split.valid_idx]),
            "test": evaluate_model(model, x.iloc[split.test_idx], y.iloc[split.test_idx]),
        }
    return fitted, results
