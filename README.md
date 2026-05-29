# Riot Ranked Surrender Prediction

아주대학교 인공지능융합학과 2026년 1학기 **기계학습기초** Team 2 프로젝트임.
Riot API로 수집한 랭크 솔로 게임을 팀 단위 데이터셋으로 변환하고, 15분 시점의 경기 지표로 해당 팀의 최종 서렌 패배 여부를 예측함.

## 1. 문제점

League of Legends 랭크 게임은 한 판의 시간이 길고, 초반 불리함이 누적되면 유저가 경기를 끝까지 이어가기 부담스러운 구조임. 유저들이 소환사의 협곡뿐 아니라 ARAM, 아레나처럼 짧고 전투 중심적인 모드도 많이 찾는다는 점은 긴 경기에서 발생하는 피로감과 부담이 게임 경험에서 중요한 요소라는 것을 보여줌.

특히 15분 시점에 이미 큰 격차가 벌어진 경우, 유저는 실제 승패가 확정되지 않았더라도 경기를 복구하기 어렵다고 느낄 수 있음. 이때 어떤 요소가 “게임이 기울었다”는 인식으로 이어지는지 데이터 기반으로 파악할 필요가 있음.

따라서 이 프로젝트의 문제점은 단순히 승패를 맞추는 것이 아니라, **어떤 15분 경기 상태가 유저의 포기 의사와 서렌 패배로 연결되는지 설명하기 어렵다는 점**임.

## 2. 프로젝트 목표와 접근

이 프로젝트는 15분까지 관측 가능한 팀 단위 지표만 사용해 최종 서렌 패배 여부를 예측함. 경기 종료 시점 정보를 feature에 넣지 않고, 15분 이전 타임라인과 이벤트만 사용해 label leakage를 줄임.

| 항목 | 내용 |
| --- | --- |
| 분석 단위 | 한 경기의 한 팀 |
| 대상 큐 | Ranked Solo/Duo, `queue_id=420` |
| 기준 시점 | 게임 시작 후 15분 |
| 예측 대상 | 해당 팀의 일반 서렌 패배 여부 |
| 주요 feature | 골드, 킬, CS, 평균 레벨, 포탑, 드래곤, 전령, 선취점, 첫 포탑, 와드 설치/제거 차이 |

분석 데이터의 포함 기준, feature, label 정의는 [분석 데이터 기준서](docs/data_contract.md)에 정리함.

## 3. 주요 결과

현재 분석 notebook은 `riot-scale-2600` 실행 산출물을 기준으로 작성됨.

| 항목 | 값 |
| --- | ---: |
| 분석 경기 수 | 2,525 |
| 팀 row 수 | 5,050 |
| 서렌 패배 row 수 | 870 |
| 서렌 패배 비율 | 17.23% |
| 최고 test ROC-AUC | Logistic Regression, 0.8101 |
| Logistic Regression test F1 | 0.4936 |
| Random Forest test accuracy | 0.8337 |

15분 시점에서 골드, 킬, CS, 포탑, 드래곤 차이가 서렌 패배 label과 관련되는 경향을 확인함. 클래스 불균형이 있으므로 accuracy만으로 판단하지 않고 ROC-AUC, PR-AUC, F1, recall을 함께 확인함.

현재 전체 모델 해석에서는 `gold_diff_15`의 영향이 크게 나타남. 다만 특정 티어, 패치, 게임 흐름별로는 타워 차이와 드래곤 차이가 더 큰 신호가 될 가능성이 있음. 이런 경우 유저는 단순한 킬 손해보다 맵 주도권과 오브젝트 손실을 더 강하게 “게임이 기울었다”는 신호로 받아들인다고 해석 가능함.

## 4. 해석 관점

서렌 예측은 단순히 패배를 예측하는 문제가 아님. 유저가 어떤 경기 상태를 “복구하기 어렵다”고 인식하는지 분석하는 문제에 가까움.

예를 들어 특정 요소에 의해 한 팀이 복구하기 힘든 피해를 입었다고 인식하면, 그 시점 이후 서렌 투표로 이어질 수 있음. 이 프로젝트는 그런 인식이 발생할 수 있는 15분 시점의 경기 요소를 데이터로 확인하려는 접근임.

| 주요 요인 | 해석 가능성 |
| --- | --- |
| 15분 골드 차이 | 초반 스노우볼이 강하게 작동할 가능성 있음 |
| 드래곤 차이 | 오브젝트 보상이 체감상 크게 느껴질 가능성 있음 |
| 타워 차이 | 라인전 붕괴 이후 맵 주도권 회복이 어렵게 인식될 가능성 있음 |
| 킬 차이 | 초반 교전 패배가 포기 의사로 이어질 가능성 있음 |
| 시야 차이 | 운영 격차가 심리적 포기와 연결될 가능성 있음 |

