# Jupyter Version Log

노트북 파일명을 기준으로 분석 단계 구분함.

## Naming rule

```text
notebooks/versions/vNN_<purpose>_<run_id>.ipynb
```

- `vNN`: 분석 진행 순서
- `<purpose>`: data validation, EDA, modeling, report summary
- `<run_id>`: 사용 데이터 실행본. 현재는 `riot-scale-2600`

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
