#!/usr/bin/env python3
"""Generate versioned Jupyter notebooks for non-git analysis iteration."""
from __future__ import annotations

import json
import textwrap
from datetime import datetime
from pathlib import Path

import nbformat as nbf

ROOT = Path(__file__).resolve().parents[1]
NOTEBOOK_DIR = ROOT / "notebooks"
VERSION_DIR = NOTEBOOK_DIR / "versions"
RUN_ID = "riot-scale-2600"

COMMON_SETUP = r'''
from pathlib import Path
import json
import os
import sys

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import joblib

ROOT = next(
    path for path in [Path.cwd(), *Path.cwd().parents]
    if (path / 'src' / 'team2_surrender').exists()
)
os.chdir(ROOT)
SRC = ROOT / 'src'
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from IPython.display import display, Markdown, Image
from sklearn.metrics import f1_score, precision_score, recall_score, confusion_matrix
from team2_surrender.modeling import FEATURE_COLUMNS, TARGET_COLUMN, GROUP_COLUMN, make_group_split

RUN_ID = 'riot-scale-2600'
DATA_PATH = ROOT / 'data' / 'processed' / 'riot' / f'{RUN_ID}_team_features.csv'
VALIDATION_PATH = ROOT / 'data' / 'processed' / 'riot' / f'{RUN_ID}_team_features_validation_strict.json'
METRICS_PATH = ROOT / 'outputs' / 'metrics' / f'{RUN_ID}_model_comparison.json'
FIGURE_DIR = ROOT / 'reports' / 'figures' / RUN_ID
MODEL_DIR = ROOT / 'models' / RUN_ID
UPLOAD_VERIFICATION_PATH = ROOT / 'outputs' / 'verification' / f'supabase_upload_{RUN_ID}.json'

REQUIRED_PATHS = [DATA_PATH, VALIDATION_PATH, METRICS_PATH, FIGURE_DIR, MODEL_DIR, UPLOAD_VERIFICATION_PATH]

for path in REQUIRED_PATHS:
    print(f'{path.relative_to(ROOT)} -> {path.exists()}')

missing_paths = [path for path in REQUIRED_PATHS if not path.exists()]
if missing_paths:
    missing_text = '\n'.join(str(path.relative_to(ROOT)) for path in missing_paths)
    raise FileNotFoundError(
        'Missing required analysis artifacts:\n'
        f'{missing_text}\n\n'
        'Run: python scripts/prepare_jupyter_analysis_artifacts.py'
    )
'''.strip()

LOAD_DF = r'''
df = pd.read_csv(DATA_PATH)
y = df[TARGET_COLUMN].astype(bool).astype(int)
print('rows:', len(df))
print('matches:', df[GROUP_COLUMN].nunique())
print('positive rows:', int(y.sum()))
print('positive rate:', round(float(y.mean()), 4))
display(df.head())
'''.strip()


def md(text: str):
    return nbf.v4.new_markdown_cell(textwrap.dedent(text).strip())


def code(text: str):
    return nbf.v4.new_code_cell(text.strip())


def notebook(cells):
    nb = nbf.v4.new_notebook()
    nb["metadata"] = {
        "kernelspec": {"display_name": "Team2 Surrender (.venv)", "language": "python", "name": "team2-surrender"},
        "language_info": {"name": "python", "pygments_lexer": "ipython3"},
    }
    nb["cells"] = cells
    return nb


def write_nb(name: str, cells):
    VERSION_DIR.mkdir(parents=True, exist_ok=True)
    path = VERSION_DIR / name
    nbf.write(notebook(cells), path)
    return path