즉, 서렌 예측 모델은 유저들이 어떤 게임 상태를 “돌이킬 수 없다”고 느끼는지 보여주는 도구가 될 수 있음.

## 5. 산업적 활용 가능성

이 분석은 게임 밸런스와 유저 경험 개선에 활용 가능함. 특정 지표가 서렌 가능성과 지나치게 강하게 연결된다면, 해당 지표는 밸런스 관점에서 중요한 신호일 수 있음.

예를 들어 15분 골드 차이가 가장 강한 요인이라면 초반 스노우볼이 과도할 가능성을 검토할 수 있음. 드래곤 차이가 강한 요인이라면 오브젝트 보상이 체감상 과도한지 확인할 수 있음. 타워 차이가 강한 요인이라면 라인전 붕괴 이후 복구 가능성이 충분한지 살펴볼 수 있음.

따라서 이 모델은 “누가 이길 것인가”를 넘어서, “어떤 게임 상태에서 유저가 경기를 포기하고 싶어지는가”를 분석하는 도구로 활용 가능함.

## 6. 한계와 후속 분석

현재 결과는 15분 시점 feature와 서렌 패배 label 사이의 관계를 분석한 것임. 따라서 특정 feature가 서렌의 직접 원인이라고 단정할 수는 없음. 인과관계를 더 강하게 주장하려면 패치 버전, 티어, 챔피언 조합, 포지션, 게임 모드별 추가 분석이 필요함.

후속 분석으로는 다음이 필요함.

- 패치 버전별 feature 영향 비교
- 티어별 서렌 패턴 비교
- 챔피언/포지션 조합 feature 추가
- ARAM, 아레나 등 짧은 게임 모드와의 비교
- SHAP 또는 permutation importance 기반 feature 영향 재검증

## 7. 진행 방식과 역할 분담

작업은 기능 단위 브랜치와 Pull Request 기준으로 나누어 진행함. 정민기가 Git/PR 운영 흐름을 관리하고, 정민기가 작성한 PR은 송재혁이 리뷰함.

| 담당자 | 주요 역할 | 산출물 |
| --- | --- | --- |
| 정민기 | Git/PR 운영, README, notebook/report 정리 | PR template, 프로젝트 문서, Jupyter 분석 notebook, README |
| 송재혁 | 분석 데이터 기준, feature/label, validation, test | `docs/data_contract.md`, feature/label 로직, 검증 스크립트, fixture test |
| 손범준 | Riot 수집과 Supabase 업로드 파이프라인 | Riot API 수집 스크립트, Supabase upload 스크립트 |
| 양승범 | 모델 학습과 EDA 파이프라인 | baseline 모델 학습, EDA figure 생성, metric 산출 |

리뷰와 PR 문서화 과정은 [docs/pr_review_record.md](docs/pr_review_record.md)에 기록함.

## 8. 프로젝트 구조

```text
.
├── docs/
│   ├── data_contract.md          # 분석 데이터 기준서
│   ├── development_guide.md
│   └── supabase_schema.sql
├── notebooks/
│   ├── team2_riot_surrender_analysis.ipynb
│   ├── team2_riot_surrender_analysis.executed.ipynb
│   └── versions/
├── scripts/
│   ├── collect_riot_matches.py
│   ├── build_team_dataset.py
│   ├── validate_team_dataset.py
│   ├── train_models.py
│   ├── run_eda.py
│   └── verify_local_pipeline.py
├── src/team2_surrender/
└── tests/
```

## 9. 주요 산출물

- 메인 분석 notebook: [notebooks/team2_riot_surrender_analysis.ipynb](notebooks/team2_riot_surrender_analysis.ipynb)
- 실행 완료 notebook: [notebooks/team2_riot_surrender_analysis.executed.ipynb](notebooks/team2_riot_surrender_analysis.executed.ipynb)
- 버전별 notebook: [notebooks/versions](notebooks/versions)
- 분석 데이터 기준서: [docs/data_contract.md](docs/data_contract.md)
- 개발 및 재현 가이드: [docs/development_guide.md](docs/development_guide.md)
- Supabase schema: [docs/supabase_schema.sql](docs/supabase_schema.sql)

## 10. 재현 방법 요약

상세한 개발 환경 구축, 데이터 수집, 모델 학습, notebook 실행 방법은 [docs/development_guide.md](docs/development_guide.md)를 참고함.

빠른 로컬 검증은 fixture 데이터 기준으로 실행 가능함.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
PYTHONPATH=src python -m unittest discover -s tests -v
python scripts/verify_local_pipeline.py
```

원본 Riot 응답, 가공 CSV, 모델 파일, 출력 결과, figure 산출물은 git에 올리지 않음. 제출 문서와 notebook에는 재현 가능한 절차와 핵심 결과만 남김.
