# Team 2 Riot 15분 경기 상태 기반 패배 위험 분석

아주대학교 인공지능융합학과 2026년 1학기 **기계학습기초** Team 2 프로젝트입니다.
Riot Ranked Solo/Duo 경기의 15분 시점 팀 단위 feature를 사용해 경기 상태가 패배 위험과 어떻게 연결되는지 분석합니다.

## 1. 문제 정의

초기 목표는 15분 시점의 팀 상태로 **서렌 패배(`team_surrendered`)**를 예측하는 것이었습니다.
실험을 진행하면서 서렌 label은 양성 비율이 낮고, 팀의 15분 경기력보다 유저 의사결정·상황적 요인의 영향을 크게 받는다는 한계를 확인했습니다.

따라서 최종 분석은 다음과 같이 정리합니다.

- 교육과정 범위 모델로 `team_surrendered` baseline을 검증합니다.
- 성능과 설명력을 높이기 위해 label을 **최종 패배(`final_loss`)**로 재정의한 실험을 함께 제시합니다.
- 최종 해석은 “15분 경기 상태가 최종 패배 위험을 얼마나 설명하는가”에 둡니다.
- XGBoost/LightGBM, KMeans interaction 등 교육과정 밖 방법은 보조 검증으로만 사용합니다.

## 2. 최종 제출 구조

```text
.
├── data_1/                     # 초기 공통 baseline 재현용 최소 가공 데이터
├── data_2/                     # temporal/counter 확장 중간 데이터
├── data_3/                     # 최종 v16.9 정합 데이터와 외부 champion context
├── lab/                        # 공식 Jupyter 분석 notebook
├── Report/Submission/          # 최종 보고서
├── docs/                       # data contract, schema, PR/review 작업 문서
├── scripts/                    # 수집/가공/업로드/검증 실행 스크립트
├── src/team2_surrender/        # 재사용 가능한 데이터셋/feature/pipeline 코드
└── tests/                      # 단위 테스트와 fixture 검증
```

커밋 대상에서 제외하는 항목은 `.gitignore`에 정리했습니다. 개인 실험 workspace, 모델 바이너리, 실행 output, zip 파일은 올리지 않고, 핵심 실험 내용은 `lab/*.ipynb`와 최종 보고서에 흡수합니다.

## 3. Jupyter notebook 구성

`lab/`은 시간순 실험 흐름을 재현하도록 구성했습니다.

| 파일 | 내용 |
| --- | --- |
| `01_data_validation.ipynb` | 초기 공통 데이터 검증 |
| `02_eda_feature_interpretation.ipynb` | EDA와 feature 해석 |
| `03_modeling_threshold.ipynb` | baseline 모델과 threshold 조정 |
| `04_submission_report_analysis.ipynb` | 공통 결과와 최종 보고서 연결 |
| `05_bumjun_baseline_feature_expansion.ipynb` | 범준: baseline feature 확장 한계 |
| `06_bumjun_mlp_model_ceiling.ipynb` | 범준: MLP/비선형 모델 상한 검토 |
| `07_bumjun_label_reframing_final_loss.ipynb` | 범준: `final_loss` label 재정의 |
| `08_bumjun_generalization_risk_explanation.ipynb` | 범준: multi-seed 안정성/일반화 위험 |
| `09_bumjun_data3_compact_l1_explainability.ipynb` | 범준: data_3 compact L1 설명 모델 |
| `10_seungbeom_rf_tuning_initial_limit.ipynb` | 승범: Random Forest tuning 한계 |
| `11_seungbeom_deep_learning_counter_limit.ipynb` | 승범: MLP/counter feature 한계 |
| `12_seungbeom_loss_only_scorecard_explainability.ipynb` | 승범: final_loss scorecard |
| `13_seungbeom_data3_lolalytics_final_loss.ipynb` | 승범: Lolalytics/game-length context |
| `14_seungbeom_kmeans_interaction_advanced_check.ipynb` | 승범: KMeans interaction과 고급 모델 보조 검증 |

## 4. 데이터 묶음

| 폴더 | 역할 |
| --- | --- |
| `data_1/` | `riot-scale-2600` 공통 baseline 재현용 최소 데이터 |
| `data_2/` | temporal feature, champion counter, game-length win-rate 확장 과정 데이터 |
| `data_3/` | 최종 분석 기준 데이터. Riot v16.9 5,050 team row와 Lolalytics v16.9 외부 context를 포함 |

원본 Riot API 응답과 중간 산출물은 용량과 재현성 관리 문제 때문에 제출 대상에서 제외합니다.

## 5. 주요 실험 결론

- `team_surrendered`는 프로젝트의 초기 문제의식과 맞지만, 양성 label이 희소해 설명력 개선 폭이 제한적이었습니다.
- 15분 feature는 서렌보다 최종 패배 위험(`final_loss`)과 더 직접적으로 연결되었습니다.
- 딥러닝/고급 모델을 시도해도 설명 가능한 L1/L2 Logistic Regression을 압도하지 못했습니다.
- 최종 보고서는 성능 수치만 강조하지 않고, label 재정의의 타당성·feature 해석·일반화 위험을 함께 설명합니다.

세부 수치와 해석은 `Report/Submission/Team2_report.md`와 `lab/` notebook을 기준으로 확인합니다.

## 6. 재현 방법

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Jupyter에서 `lab/01`부터 `lab/14`까지 순서대로 실행합니다. 일괄 실행 검증은 다음과 같이 할 수 있습니다.

```bash
python -m nbconvert --execute --to notebook --inplace lab/*.ipynb
```

코드 단위 검증은 다음 명령을 사용합니다.

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
```

## 7. 최종 보고서

최종 제출 보고서는 다음 파일입니다.

```text
Report/Submission/Team2_report.md
```

개인별 작은 markdown summary나 실험 로그는 원격 저장소에 따로 올리지 않고, 최종 보고서와 `lab/` notebook 안에서 필요한 내용만 유지합니다.