def main() -> int:
    created = []

    created.append(write_nb(
        "v01_data_validation_riot_scale_2600.ipynb",
        [
            md("""
            # v01 — Data Validation Snapshot

            범위: `riot-scale-2600` 데이터 규모와 strict validation 결과.
            """),
            code(COMMON_SETUP),
            md("## 1. 데이터 로드"),
            code(LOAD_DF),
            md("## 2. Dataset summary"),
            code(r'''
summary = pd.DataFrame({
    'metric': [
        'team_rows', 'unique_matches', 'positive_rows', 'negative_rows', 'positive_rate',
        'min_duration_sec', 'median_duration_sec', 'max_duration_sec', 'queue_ids'
    ],
    'value': [
        len(df),
        df[GROUP_COLUMN].nunique(),
        int(y.sum()),
        int((1 - y).sum()),
        round(float(y.mean()), 4),
        int(df['game_duration_sec'].min()),
        int(df['game_duration_sec'].median()),
        int(df['game_duration_sec'].max()),
        ', '.join(map(str, sorted(df['queue_id'].unique()))),
    ]
})
display(summary)
            '''),
            md("## 3. Strict validation checks"),
            code(r'''
validation = json.loads(VALIDATION_PATH.read_text())
checks = validation.get('checks', validation)
rows = []
if isinstance(checks, dict):
    for name, value in checks.items():
        if isinstance(value, dict):
            rows.append({'check': name, 'status': value.get('status') or value.get('result'), 'message': value.get('message') or value.get('detail') or ''})
        else:
            rows.append({'check': name, 'status': value, 'message': ''})
else:
    rows = checks
validation_df = pd.DataFrame(rows)
display(validation_df)
            '''),
            md("## 4. Upload row count check"),
            code(r'''
upload = json.loads(UPLOAD_VERIFICATION_PATH.read_text())
display(pd.DataFrame([upload]))
            '''),
            md("## v01 notes\n\n- 데이터셋 규모: 2,525 matches / 5,050 team rows.\n- match별 2개 team row, queue 420, 15분 이상 경기 조건, positive label 제약 통과."),
        ],
    ))

    created.append(write_nb(
        "v02_eda_feature_interpretation_riot_scale_2600.ipynb",
        [
            md("""
            # v02 — EDA & Feature Interpretation

            범위: 항복 패배 label과 15분 feature의 관계.
            """),
            code(COMMON_SETUP),
            code(LOAD_DF),
            md("## 1. Label distribution"),
            code(r'''
label_counts = y.value_counts().sort_index()
label_counts.index = ['negative', 'positive']
display(label_counts.to_frame('team_rows'))
fig, ax = plt.subplots(figsize=(5, 3))
label_counts.plot(kind='bar', ax=ax, color=['#4e79a7', '#e15759'])
ax.set_title('Team surrender label distribution')
ax.set_xlabel('label')
ax.set_ylabel('team rows')
ax.bar_label(ax.containers[0])
plt.tight_layout()
plt.show()
            '''),
            md("## 2. Positive vs Negative feature means"),
            code(r'''
class_means = df.groupby(y)[FEATURE_COLUMNS].mean().T
class_means.columns = ['negative_mean', 'positive_mean']
class_means['positive_minus_negative'] = class_means['positive_mean'] - class_means['negative_mean']
display(class_means.sort_values('positive_minus_negative'))

plot_df = class_means['positive_minus_negative'].sort_values()
fig, ax = plt.subplots(figsize=(8, 5))
plot_df.plot(kind='barh', ax=ax, color=['#e15759' if v < 0 else '#59a14f' for v in plot_df])
ax.axvline(0, color='black', linewidth=1)
ax.set_title('Positive - Negative mean difference')
ax.set_xlabel('mean difference')
plt.tight_layout()
plt.show()
            '''),
            md("## 3. Surrender rate by gold/kill buckets"),
            code(r'''
for feature, bins in {
    'gold_diff_15': [-20000, -8000, -5000, -3000, -1000, 0, 1000, 3000, 5000, 8000, 20000],
    'kill_diff_15': [-50, -15, -10, -5, -2, 0, 2, 5, 10, 15, 50],
}.items():
    tmp = df.copy()
    tmp[f'{feature}_bucket'] = pd.cut(tmp[feature], bins=bins, include_lowest=True)
    rate = tmp.groupby(f'{feature}_bucket', observed=False)[TARGET_COLUMN].mean().reset_index()
    display(rate)
    fig, ax = plt.subplots(figsize=(9, 3.5))
    ax.plot(range(len(rate)), rate[TARGET_COLUMN], marker='o')
    ax.set_xticks(range(len(rate)))
    ax.set_xticklabels(rate[f'{feature}_bucket'].astype(str), rotation=45, ha='right')
    ax.set_title(f'Surrender positive rate by {feature} bucket')
    ax.set_ylabel('positive rate')
    ax.set_ylim(0, max(0.5, float(rate[TARGET_COLUMN].max()) + 0.05))
    plt.tight_layout()
    plt.show()
            '''),
            md("## 4. Existing pipeline EDA figures"),
            code(r'''
figure_paths = sorted(FIGURE_DIR.glob('*.png'))
print('figure count:', len(figure_paths))
for path in figure_paths:
    display(Markdown(f'### {path.name}'))
    display(Image(filename=str(path)))
            '''),
            md("## v02 notes\n\n- Positive team은 평균적으로 15분 지표에서 더 불리함.\n- gold/kill/cs/tower/dragon 격차가 label 차이를 크게 설명함."),
        ],
    ))

    created.append(write_nb(
        "v03_modeling_threshold_riot_scale_2600.ipynb",
        [
            md("""
            # v03 — Modeling, Feature Importance & Threshold Tuning

            범위: baseline 모델 비교, feature importance, threshold tuning.
            """),
            code(COMMON_SETUP),
            code(LOAD_DF),
            md("## 1. Model comparison"),
            code(r'''
metrics = json.loads(METRICS_PATH.read_text())
rows = []
for model_name, splits in metrics['models'].items():
    for split_name, vals in splits.items():
        row = {'model': model_name, 'split': split_name}
        for col in ['accuracy', 'f1', 'precision', 'recall', 'roc_auc', 'pr_auc']:
            row[col] = vals[col]
        rows.append(row)
metrics_df = pd.DataFrame(rows)
display(metrics_df.sort_values(['split', 'roc_auc'], ascending=[True, False]))

test_metrics = metrics_df[metrics_df['split'] == 'test'].set_index('model')
display(test_metrics.sort_values('roc_auc', ascending=False))
            '''),
            md("## 2. Test metric plot"),
            code(r'''
plot_cols = ['roc_auc', 'pr_auc', 'f1', 'recall', 'precision']
fig, axes = plt.subplots(1, len(plot_cols), figsize=(18, 3.8))
for ax, col in zip(axes, plot_cols):
    test_metrics[col].sort_values().plot(kind='barh', ax=ax, color='#4e79a7')
    ax.set_title(col)
    ax.set_xlim(0, 1)
plt.suptitle('Test metric comparison')
plt.tight_layout()
plt.show()
            '''),
            md("## 3. Feature importance"),
            code(r'''
logistic = joblib.load(MODEL_DIR / 'logistic_regression.joblib')
rf = joblib.load(MODEL_DIR / 'random_forest.joblib')

coef_df = pd.DataFrame({'feature': FEATURE_COLUMNS, 'logistic_coef': logistic.named_steps['model'].coef_[0]})
coef_df['abs_coef'] = coef_df['logistic_coef'].abs()
display(coef_df.sort_values('abs_coef', ascending=False))

rf_df = pd.DataFrame({'feature': FEATURE_COLUMNS, 'rf_importance': rf.named_steps['model'].feature_importances_})
display(rf_df.sort_values('rf_importance', ascending=False))

fig, axes = plt.subplots(1, 2, figsize=(14, 5))
coef_df.sort_values('logistic_coef').plot(x='feature', y='logistic_coef', kind='barh', ax=axes[0], legend=False, color='#e15759')
axes[0].axvline(0, color='black', linewidth=1)
axes[0].set_title('Logistic coefficients')
rf_df.sort_values('rf_importance').plot(x='feature', y='rf_importance', kind='barh', ax=axes[1], legend=False, color='#4e79a7')
axes[1].set_title('Random Forest importance')
plt.tight_layout()
plt.show()
            '''),
            md("## 4. Logistic threshold tuning"),
            code(r'''
split = make_group_split(df, group_col=GROUP_COLUMN, random_state=42)
X = df[FEATURE_COLUMNS]
valid_idx = split.valid_idx
test_idx = split.test_idx
valid_scores = logistic.predict_proba(X.iloc[valid_idx])[:, 1]
test_scores = logistic.predict_proba(X.iloc[test_idx])[:, 1]

threshold_rows = []
for thr in np.linspace(0.05, 0.95, 91):
    pred = (valid_scores >= thr).astype(int)
    threshold_rows.append({
        'threshold': thr,
        'valid_f1': f1_score(y.iloc[valid_idx], pred, zero_division=0),
        'valid_precision': precision_score(y.iloc[valid_idx], pred, zero_division=0),
        'valid_recall': recall_score(y.iloc[valid_idx], pred, zero_division=0),
    })
threshold_df = pd.DataFrame(threshold_rows)
best = threshold_df.sort_values('valid_f1', ascending=False).iloc[0]
display(threshold_df.sort_values('valid_f1', ascending=False).head(10))

test_pred = (test_scores >= best['threshold']).astype(int)
tuned = pd.DataFrame([{
    'selected_threshold': float(best['threshold']),
    'test_f1': f1_score(y.iloc[test_idx], test_pred, zero_division=0),
    'test_precision': precision_score(y.iloc[test_idx], test_pred, zero_division=0),
    'test_recall': recall_score(y.iloc[test_idx], test_pred, zero_division=0),
    'test_confusion_matrix': confusion_matrix(y.iloc[test_idx], test_pred, labels=[0, 1]).tolist(),
}])
display(tuned)

fig, ax = plt.subplots(figsize=(7, 4))
threshold_df.plot(x='threshold', y=['valid_f1', 'valid_precision', 'valid_recall'], ax=ax)
ax.axvline(best['threshold'], color='black', linestyle='--', linewidth=1)
ax.set_title('Validation threshold tuning')
ax.set_ylim(0, 1)
plt.tight_layout()
plt.show()
            '''),
            md("## v03 notes\n\n- Test ROC-AUC 기준 Logistic Regression이 가장 높음.\n- class imbalance가 있어 threshold 0.5와 tuned threshold를 함께 기록함."),
        ],
    ))

    created.append(write_nb(
        "v04_submission_report_riot_scale_2600.ipynb",
        [
            md("""
            # v04 — Report Summary

            범위: v01~v03 핵심 수치와 해석 요약.
            """),
            code(COMMON_SETUP),
            code(LOAD_DF),
            md("## 1. Problem definition\n\nRiot Ranked Solo/Duo 경기에서 15분 시점 팀 상태를 이용해, 해당 팀이 항복으로 패배할 위험을 예측함. 분석 단위는 participant가 아니라 **team-level row**임."),
            md("## 2. Data and validation summary"),
            code(r'''
validation = json.loads(VALIDATION_PATH.read_text())
upload = json.loads(UPLOAD_VERIFICATION_PATH.read_text())
report_summary = pd.DataFrame({
    'item': ['run_id', 'matches', 'team_rows', 'positive_rows', 'positive_rate', 'supabase_upload_status'],
    'value': [
        RUN_ID,
        df[GROUP_COLUMN].nunique(),
        len(df),
        int(y.sum()),
        round(float(y.mean()), 4),
        upload.get('status'),
    ]
})
display(report_summary)
            '''),
            md("## 3. Core EDA finding"),
            code(r'''
class_means = df.groupby(y)[FEATURE_COLUMNS].mean().T
class_means.columns = ['negative_mean', 'positive_mean']
class_means['positive_minus_negative'] = class_means['positive_mean'] - class_means['negative_mean']
top_directional = class_means.reindex(class_means['positive_minus_negative'].abs().sort_values(ascending=False).index).head(8)
display(top_directional)

fig, ax = plt.subplots(figsize=(8, 4.5))
top_directional.sort_values('positive_minus_negative')['positive_minus_negative'].plot(kind='barh', ax=ax, color='#e15759')
ax.axvline(0, color='black', linewidth=1)
ax.set_title('Top feature mean differences: positive - negative')
plt.tight_layout()
plt.show()
            '''),
            md("## 4. Model result summary"),
            code(r'''
metrics = json.loads(METRICS_PATH.read_text())
rows = []
for model_name, splits in metrics['models'].items():
    vals = splits['test']
    rows.append({
        'model': model_name,
        'accuracy': vals['accuracy'],
        'f1': vals['f1'],
        'precision': vals['precision'],
        'recall': vals['recall'],
        'roc_auc': vals['roc_auc'],
        'pr_auc': vals['pr_auc'],
    })
model_summary = pd.DataFrame(rows).sort_values('roc_auc', ascending=False)
display(model_summary)
            '''),
            md("""
            ## 5. Summary

            - 수집/전처리 결과: `riot-scale-2600` 실행본에서 2,525경기, 5,050개 team row 확보함.
            - label: 항복으로 종료된 경기에서 패배 팀만 positive로 정의해 team-level label leakage 줄임.
            - 검증: strict validation과 업로드 전 로컬 row count 검증 통과함.
            - 모델: Logistic Regression이 test ROC-AUC 기준 가장 높은 성능 보임.
            - 해석: 15분 시점 gold/kill/cs/tower/dragon 차이가 항복 패배 label과 관련됨.
            - 한계: Emerald I 중심 데이터라 tier/generalization 편향 남음.
            """),
        ],
    ))

    manifest = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "run_id": RUN_ID,
        "purpose": "Versioned Riot surrender analysis notebooks",
        "notebooks": [str(p.relative_to(ROOT)) for p in created],
        "recommended_order": [
            "v01_data_validation_riot_scale_2600.ipynb",
            "v02_eda_feature_interpretation_riot_scale_2600.ipynb",
            "v03_modeling_threshold_riot_scale_2600.ipynb",
            "v04_submission_report_riot_scale_2600.ipynb",
        ],
    }
    (VERSION_DIR / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    version_log = f"""
# Jupyter Version Log

노트북 파일명을 기준으로 분석 단계 구분함.

## Naming rule

```text
notebooks/versions/vNN_<purpose>_<run_id>.ipynb
```

- `vNN`: 분석 진행 순서
- `<purpose>`: data validation, EDA, modeling, report summary
- `<run_id>`: 사용 데이터 실행본. 현재는 `{RUN_ID}`

## Current notebooks

| Version | File | Purpose | Edit policy |
|---|---|---|---|
| v01 | `v01_data_validation_riot_scale_2600.ipynb` | 데이터 규모/품질/Supabase 검증 | 보존 |
| v02 | `v02_eda_feature_interpretation_riot_scale_2600.ipynb` | EDA와 feature 해석 | 보존 |
| v03 | `v03_modeling_threshold_riot_scale_2600.ipynb` | 모델 비교/중요도/threshold tuning | 보존 |
| v04 | `v04_submission_report_riot_scale_2600.ipynb` | 결과 요약 | 보존 |

## Update rule

1. 기존 버전은 보존함.
2. 새 분석 단계는 `v05_...ipynb`처럼 추가함.
3. `manifest.json`과 이 로그를 함께 갱신함.
4. 실행 완료본은 output을 남기고, 별도 보관이 필요하면 `.executed.ipynb` suffix 사용함.
""".strip() + "\n"
    (NOTEBOOK_DIR / "VERSION_LOG.md").write_text(version_log, encoding="utf-8")

    print("created notebooks:")
    for path in created:
        print(" -", path.relative_to(ROOT))
    print(" -", (VERSION_DIR / "manifest.json").relative_to(ROOT))
    print(" -", (NOTEBOOK_DIR / "VERSION_LOG.md").relative_to(ROOT))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
