---
title: "2026-1 기계학습기초 Team 2 Final Report: 15분 경기 상태 기반 League of Legends 랭크 솔로 서렌 패배 및 Dead Game 위험 분석"
author: "2팀: 정민기, 송재혁, 손범준, 양승범"
date: "2026-06-12"
lang: ko-KR
fontsize: "10pt"
bibliography: "references.bib / Word 사용 시 MLA 또는 URL 참고문헌 형식"
link-citations: true
---

**소속:** 아주대학교 인공지능융합학과  
**교과목:** 2026년 1학기 기계학습기초  
**담당교수:** 기계학습기초 담당교수  
**팀:** Team 2  
**팀원:** 정민기, 송재혁, 손범준, 양승범  
**제출일:** 2026-06-12  

---

# 15분 경기 상태 기반 League of Legends 랭크 솔로 서렌 패배 및 Dead Game 위험 분석

## Abstract

본 프로젝트는 Riot API로 수집한 League of Legends 한국 서버 랭크 솔로/듀오 게임 데이터를 이용하여, 경기 시작 후 15분 시점의 팀 단위 상태가 일반 서렌 패배 및 최종 패배 위험과 어떻게 연결되는지 분석한다[1]. 초기 문제는 `team_surrendered` 이진 분류였으며, `riot-scale-2600` 데이터셋은 2,525경기, 5,050개 match-team row, 서렌 패배 row 870개로 구성된다. 기존 서렌 label 기준에서는 Dummy, Logistic Regression, Random Forest, HistGradientBoosting을 비교했고, 하이퍼파라미터 및 threshold 조정 후 F1 균형 Random Forest가 test F1 0.522, recall 0.647, precision 0.438을 기록했다[2][3]. 그러나 후속 설명력 보강 실험에서 확인한 핵심 결론은, 15분 경기 상태만으로 “서렌 선택” 자체를 고성능으로 예측하기는 어렵지만 같은 계열의 15분 feature가 최종 패배 또는 Dead Game 위험은 훨씬 안정적으로 설명한다는 점이다. `data_3` v16.9 단일 패치와 Lolalytics champion-position prior를 반영한 후[13], 12-feature `core_rule_lolalytics_12_pruned` L1 Logistic Regression은 10-seed 평균 F1 0.7716, PR-AUC 0.8490을 기록했고, `flow_plus_counter_game_length_archetype_interactions` L1 Logistic Regression은 5-seed 평균 F1 0.7855, PR-AUC 0.8584를 기록했다[7][9][10]. 단, 이 수치는 target, dataset, feature set이 함께 바뀐 후속 실험 결과이므로 “동일 조건에서 단순히 모델만 바꿔 상승했다”는 뜻이 아니라, 문제정의를 서렌 행동 label과 final-loss 위험 label로 분리했을 때 설명력이 달라진다는 근거로 해석한다. 따라서 최종 보고서의 주장은 “15분에 서렌해야 하는지 추천하는 모델”이 아니라, “15분 경기 상태가 최종 패배 위험을 설명하는 방식과 그 한계를 분석한 설명 가능한 ML 모델”로 정리한다.

**Keywords:** League of Legends, Riot API, surrender prediction, final-loss risk, Dead Game, early-game features, class imbalance, Logistic Regression, Random Forest, explainability

---

## 1. Introduction

### 1.1 문제 배경

League of Legends는 5대5 팀 기반 MOBA 게임으로, 한 경기의 승패는 라인전, 교전, 오브젝트, 시야, 운영 등 다양한 요소가 누적되어 결정된다. 그러나 실제 플레이 경험에서는 최종 넥서스 파괴 이전에도 “이미 게임이 기울었다”는 인식이 발생한다. 특히 랭크 솔로/듀오 게임에서는 팀원 간 의사소통이 제한적이고, 초반 손해가 누적되면 플레이어가 게임을 끝까지 이어가기보다 서렌 투표를 선택하는 상황이 자주 발생한다.

이 프로젝트는 단순히 어떤 팀이 승리할지 맞히는 것이 아니라, 15분 시점의 경기 상태가 최종적인 서렌 패배와 얼마나 연결되는지를 분석한다. 여기서 15분은 일반 서렌 투표가 가능해지는 시점과 연결되는 중요한 기준점이다. 따라서 15분까지 관측 가능한 팀 단위 지표가 서렌 패배 여부를 설명할 수 있다면, 이는 플레이어가 어떤 경기 상태를 복구 불가능하다고 인식하는지 이해하는 데 도움이 된다.

### 1.2 문제 정의

본 프로젝트의 예측 문제는 다음과 같이 정의한다.

> 경기 시작 후 15분까지의 팀 단위 경기 지표만 보고, 해당 팀이 최종적으로 일반 서렌 패배한 팀인지 예측한다.

분석 단위는 `match-team row`이다. 하나의 경기는 블루 팀과 레드 팀의 두 행으로 변환되며, 각 row는 “우리 팀 기준”의 feature 차이값을 가진다. 예를 들어 `gold_diff_15`는 해당 팀의 15분 골드 합에서 상대 팀의 15분 골드 합을 뺀 값이다. 라벨 `team_surrendered`는 해당 팀이 패배 팀이고 참가자 중 일반 서렌 종료 플래그가 존재하는 경우 `True`로 정의했다.

다만 후속 실험에서는 이 target만으로는 프로젝트 의의를 충분히 설명하기 어렵다는 점도 확인했다. 서렌은 경기 상태뿐 아니라 플레이어 성향, 팀 분위기, 15분 이후 사건이 섞인 행동 label이기 때문이다. 따라서 본 보고서는 초기 `team_surrendered` 예측 실험을 기준선으로 보존하되, 최종 해석에서는 보조 target인 `final_loss`, 즉 해당 팀이 최종적으로 패배했는지를 사용해 15분 상태가 Dead Game/패배 위험을 얼마나 설명하는지 함께 분석한다.

본 보고서에서 **Dead Game**은 “15분까지 관측 가능한 팀 상태와 외부 champion-position prior만으로 추정했을 때 final-loss 위험 점수가 높은 경기 상태”를 뜻한다. 이는 실제 경기 종료 시간, 실제 최종 승패, 플레이어가 누른 서렌 여부를 feature로 사용하는 개념이 아니며, 특정 팀에게 서렌을 권고하는 운영 모델도 아니다. 즉 Dead Game은 사후 label인 `final_loss`와 15분 상태 사이의 관련성을 설명하기 위한 분석 용어이다.

### 1.3 프로젝트 목표와 기여

본 프로젝트의 목표는 다음 다섯 가지이다.

1. Riot API match/timeline 응답을 기반으로 15분 팀 단위 feature 데이터셋을 구축한다.
2. 종료 시점 정보가 feature에 섞이지 않도록 데이터 계약과 검증 절차를 명확히 한다.
3. class imbalance가 있는 서렌 패배 예측 문제에서 accuracy 착시를 피하고 F1, recall, PR-AUC 중심으로 모델을 평가한다.
4. 모델 성능뿐 아니라 feature 신호를 해석하여 어떤 초반 경기 요소가 서렌 패배 흐름과 강하게 연결되는지 논의한다.
5. 최신 `data_3`와 설명가능 feature engineering 실험을 통해, 원래 서렌 label의 한계와 final-loss 위험 설명 모델의 의의를 구분한다.

본 프로젝트의 주요 기여는 다음과 같다.

- `queue_id=420` 랭크 솔로/듀오 게임만 사용하고, 15분 미만 경기·조기 서렌·필수 타임라인 누락 경기 등을 제외하는 데이터 기준을 정의했다.
- 한 경기의 양 팀 row가 서로 다른 split에 들어가는 leakage를 방지하기 위해 `match_id` 기준 group split을 적용했다.
- Dummy baseline의 높은 accuracy가 실제 positive class 탐지 능력을 의미하지 않음을 확인하고, 서렌 패배 class 중심의 평가 체계를 사용했다.
- F1 균형 후보와 recall 중심 후보를 구분하여, 모델 운영 목적에 따른 threshold trade-off를 제시했다.
- 이후 후속 설명력 보강 실험을 통해 복잡한 딥러닝보다 L1 Logistic Regression, KMeans archetype, scorecard 등 설명 가능한 feature engineering이 final-loss 위험 분석에 더 적합함을 확인했다.

---

## 2. Related Work / Background

### 2.1 Riot API와 match timeline 기반 분석

Riot Developer Portal은 League of Legends의 Match-V5 API를 통해 match detail과 timeline 데이터를 제공한다. Match detail에는 게임 메타데이터, 참가자 정보, 팀별 종료 상태 등이 포함되며, timeline에는 분 단위 participant frame과 이벤트가 포함된다. 본 프로젝트는 이 구조를 이용하여 15분 시점 participant frame에서 골드·CS·레벨 정보를 추출하고, 15분 이전 이벤트에서 킬, 포탑, 드래곤, 전령, 와드 설치/제거, 선취점, 첫 포탑 정보를 추출했다.

다만 원본 Riot 응답에는 PUUID, 소환사 식별자 등 개인정보 또는 재식별 가능 정보가 포함될 수 있다. 따라서 공개 산출물에는 팀 단위로 집계한 feature만 남기고, PUUID·소환사명·Riot ID·API key·Supabase key를 포함하지 않는 기준을 적용했다.

### 2.2 Early-game feature 기반 예측

게임 승패 또는 불리한 흐름 예측에서는 초반 경제 차이, 경험치/레벨 차이, 교전 결과, 오브젝트 획득 여부가 중요한 설명 변수로 사용된다. 본 프로젝트 역시 15분 이전 정보만 사용하는 early-game prediction 문제로 볼 수 있다. 그러나 일반 승패 예측과 달리 target은 최종 승패가 아니라 “일반 서렌으로 패배했는지”이다. 따라서 모델은 단순히 이길 팀을 맞히기보다, 플레이어가 경기 지속 의지를 잃을 만큼 불리한 상태를 탐지하는 역할에 가깝다.

### 2.3 Class imbalance와 평가 지표

최종 데이터셋에서 서렌 패배 row는 전체 5,050개 중 870개로 17.23%에 불과하다. 이처럼 positive class가 적은 이진 분류 문제에서는 모든 샘플을 negative로 예측해도 accuracy가 높게 나올 수 있다. 실제로 Dummy baseline은 test accuracy 0.818을 기록했지만, 서렌 패배 184건 중 0건을 잡아 recall과 F1이 모두 0이었다. 따라서 본 프로젝트에서는 accuracy를 보조 지표로만 사용하고, precision, recall, F1, ROC-AUC, PR-AUC를 함께 확인했다.

### 2.4 사용 모델의 배경

본 프로젝트는 다음 모델을 비교했다.

- **Dummy Classifier:** class imbalance 상황에서 “아무것도 학습하지 않는 기준선”을 제공한다.
- **Logistic Regression:** 선형 결정 경계를 기반으로 class_weight와 threshold 조정을 통해 positive class recall을 높이기 쉽다.
- **Random Forest:** 여러 decision tree를 앙상블하여 비선형 feature 상호작용을 포착할 수 있고, feature scale에 덜 민감하다.
- **HistGradientBoosting:** gradient boosting 계열의 비선형 모델로 baseline 비교에 포함했다.

초기 서렌 label 해석에서는 Random Forest를 F1 균형 후보로, Logistic Regression을 recall 중심 대안으로 제시한다[3][6][7]. 후속 final-loss 위험 분석에서는 L1 Logistic Regression을 중심으로 사용했다. L1 규제는 feature 선택 효과가 있어 계수 해석과 feature pruning이 가능하며[9], 교수님이 지적한 모델 설명력 요구에 대응하기 쉽다. 한 실험 track에서는 KMeans로 champion-position archetype을 구성해 조합의 시간대별 강약을 feature로 요약했고[10], 다른 track에서는 12개 core-rule 및 Lolalytics prior feature만 남긴 compact LR을 최종 설명 후보로 두었다[13]. XGBoost와 LightGBM은 성능 상한 확인용으로 실험했지만, 본문 최종 후보는 설명 가능성이 높은 L1 LR 계열로 유지한다[11][12].

---

## 3. Dataset and Data Contract

### 3.1 데이터 수집 개요

최종 분석에는 `riot-scale-2600` 실행 산출물을 사용했다. 수집 파이프라인은 Riot API에서 match detail과 timeline JSON을 수집한 뒤, 이를 팀 단위 feature CSV로 변환하는 방식이다. 검증 기록에 따르면 수집은 한국 서버 기준 랭크 솔로/듀오 게임을 대상으로 수행되었고, 수집 설정은 `EMERALD I`, 최대 seed 200명, seed별 match id 최대 20개, unique match 최대 2,600개였다.

최종 feature CSV 생성 결과는 다음과 같다.

| 항목 | 값 |
| --- | ---: |
| 입력 run id | `riot-scale-2600` |
| eligible match 수 | 2,525 |
| team row 수 | 5,050 |
| positive row 수 (`team_surrendered=True`) | 870 |
| negative row 수 | 4,180 |
| positive 비율 | 17.23% |
| queue id | 420 |
| feature version | `v1_15min` |
| 생성 시각 | 2026-05-14 19:59:29 UTC |

2,600개 unique match 수집을 목표로 했으나 최종 eligible match는 2,525개였다. 제외 사유는 15분 미만 경기 71개, `queue_id != 420` 경기 4개였다.

### 3.2 분석 단위

데이터셋의 한 행은 “한 경기의 한 팀”이다. 한 경기는 블루 팀(`team_id=100`)과 레드 팀(`team_id=200`) 두 행으로 변환된다. 모든 차이 feature는 “해당 row의 팀 기준”으로 계산된다.

```text
feature_diff = this_team_value - opponent_team_value
```

예를 들어 블루 팀 row에서 `gold_diff_15=-3000`이면 15분 시점 블루 팀의 총 골드가 레드 팀보다 3,000 낮다는 뜻이다. 같은 경기의 레드 팀 row에서는 이 값이 반대 부호가 된다.

### 3.3 포함 및 제외 기준

최종 데이터셋에는 다음 조건을 만족하는 경기만 포함했다.

- Ranked Solo/Duo queue인 `queue_id=420` 경기
- 게임 길이가 900초 이상인 경기
- 15분 timeline frame이 존재하는 경기
- 필수 participant frame 값이 누락되지 않은 경기
- 조기 서렌 또는 리메이크에 가까운 경기로 판단되지 않은 경기

제외 기준은 다음과 같다.

| 제외 조건 | 이유 |
| --- | --- |
| `queue_id != 420` | 랭크 솔로/듀오가 아닌 경기 제외 |
| `game_duration_sec < 900` | 15분 feature를 만들 수 없거나 일반 서렌 기준과 맞지 않음 |
| `gameEndedInEarlySurrender == true` | 조기 서렌/리메이크성 경기와 일반 서렌 패배를 분리 |
| 15분 frame 없음 | 핵심 feature 산출 불가 |
| 필수 participant frame 값 누락 | 팀 단위 feature 산출 신뢰도 저하 |

### 3.4 라벨 정의

라벨 컬럼은 `team_surrendered`이다. 정의는 다음과 같다.

```text
team_surrendered = True
if this team is the losing team
and at least one participant in this team has gameEndedInSurrender == true
```

중요한 점은 라벨 생성을 위해 경기 종료 상태를 사용하지만, 종료 상태 자체는 feature로 사용하지 않는다는 것이다. 즉, 모델은 최종 승패, 최종 골드, 경기 종료 시간, 15분 이후 이벤트, 서렌 종료 플래그를 직접 보지 않는다.

### 3.5 Feature 정의

사용한 feature는 총 11개이다.

| Feature | 의미 | 출처 |
| --- | --- | --- |
| `gold_diff_15` | 15분 팀 총 골드 차이 | 15분 participant frame |
| `kill_diff_15` | 15분까지 챔피언 킬 수 차이 | `CHAMPION_KILL` event |
| `tower_diff_15` | 15분까지 포탑 파괴 수 차이 | `BUILDING_KILL` event |
| `dragon_diff_15` | 15분까지 드래곤 처치 수 차이 | `ELITE_MONSTER_KILL` event |
| `rift_herald_diff_15` | 15분까지 전령 처치 수 차이 | `ELITE_MONSTER_KILL` event |
| `cs_diff_15` | 15분 미니언+정글 CS 합 차이 | 15분 participant frame |
| `avg_level_diff_15` | 15분 팀 평균 레벨 차이 | 15분 participant frame |
| `first_blood` | 15분 전 선취점 방향 | event |
| `first_tower` | 15분 전 첫 포탑 방향 | event |
| `ward_placed_diff_15` | 15분까지 와드 설치 수 차이 | `WARD_PLACED` event |
| `ward_kill_diff_15` | 15분까지 와드 제거 수 차이 | `WARD_KILL` event |

`first_blood`와 `first_tower`는 해당 팀이 먼저 달성하면 `1`, 상대 팀이 먼저 달성하면 `-1`, 15분 전 발생하지 않았으면 `0`으로 인코딩했다.

전령 feature에 대해서는 추가 확인이 필요했다. 최종 CSV에서 `rift_herald_diff_15`가 모든 row에서 0으로 나타났기 때문이다. raw timeline 2,600개를 스캔한 결과, 15분 이전 `ELITE_MONSTER_KILL` 이벤트에는 `DRAGON` 3,822건과 `HORDE` 7,626건이 있었고, `RIFTHERALD` 2,304건은 모두 15분 이후에 기록되어 있었다. 따라서 이번 데이터에서 `rift_herald_diff_15=0`은 단순 집계 오류라기보다 현재 패치의 15분 이전 상단 오브젝트가 Riot timeline에서 `HORDE`로 기록되기 때문으로 해석된다. 본 실험에서는 기존 feature 계약을 유지하기 위해 `HORDE`를 별도 feature로 추가하지 않았으므로, `rift_herald_diff_15`는 모델 구분 신호로 작동하지 않는다. 후속 실험에서는 `horde_diff_15`를 추가하거나 전령/공허 유충 오브젝트 정의를 패치 버전에 맞게 갱신해야 한다.

### 3.6 개인정보 및 보안 기준

분석 및 제출 산출물에는 다음 정보를 포함하지 않았다.

- PUUID
- 암호화된 소환사 ID
- 소환사 이름 또는 Riot ID
- 참가자 이름
- Riot API key
- Supabase key 또는 DB password

원본 JSON과 대용량 processed data는 재현을 위한 로컬 산출물로만 유지하고, 제출 보고서에는 팀 단위 집계 결과와 재현 절차만 포함한다.

### 3.7 후속 `data_3`와 외부 prior 데이터 계약

Claude 검수에서 지적된 것처럼, 후속 final-loss 성능을 해석하려면 `data_3`의 정의를 별도로 밝혀야 한다. `data_3`는 `riot-scale-2600`과 같은 규모의 2,525경기, 5,050 match-team row 구조를 유지하되, 패치 분포를 v16.9 단일 패치로 맞춘 재수집·보강 데이터이다. 팀 row 기준 `final_loss`는 한 경기당 패배 팀 1행만 positive가 되므로 전체 양성률은 50.0%이다. 이는 `team_surrendered=True` 양성률 17.23%와 다르기 때문에, 두 target의 F1을 단순 동일 조건 성능으로 비교해서는 안 된다.

후속 실험의 외부 feature는 Lolalytics 16.9 champion-position 집계 prior를 사용했다[13]. 여기서 `game_length` 또는 `duration bucket`이라는 이름이 붙은 feature는 **현재 match의 실제 경기 시간**이 아니다. 각 챔피언·포지션이 15~20분, 20~25분, 25~30분 등 시간대별로 어떤 평균 승률 profile을 갖는지 나타내는 외부 집계 prior이며, match 시작 전 또는 15분 시점에도 알 수 있는 champion prior로만 사용했다. 누수 방지 audit에서도 `game_duration`, `duration_bucket`, `actual_game_length`, `win`, `team_surrendered`, `final_loss_label` 등 금지 feature와의 교집합은 비어 있었다.

| 항목 | `riot-scale-2600` 초기 데이터 | 후속 `data_3` |
| --- | ---: | ---: |
| match 수 | 2,525 | 2,525 |
| team row 수 | 5,050 | 5,050 |
| 주요 target | `team_surrendered` | `final_loss` |
| positive rate | 17.23% | 50.00% |
| 패치 | 수집 run 기준 혼합 가능 | v16.9 only |
| 외부 prior | 없음 | Lolalytics 16.9 champion-position prior |
| split 기준 | `match_id` group split | `match_id` group split |
| 금지 feature | 종료/승패/15분 이후 정보 제외 | 종료/승패/실제 경기 시간/label 제외 |

---

## 4. Approach

### 4.1 전체 파이프라인

본 프로젝트의 전체 흐름은 다음과 같다.

```text
Riot API
→ raw match/timeline JSON 수집
→ 15분 기준 팀 단위 feature 추출
→ 데이터 계약 검증
→ match_id 기준 train/validation/test split
→ baseline 모델 학습
→ 하이퍼파라미터 튜닝
→ feature set 비교
→ threshold 조정
→ 원래 서렌 label 성능 한계 확인
→ final-loss / Dead Game 위험 설명 실험
→ 설명가능 feature pruning 및 최종 후보 해석
```

각 단계의 주요 산출물은 다음과 같다.

| 단계 | 입력 | 출력 | 근거 파일 |
| --- | --- | --- | --- |
| 데이터 수집 | Riot API | raw JSON run | `scripts/collect_riot_matches.py` |
| 팀 feature 생성 | raw JSON | team feature CSV | `scripts/build_team_dataset.py` |
| 데이터 검증 | team feature CSV | validation JSON | `scripts/validate_team_dataset.py` |
| 모델 학습 | team feature CSV | metrics/model artifacts | `scripts/train_models.py` |
| EDA | team feature CSV | figures | `scripts/run_eda.py` |
| 실험 튜닝 | team feature CSV | threshold/model 비교 | `lab/03_modeling_threshold.ipynb`, `lab/10_seungbeom_rf_tuning_initial_limit.ipynb`, `lab/14_seungbeom_kmeans_interaction_advanced_check.ipynb` |

### 4.2 Leakage 방지 전략

본 프로젝트에서 가장 중요한 설계 원칙은 15분 이후 정보가 feature에 들어가지 않도록 하는 것이다. 이를 위해 다음 기준을 적용했다.

1. feature는 15분 frame 또는 timestamp `<= 900000 ms` 이벤트만 사용한다.
2. 최종 승패, 종료 시간, 최종 골드, 최종 오브젝트, 서렌 플래그는 feature에서 제외한다.
3. 라벨은 feature 생성 이후 별도로 생성한다.
4. train/validation/test split은 row 기준이 아니라 `match_id` 기준 group split으로 수행한다.

특히 4번이 중요하다. 같은 match에서 블루 팀 row와 레드 팀 row는 서로 반대 부호의 feature를 갖는다. 만약 한 팀 row가 train에, 반대 팀 row가 test에 들어가면 모델이 같은 경기를 간접적으로 학습하는 leakage가 발생할 수 있다. 따라서 같은 match의 두 팀 row는 반드시 동일 split에 배정했다.

### 4.3 모델링 전략

모델링은 초기 서렌 label 실험 3단계와 후속 설명력 보강 실험 1단계로 진행했다.

#### 4.3.1 Baseline 비교

먼저 다음 모델을 동일한 feature와 split에서 비교했다.

- Dummy most frequent
- Logistic Regression
- Random Forest
- HistGradientBoosting

이 단계의 목적은 “어떤 모델이 가장 높은 accuracy를 내는가”가 아니라, class imbalance 상황에서 각 모델이 서렌 패배 row를 얼마나 잡는지 확인하는 것이다.

전처리는 scikit-learn pipeline으로 고정했다. Logistic Regression에는 median imputation 이후 `StandardScaler`를 적용했고, tree 계열 모델에는 median imputation만 적용했다. Logistic Regression과 Random Forest는 class imbalance를 고려해 `class_weight=balanced` 또는 `balanced_subsample` 계열 설정을 사용했다. HistGradientBoosting baseline은 기본 설정 비교용으로 포함했으며, 별도 class imbalance 보정이 없는 baseline이므로 최종 후보 판단에서는 Logistic Regression과 Random Forest를 중심으로 해석했다.

#### 4.3.2 하이퍼파라미터 튜닝

1차 튜닝에서는 11개 feature를 고정하고 모델 파라미터를 변경했다. Random Forest의 `n_estimators`, `max_depth`, `min_samples_leaf`, `class_weight` 등을 조정했고, Logistic Regression은 `C`와 `class_weight`를 중심으로 비교했다.

#### 4.3.3 Feature set 및 threshold 비교

2차 실험에서는 feature set을 다음과 같이 나누어 비교했다.

| Feature set | 구성 |
| --- | --- |
| `all_11_features` | 전체 11개 feature |
| `no_vision` | 전체 feature에서 시야 feature 제외 |
| `economy_only` | 골드, CS, 평균 레벨 |
| `combat_objective` | 킬, 포탑, 드래곤, 전령, 선취점, 첫 포탑 |

3차 실험에서는 최종 후보를 두 track으로 나누었다.

| Track | 목적 | 모델 |
| --- | --- | --- |
| F1 균형 후보 | precision과 recall의 균형 | Random Forest |
| Recall 중심 후보 | 실제 서렌 패배 팀을 더 많이 탐지 | Logistic Regression |

Threshold는 test set으로 고르지 않았다. 각 모델과 파라미터 조합을 train set으로 학습한 뒤 validation set에서 threshold grid를 비교했고, 미리 정한 선택 기준을 만족하는 후보를 고른 다음 test set에는 최종 확인용으로 한 번 적용했다. 따라서 test 성능은 threshold 선택에 사용하지 않은 hold-out 결과로 해석한다.

#### 4.3.4 설명력 보강과 final-loss 위험 분석

교수님 피드백 이후 후속 실험의 초점은 단순 점수 상승보다 “모델이 무엇을 설명하는가”로 이동했다. 이를 위해 다음 절차를 추가했다.

1. 기존 `team_surrendered` label의 성능 한계를 baseline으로 고정한다.
2. 같은 15분 feature가 `final_loss`를 얼마나 설명하는지 비교한다.
3. 7→15분 흐름, counter, Lolalytics champion-position prior, KMeans 조합 archetype을 추가한다. 이때 `game-length` 관련 prior는 실제 경기 종료 시간이 아니라 외부 사이트의 챔피언별 시간대 승률 profile이다.
4. feature 수를 줄인 L1 Logistic Regression과 scorecard를 사용해 설명 가능한 최종 후보를 만든다.
5. LightGBM, XGBoost, 딥러닝은 성능 상한 확인용 appendix로 두고, 최종 본문 모델은 설명력 중심의 LR 계열로 유지한다.

이 단계의 목적은 “서렌을 완벽히 맞히는 모델”을 만드는 것이 아니라, 15분 상태가 실제 패배 위험을 얼마나 잘 정렬하고 설명하는지 검증하는 것이다. 따라서 후속 수치는 초기 `team_surrendered` 실험과 target·feature·seed 수가 다르다는 점을 항상 함께 해석한다.

---

## 5. Experiment

### 5.1 Dataset

최종 실험 데이터셋은 다음과 같다.

| 항목 | 내용 |
| --- | --- |
| 데이터셋 | Riot API 기반 `riot-scale-2600` 팀 feature CSV |
| 초기 예측 목표 | `team_surrendered` |
| 후속 해석 목표 | `final_loss` / Dead Game 위험 |
| 분석 단위 | match-team row |
| match 수 | 2,525 |
| row 수 | 5,050 |
| 초기 feature 수 | 11 |
| `team_surrendered=True` row 수 | 870 |
| positive 비율 | 17.23% |
| queue | Ranked Solo/Duo (`queue_id=420`) |
| 기준 시점 | 게임 시작 후 15분 |
| 데이터 생성일 | 2026-05-14 |
| 후속 보강 데이터 | `data_3` v16.9-only Riot + Lolalytics 16.9 feature |
| `data_3` row/positive rate | 5,050 rows / `final_loss=True` 50.00% |

### 5.2 데이터 품질 검증

Strict validation 결과 모든 검증 항목이 통과했다.

| 검증 항목 | 결과 | 의미 |
| --- | --- | --- |
| Required columns | OK | 필수 컬럼 존재 |
| Row count | OK | 5,050 rows |
| Feature count | OK | 10개 이상 feature 존재 |
| Privacy columns | OK | 금지 식별자/key 컬럼 없음 |
| Target classes | OK | positive/negative 두 class 존재 |
| Group count | OK | 2,525 unique matches |
| Two rows per match | OK | 모든 match가 두 팀 row 보유 |
| Positive labels per match | OK | 한 match에 서렌 패배 팀 최대 1개 |
| Queue id | OK | 모든 row가 `queue_id=420` |
| Duration | OK | 모든 row가 900초 이상 |

### 5.3 Train/Validation/Test split

`match_id` 기준 group split을 적용했다.

| Split | Rows | Match groups |
| --- | ---: | ---: |
| Train | 3,232 | 1,616 |
| Validation | 808 | 404 |
| Test | 1,010 | 505 |

Test split에는 positive row 184개, negative row 826개가 포함되었다.

각 split의 positive 비율은 다음과 같다.

| Split | Positive rows | Negative rows | Positive ratio |
| --- | ---: | ---: | ---: |
| Train | 545 | 2,687 | 16.86% |
| Validation | 141 | 667 | 17.45% |
| Test | 184 | 826 | 18.22% |

세 split 모두 전체 positive 비율 17.23%와 크게 벗어나지 않아, group split으로 leakage를 막으면서도 라벨 분포가 과도하게 한쪽으로 치우치지는 않았다.

### 5.4 평가 지표

평가 지표는 다음과 같이 해석했다.

| 지표 | 해석 |
| --- | --- |
| Accuracy | 전체 row 중 맞춘 비율. class imbalance 때문에 단독 기준으로 사용하지 않음 |
| Precision | 서렌 위험이라고 예측한 팀 중 실제 서렌 패배 팀 비율 |
| Recall | 실제 서렌 패배 팀 중 모델이 잡아낸 비율 |
| F1 | precision과 recall의 균형 |
| ROC-AUC | positive와 negative의 ranking 분리 능력 |
| PR-AUC | positive class가 적을 때의 주요 구분 지표 |
| Confusion matrix | false positive와 false negative의 trade-off 확인 |

### 5.5 실험 환경

| 항목 | 설정 |
| --- | --- |
| 언어 | Python 3.x |
| 주요 라이브러리 | pandas, numpy, scikit-learn, matplotlib, joblib |
| 모델 구현 | scikit-learn |
| 데이터 split | `GroupShuffleSplit` 기반 `match_id` group split |
| random state | 42 |
| 실행/검증 산출물 | `lab/*.ipynb` 실행 output, `tests/` 단위 테스트 결과 |

Logistic Regression 실험은 정규화가 필요한 선형 모델이므로 `StandardScaler`를 포함한 pipeline으로 학습했다. Random Forest와 HistGradientBoosting은 scale에 상대적으로 둔감하므로 median imputation 이후 원 feature scale을 유지했다. 최종 후보 비교에서는 validation 기준 선택과 test 기준 최종 확인을 분리했다. 후속 final-loss 실험도 같은 원칙을 유지했으며, repeated `match_id` group-aware split을 사용해 단일 split 착시를 줄였다.

---

## 6. Results

### 6.1 Class balance

최종 데이터셋의 라벨 분포는 다음과 같다.

| Label | Count | Ratio |
| --- | ---: | ---: |
| `team_surrendered=False` | 4,180 | 82.77% |
| `team_surrendered=True` | 870 | 17.23% |

Positive class가 17.23%이므로, 대부분을 negative로 예측하는 모델도 높은 accuracy를 얻을 수 있다. 이 점은 baseline 결과에서 명확하게 나타났다.

Figure 1에 해당하는 class balance 그래프는 `lab/01_data_validation.ipynb`와 `lab/02_eda_feature_interpretation.ipynb`의 실행 output에서 확인할 수 있다. 해당 그래프는 서렌 패배 class가 소수 class임을 보여준다.

### 6.2 Feature EDA: 서렌 패배 팀과 비서렌 팀의 15분 상태 차이

서렌 패배 row와 비서렌 row의 feature 평균을 비교하면, 서렌 패배 팀은 15분 시점에서 전반적으로 불리한 상태에 놓여 있었다.

| Feature | 비서렌 row 평균 | 서렌 패배 row 평균 | 해석 |
| --- | ---: | ---: | --- |
| `gold_diff_15` | 739.1 | -3550.9 | 서렌 패배 팀은 평균 3,550골드 불리 |
| `kill_diff_15` | 1.27 | -6.10 | 평균 6킬가량 뒤처짐 |
| `tower_diff_15` | 0.19 | -0.89 | 포탑 손실이 더 큼 |
| `dragon_diff_15` | 0.13 | -0.63 | 드래곤 오브젝트 손실 경향 |
| `cs_diff_15` | 6.81 | -32.70 | 라인/정글 성장 격차 존재 |
| `avg_level_diff_15` | 0.10 | -0.50 | 평균 레벨도 뒤처짐 |
| `first_blood` | 0.04 | -0.18 | 상대 선취점 비율이 높음 |
| `first_tower` | 0.10 | -0.47 | 상대 첫 포탑 비율이 높음 |
| `ward_placed_diff_15` | 0.30 | -1.42 | 시야 설치량도 다소 낮음 |
| `ward_kill_diff_15` | 0.16 | -0.76 | 시야 제거량도 다소 낮음 |

라벨과 feature의 단순 상관을 보면 절댓값 기준으로 `gold_diff_15`, `kill_diff_15`, `avg_level_diff_15`, `tower_diff_15`, `cs_diff_15`, `first_tower`, `dragon_diff_15` 순서로 강한 신호를 보였다. 이번 run에서는 `rift_herald_diff_15`의 값이 모두 0으로 관측되어 모델 구분 신호로 작동하지 않았다.

Figure 2~3에 해당하는 feature mean difference와 correlation heatmap은 `lab/02_eda_feature_interpretation.ipynb`의 실행 output에서 확인할 수 있다. 서렌 패배 팀은 포탑·드래곤 등 주요 오브젝트에서도 불리한 경향을 보이며, 골드·킬·CS·레벨 등 초반 성장 지표가 서로 연결되어 있음을 확인할 수 있다.

최종 F1 균형 Random Forest 후보의 impurity 기반 feature importance와 permutation importance를 함께 확인했다. Impurity importance에서는 `gold_diff_15`, `kill_diff_15`, `avg_level_diff_15`, `cs_diff_15`가 상위권이었다. Test set에서 average precision 기준 permutation importance를 계산했을 때도 `gold_diff_15`와 `kill_diff_15`가 가장 큰 감소를 만들었다.

| Feature | RF impurity importance | Test permutation importance(AP 감소) |
| --- | ---: | ---: |
| `gold_diff_15` | 0.290 | 0.115 |
| `kill_diff_15` | 0.175 | 0.040 |
| `avg_level_diff_15` | 0.127 | 0.004 |
| `cs_diff_15` | 0.122 | 0.003 |
| `ward_placed_diff_15` | 0.072 | 0.009 |
| `tower_diff_15` | 0.060 | -0.001 |
| `dragon_diff_15` | 0.055 | 0.014 |
| `ward_kill_diff_15` | 0.055 | 0.007 |
| `first_tower` | 0.029 | 0.003 |
| `first_blood` | 0.015 | 0.002 |
| `rift_herald_diff_15` | 0.000 | 0.000 |

Impurity importance는 feature 분산과 tree split 구조의 영향을 받을 수 있으므로 절대적인 인과 효과로 해석하지 않는다. 다만 EDA, permutation importance, 모델 성능을 함께 보면 15분 골드·킬·성장 격차가 서렌 패배 예측의 중심 신호라는 결론은 일관된다.

### 6.3 골드 차이에 따른 서렌 패배 비율

15분 골드 차이를 구간화하면 골드 열세가 커질수록 서렌 패배 비율이 뚜렷하게 증가했다.

| 15분 골드 차이 구간 | Row 수 | 서렌 패배 비율 |
| --- | ---: | ---: |
| -5,000 이하 | 574 | 50.2% |
| -5,000 ~ -3,000 | 566 | 31.3% |
| -3,000 ~ -1,500 | 635 | 24.4% |
| -1,500 ~ 0 | 750 | 14.0% |
| 0 ~ 1,500 | 750 | 10.9% |
| 1,500 ~ 3,000 | 635 | 6.8% |
| 3,000 ~ 5,000 | 566 | 2.8% |
| 5,000 초과 | 574 | 0.7% |

이 결과는 15분 골드 차이가 서렌 패배 흐름을 설명하는 핵심 지표임을 보여준다. 다만 골드 차이는 킬, CS, 포탑, 오브젝트 손실의 결과를 함께 반영하므로, 골드 차이만을 독립적인 원인으로 해석해서는 안 된다.

또한 이 표의 row 수가 음수 구간과 양수 구간에서 대칭적으로 나타나는 것은 데이터가 한 경기당 두 팀 row를 갖기 때문이다. 한 경기에서 블루 팀이 `gold_diff_15=-3000`이면 레드 팀 row는 `gold_diff_15=3000`을 갖는다. 따라서 이 표의 핵심은 양쪽 표본 수의 대칭 자체가 아니라, 골드 열세가 커질수록 서렌 패배 비율이 단조적으로 증가한다는 점이다.

Figure 4에 해당하는 15분 골드 차이 구간별 서렌 패배 비율 그래프는 `lab/02_eda_feature_interpretation.ipynb`의 bucket-rate 실행 output에서 확인할 수 있다. 골드 열세가 커질수록 positive 비율이 증가한다.

### 6.4 Baseline 모델 성능

Baseline test 성능은 다음과 같다.

| 모델 | Accuracy | F1 | Precision | Recall | ROC-AUC | PR-AUC | Confusion Matrix |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| Dummy | 0.818 | 0.000 | 0.000 | 0.000 | 0.500 | 0.182 | `[[826, 0], [184, 0]]` |
| Logistic Regression | 0.726 | 0.494 | 0.372 | 0.734 | 0.810 | 0.494 | `[[598, 228], [49, 135]]` |
| Random Forest | 0.834 | 0.408 | 0.580 | 0.315 | 0.785 | 0.477 | `[[784, 42], [126, 58]]` |
| HistGradientBoosting | 0.815 | 0.305 | 0.482 | 0.223 | 0.745 | 0.386 | `[[782, 44], [143, 41]]` |

Dummy baseline은 test accuracy 0.818을 기록했지만 실제 서렌 패배 184건 중 0건을 잡았다. 따라서 이 문제에서 accuracy만으로 모델을 평가하면 잘못된 결론을 낼 수 있다.

Logistic Regression은 test recall 0.734로 실제 서렌 패배 184건 중 135건을 잡았다. 반면 false positive가 228건으로 많아 precision은 0.372에 머물렀다. 즉, 위험 신호를 넓게 잡는 모델이다.

Random Forest baseline은 accuracy와 precision이 높았지만 recall은 0.315였다. 이는 확실한 서렌 패배 상황만 보수적으로 잡고, 애매한 위험 상황을 많이 놓쳤다는 의미이다.

Figure 5에 해당하는 baseline 모델별 지표 비교 그래프는 `lab/03_modeling_threshold.ipynb`의 metric comparison 실행 output에서 확인할 수 있다. Accuracy와 positive class 탐지 성능이 서로 다르게 움직임을 보여준다.

### 6.5 1차 하이퍼파라미터 튜닝 결과

1차 튜닝에서는 11개 feature를 고정하고 60개 후보를 비교했다. validation F1 기준 상위 후보는 대부분 Random Forest였다.

| 순위 | 모델 | 주요 설정 | Valid F1 | Test F1 | Test Precision | Test Recall | Test PR-AUC |
| ---: | --- | --- | ---: | ---: | ---: | ---: | ---: |
| 1 | Random Forest | `n_estimators=500`, `max_depth=8`, `min_samples_leaf=5`, `class_weight=balanced` | 0.507 | 0.519 | 0.433 | 0.647 | 0.499 |
| 2 | Random Forest | `n_estimators=500`, `max_depth=8`, `min_samples_leaf=2`, `class_weight=balanced` | 0.505 | 0.517 | 0.438 | 0.630 | 0.497 |
| 3 | Random Forest | `n_estimators=300`, `max_depth=8`, `min_samples_leaf=5`, `class_weight=balanced` | 0.504 | 0.512 | 0.429 | 0.636 | 0.499 |
| 5 | Random Forest | `n_estimators=300`, `max_depth=6`, `min_samples_leaf=2`, `class_weight=balanced` | 0.496 | 0.516 | 0.412 | 0.690 | 0.502 |
| 6 | Logistic Regression | `C=0.1`, `class_weight=balanced` | 0.493 | 0.495 | 0.372 | 0.739 | 0.493 |

가장 중요한 변화는 Random Forest의 recall 개선이다. Baseline Random Forest는 test recall 0.315였지만, 튜닝 후 상위 후보는 test recall 0.647까지 상승했다. 즉, Random Forest가 “확실한 서렌 패배만 잡는 보수적 모델”에서 “불리한 흐름을 더 넓게 잡는 모델”로 바뀌었다.

### 6.6 2차 feature set 비교 결과

2차 실험에서는 feature 묶음별로 성능을 비교했다.

| Feature set | 구성 | Test F1 | Test Recall | Test PR-AUC | 해석 |
| --- | --- | ---: | ---: | ---: | --- |
| `all_11_features` | 전체 11개 | 0.526 | 0.636 | 0.498 | 최종 후보로 가장 안정적 |
| `no_vision` | 시야 feature 제외 | 0.497 | 0.625 | 0.479 | validation은 좋았지만 test에서 하락 |
| `economy_only` | 골드, CS, 평균 레벨 | 0.482 | 0.625 | 0.457 | 경제 차이만으로도 신호 존재 |
| `combat_objective` | 킬, 포탑, 오브젝트, 선취점 | 0.475 | 0.712 | 0.471 | recall은 높지만 오탐 가능성 큼 |

`all_11_features`가 test F1 기준으로 가장 안정적이었다. `economy_only`도 의미 있는 성능을 보여 골드·CS·레벨이 핵심 신호임을 확인했다. `combat_objective`는 recall이 높아 위험 탐지는 넓게 수행하지만, precision이 낮아질 가능성이 있어 단독 최종 후보로는 조심스럽다. 여기서 `all_11_features`의 test F1 0.526은 feature 묶음 비교 단계의 best test score이고, 다음 절의 Random Forest F1 0.522는 validation 기준으로 threshold와 운영 track까지 고정한 최종 후보의 hold-out score이다. 선택 기준이 다르므로 두 값은 모순이 아니라 실험 단계 차이로 보아야 한다.

### 6.7 3차 최종 후보 비교

3차 실험에서는 전체 11개 feature를 고정하고, F1 균형 후보와 recall 중심 후보를 나누어 threshold까지 비교했다.

핵심 후보는 다음과 같다.

| Track | 모델 | Threshold | Valid F1 | Test F1 | Test Precision | Test Recall | Test PR-AUC | 해석 |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| F1 균형 | Random Forest | 0.50 | 0.523 | 0.522 | 0.438 | 0.647 | 0.497 | 최종 단일 모델 후보 |
| Recall 중심 | Logistic Regression | 0.55 | 0.501 | 0.509 | 0.414 | 0.663 | 0.493 | 서렌 위험 탐지 보조 후보 |
| 극단 Recall | Logistic Regression | 0.30 | 0.416 | 0.419 | 0.270 | 0.935 | 0.494 | 많은 서렌 패배를 잡지만 오탐 과다 |
| 높은 precision 쪽 | Random Forest | 0.60 | 0.535 | 0.503 | 0.511 | 0.495 | 0.503 | 오탐을 줄이나 recall 하락 |

위 표의 후보는 모두 validation set에서 threshold를 비교해 선정한 뒤, test set으로 최종 확인한 결과이다. 예를 들어 F1 균형 Random Forest는 validation recall이 0.60 이상인 후보 중 validation F1이 높은 설정을 선택했고, recall 중심 Logistic Regression은 validation recall이 0.70 이상인 후보 중 validation F1이 높은 설정을 선택했다. Test set의 F1과 recall은 선택 이후의 hold-out 평가값이다.

최종 F1 균형 후보의 상세 설정은 다음과 같다.

```text
Model: Random Forest
Track: f1_balanced
n_estimators: 500
max_depth: 10
min_samples_leaf: 10
max_features: sqrt
class_weight: balanced_subsample
threshold: 0.50
valid_f1: 0.523
test_f1: 0.522
test_precision: 0.438
test_recall: 0.647
test_pr_auc: 0.497
```

Test confusion matrix는 다음과 같다.

```text
actual negative: 826
actual positive: 184
true negatives: 673
false positives: 153
false negatives: 65
true positives: 119
```

Recall 중심 Logistic Regression 대안은 다음과 같다.

```text
Model: Logistic Regression
Track: recall_oriented
C: 0.05
class_weight: balanced
threshold: 0.55
valid_f1: 0.501
test_f1: 0.509
test_precision: 0.414
test_recall: 0.663
test_pr_auc: 0.493
```

Test confusion matrix는 다음과 같다.

```text
actual negative: 826
actual positive: 184
true negatives: 653
false positives: 173
false negatives: 62
true positives: 122
```

Figure 6~7에 해당하는 confusion matrix와 precision-recall trade-off는 최종 제출에서는 별도 이미지 파일 대신 `lab/03_modeling_threshold.ipynb`의 실행 표와 threshold 비교 cell로 재현한다. 서렌 패배 class가 소수 class이므로 ROC뿐 아니라 PR-AUC, precision, recall, F1을 함께 확인했다.

### 6.8 초기 `team_surrendered` 결과 요약

초기 실험에서 최종 모델을 하나만 제시해야 한다면 Random Forest F1 균형 후보가 가장 적절했다. 이 모델은 validation과 test F1 gap이 0.001로 작고, 실제 서렌 패배 184건 중 119건을 잡으면서 false positive도 recall 중심 후보보다 적게 유지했다.

그러나 “서렌 위험을 놓치지 않는 것”이 더 중요한 분석 목적이라면 Logistic Regression recall 중심 후보도 의미가 있다. 이 후보는 실제 서렌 패배 184건 중 122건을 잡아 Random Forest보다 3건 더 많이 포착했지만, false positive가 20건 더 많았다. 따라서 두 모델의 차이는 단순 성능 차이가 아니라 운영 기준의 차이로 해석해야 한다.

다만 이 결과는 동시에 중요한 한계도 보여준다. 초기 target인 `team_surrendered`는 경기 상태뿐 아니라 패배 팀이 실제로 서렌을 선택했는지라는 행동 요인을 포함한다. 따라서 test F1 0.52대의 성능은 feature가 무의미하다는 뜻이 아니라, “15분 상태 → 서렌 선택” 사이에 15분 이후 사건, 플레이어 성향, 팀 분위기, 조합 scaling 같은 관측되지 않은 요인이 많이 남아 있다는 뜻으로 해석해야 한다.

### 6.9 설명력 보강 후속 실험: final-loss / Dead Game 위험

교수님 피드백 이후 후속 실험에서는 같은 계열의 15분 feature가 최종 패배 위험을 얼마나 설명하는지 검증했다. 이 절의 비교는 **성능 향상 표**가 아니라 **문제정의 전환과 feature 보강의 시계열적 근거 표**이다. 초기 후보와 후속 후보는 target, dataset, feature set, seed 수가 함께 달라졌기 때문에 “동일 조건에서 모델만 바꿔 F1이 0.522에서 0.786으로 올랐다”고 해석하면 안 된다. 다만 label reframing audit에서는 원래 서렌 label과 `final_loss`를 같은 core-rule feature 계열로 비교했을 때 surrender-loss F1 0.5229/PR-AUC 0.5062에서 final-loss F1 0.7652/PR-AUC 0.8506으로 바뀌어, target 자체의 noise 차이가 크다는 근거를 제공한다[17].

`final_loss`는 한 경기의 두 팀 중 패배 팀 1행이 positive가 되므로 양성률이 50.0%이다. 따라서 majority Dummy의 accuracy는 약 0.50이고, 모든 row를 positive로 찍는 단순 기준선의 F1은 약 0.667이다. 이 때문에 final-loss 실험에서는 F1뿐 아니라 PR-AUC와 ROC-AUC를 함께 보아야 한다. 양성률 50% 문제에서 무작위 ranking의 PR-AUC 기준선은 약 0.50이며, 최종 L1 LR 후보들은 PR-AUC 0.849~0.858, ROC-AUC 0.847~0.859를 기록했다.

| 구분 | Target | 대표 모델/feature | 평가 방식 | F1 | Precision | Recall | PR-AUC | ROC-AUC | 해석 |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| 초기 최종 후보 | `team_surrendered` | tuned Random Forest | hold-out test | 0.522 | 0.438 | 0.647 | 0.497 | - | 서렌 행동 label 기준선 |
| label reframing audit | `final_loss` | core-rule L1 LR | hold-out test | 0.7652 | - | - | 0.8506 | - | 같은 feature 계열에서 target noise 차이 확인 |
| data3 compact 설명 후보 | `final_loss` | 12-feature `core_rule_lolalytics_12_pruned` L1 LR | 10-seed group split | 0.7716 ± 0.0119 | 0.7020 | 0.8594 | 0.8490 ± 0.0149 | 0.8473 ± 0.0143 | feature 수를 줄여 설명력 강화 |
| data3 prior 성능 track | `final_loss` | flow+counter+external game-length prior L1 LR | 5-seed group split | 0.775 | 0.713 | 0.855 | 0.850 | 0.852 | data3 기준 방향 전환 근거 |
| KMeans archetype 후보 | `final_loss` | flow+archetype L1 LR | 5-seed group split | 0.7821 ± 0.0128 | 0.7181 | 0.8602 | 0.8583 | 0.8592 | 조합 archetype 추가 효과 |
| 최종 interaction 후보 | `final_loss` | flow+counter+external game-length prior+archetype+interaction L1 LR | 5-seed group split | **0.7855 ± 0.0122** | **0.7198** | **0.8653** | **0.8584** | **0.8592** | 최종 설명력/성능 후보 |

이 표에서 중요한 점은 서렌 여부 자체의 F1을 0.95 수준으로 끌어올린 것이 아니라, 문제정의를 더 정확히 분리했다는 점이다. 15분 상태는 플레이어가 실제로 서렌 버튼을 누르는지보다, 그 팀이 최종적으로 패배할 위험을 훨씬 안정적으로 설명했다. 최종 interaction 후보의 `game-length prior`는 실제 경기 길이 feature가 아니라 Lolalytics의 champion-position 시간대별 평균 승률 profile이다. 즉, 해당 match가 몇 분에 끝났는지 또는 어떤 duration bucket에 속했는지를 모델이 본 것이 아니다.

12-feature compact 후보는 `gold_deficit_15`, `xp_deficit_15`, `dragon_deficit_15`, `tower_deficit_15`, `kill_deficit_15`, `health_deficit_15`, `damage_taken_excess_15`, `rule_tower_deficit_2`, `rule_economy_combat_pressure`, `rule_gold_worsening_1k`, `lolalytics_weighted_wr_deficit`, `lolalytics_early_wr_deficit`만 사용한다. 단일 hold-out split에서는 test confusion matrix `[[342, 163], [77, 428]]`을 기록했고, 10-seed 평균에서도 PR-AUC 0.8490을 유지했다. 65-feature 성능 track보다 단순하지만 핵심 위험 신호가 계수와 rule로 설명되므로, 수업 프로젝트의 설명력 요구에 더 적합하다.

최종 interaction 후보는 KMeans champion-position archetype과 제한적 interaction feature를 추가한 L1 Logistic Regression이다. L1 규제 때문에 평균 non-zero coefficient는 32.4개 수준으로 줄어들어, 256개 후보 feature를 모두 설명 변수로 고정 사용하는 방식보다 해석 부담이 낮다. LightGBM과 XGBoost도 실험했지만 XGBoost는 F1 0.773, PR-AUC 0.849 수준으로 기존 L1/KMeans 후보를 넘지 못했다[11][12]. 따라서 본 보고서의 최종 모델 계열은 복잡한 boosting이 아니라 설명 가능한 Logistic Regression 중심으로 유지한다[18].

### 6.10 최종 결과 해석

최종 결과는 다음 세 문장으로 요약할 수 있다.

1. 15분 상태만으로 일반 서렌 선택 자체를 고성능으로 예측하기는 어렵다.
2. 그러나 15분 골드, 성장, 오브젝트, 전투 압력, 조합 prior는 최종 패배/Dead Game 위험을 높은 수준으로 설명한다.
3. 따라서 프로젝트의 의의는 “서렌 추천기”가 아니라 “15분 상태 기반 패배 위험 신호를 설명 가능한 방식으로 분석한 모델”에 있다.

---

## 7. Analysis / Discussion

### 7.1 왜 골드 차이가 강한 신호인가

15분 골드 차이는 킬, CS, 포탑, 오브젝트, 라인전 손실이 합쳐진 종합 지표이다. EDA에서 서렌 패배 팀의 평균 `gold_diff_15`는 -3550.9였고, 비서렌 row의 평균은 739.1이었다. 또한 15분 골드가 5,000 이상 불리한 구간에서는 서렌 패배 비율이 50.2%까지 상승했다.

이 결과는 골드 차이가 단순히 “현재 불리함”을 나타내는 것이 아니라, 플레이어가 경기 복구 가능성을 낮게 판단하는 데 영향을 주는 복합 신호일 수 있음을 보여준다. 다만 골드 차이는 여러 원인의 결과이므로, 골드 차이 자체가 서렌의 직접 원인이라고 단정할 수는 없다.

### 7.2 교전과 오브젝트 지표의 역할

`kill_diff_15`, `tower_diff_15`, `dragon_diff_15`, `first_tower` 역시 서렌 패배와 음의 상관을 보였다. 킬 차이는 초반 교전 손실을, 포탑 차이는 라인전 붕괴와 맵 주도권 상실을, 드래곤 차이는 오브젝트 주도권 상실을 나타낸다.

특히 `combat_objective` feature set은 test recall이 높았다. 이는 킬과 오브젝트 손실이 서렌 위험을 넓게 감지하는 데 유용하다는 뜻이다. 그러나 recall이 높아지는 모델은 false positive도 증가할 수 있으므로, 실제 운영에서는 위험 알림의 목적과 오탐 비용을 함께 고려해야 한다.

### 7.3 경제 지표만으로도 의미 있는 예측이 가능함

`economy_only` feature set은 골드, CS, 평균 레벨만 사용했음에도 test F1 0.482, recall 0.625를 기록했다. 이는 복잡한 이벤트 feature 없이도 15분 경제 상태가 서렌 패배 흐름을 상당 부분 설명한다는 의미이다. 특히 CS와 평균 레벨은 킬 스코어보다 덜 극적인 지표이지만, 라인전 지속 손실과 성장 격차를 안정적으로 반영한다.

### 7.4 시야 feature의 제한적 효과

시야 feature를 제외한 `no_vision` 실험은 validation에서는 좋은 결과를 보였지만 test에서는 `all_11_features`보다 낮았다. 이번 데이터에서는 시야 설치/제거 차이가 강한 핵심 신호라기보다 보조 신호로 작동한 것으로 해석된다. 다만 시야 지표는 플레이어 티어, 포지션, 게임 시간대, 서포터 행동 양식에 따라 의미가 달라질 수 있으므로 더 세분화된 분석이 필요하다.

### 7.5 Accuracy 착시와 positive class 중심 평가

Dummy baseline은 test accuracy 0.818을 보였지만, 실제 서렌 패배를 하나도 잡지 못했다. 이 결과는 class imbalance 문제에서 accuracy가 얼마나 오해를 만들 수 있는지를 보여준다. 본 프로젝트의 목표가 “서렌 패배 팀 탐지”라면, 모델은 positive class를 어느 정도 잡아야 한다. 따라서 최종 판단에서는 F1, recall, PR-AUC, confusion matrix를 함께 사용했다.

### 7.6 Threshold trade-off

Threshold를 조정하면 precision과 recall의 균형이 크게 바뀐다. Logistic Regression threshold 0.30 후보는 test recall 0.935로 실제 서렌 패배 184건 중 172건을 잡았지만, false positive가 465건으로 크게 증가했다. 이는 거의 모든 불리한 흐름을 위험으로 표시하는 방식에 가깝다.

반대로 Random Forest threshold 0.60 후보는 precision을 0.511까지 높였지만 recall이 0.495로 낮아졌다. 즉, 오탐을 줄이는 대신 실제 서렌 패배 팀을 더 많이 놓친다.

이 프로젝트에서 최종 모델을 하나로 제시할 때는 F1 균형 Random Forest가 적절하지만, 실제 서비스나 분석 목적에서는 threshold를 고정값으로만 볼 필요가 없다. “위험 조기 경보” 목적이라면 recall 중심 threshold를, “높은 확신의 위험 상황 식별” 목적이라면 precision 중심 threshold를 선택할 수 있다.

### 7.7 오분류 해석

최종 Random Forest 후보의 false negative 65건은 실제로는 서렌 패배했지만 모델이 위험하지 않다고 판단한 사례이다. 이러한 사례는 15분 시점에는 지표가 극단적으로 불리하지 않았으나, 15분 이후 한타 패배나 오브젝트 손실로 급격히 무너진 경기일 가능성이 있다. 또한 팀 내부 갈등, 조합 상성, 특정 챔피언 성장, 멘탈 요인 등 15분 feature로 포착하기 어려운 요인이 작용했을 수 있다.

False positive 153건은 모델이 서렌 위험으로 판단했지만 실제로는 일반 서렌 패배하지 않은 사례이다. 이는 15분 시점에 불리했으나 역전했거나, 불리한 상태에서도 끝까지 플레이한 경기일 수 있다. 따라서 false positive는 단순 오류라기보다 “서렌 위험은 있었지만 실제 서렌으로 이어지지 않은 경기”로 해석할 여지가 있다.

### 7.8 산업적 활용 가능성

이 모델은 단순한 승패 예측기를 넘어, 플레이어 경험 분석 도구로 활용될 수 있다. 특정 feature가 서렌 가능성과 강하게 연결된다면, 게임 밸런스 또는 유저 경험 측면에서 다음 질문을 던질 수 있다.

- 15분 골드 차이가 일정 수준을 넘으면 복구 가능성이 지나치게 낮게 체감되는가?
- 첫 포탑 또는 드래곤 손실이 플레이어의 포기 의사에 얼마나 영향을 주는가?
- 특정 티어 또는 패치에서 서렌 패턴이 달라지는가?
- 조기 경고 시스템이 있다면 어떤 threshold가 적절한가?

다만 이 분석은 관찰 데이터 기반 예측이므로, 특정 feature가 서렌을 직접 유발한다고 주장할 수는 없다. 인과적 주장을 위해서는 패치 버전, 티어, 챔피언 조합, 포지션, 팀 조합, 플레이어 행동 로그 등 추가 변수가 필요하다.

### 7.9 왜 final-loss 문제정의가 더 설득력 있는가

초기 target인 `team_surrendered`는 “패배했고, 그 패배가 일반 서렌으로 끝났는가”를 나타낸다. 이 target은 경기 상태와 플레이어 행동이 결합된 label이다. 같은 15분 상태라도 어떤 팀은 끝까지 플레이하고, 어떤 팀은 서렌을 선택할 수 있다. 따라서 모델이 보는 15분 feature만으로는 서렌 선택의 모든 요인을 설명하기 어렵다.

반면 `final_loss`는 15분 상태가 실제 경기 결과와 얼마나 연결되는지 보는 target이다. 후속 실험에서 final-loss F1과 PR-AUC가 크게 상승한 것은 feature 설정 자체가 잘못된 것이 아니라, 초기 label이 행동 noise를 많이 포함하고 있음을 보여준다. 다만 이 상승은 target, dataset, feature set이 함께 바뀐 결과이므로 순수한 모델 교체 효과로 과장하지 않는다. 이 때문에 최종 보고서에서는 `team_surrendered` 실험을 초기 기준선으로 제시하고, 프로젝트 의의는 `final_loss`/Dead Game 위험 설명으로 정리한다.

### 7.10 설명력 중심 최종 모델 선택

최종 모델을 더 복잡한 딥러닝이나 boosting으로 바꾸지 않은 이유는 성능과 설명력의 균형 때문이다. 딥러닝 계열은 Random Forest 또는 Logistic Regression 대비 뚜렷한 우위를 보이지 않았고, XGBoost/LightGBM도 최종 L1/KMeans 후보보다 낮았다. 반면 L1 Logistic Regression은 coefficient, odds ratio, scorecard, risk decile로 설명이 가능하다.

따라서 교수님이 지적한 “설명력이 낮으면 ML 프로젝트 의의가 흔들린다”는 문제에 대해, 본 프로젝트는 다음처럼 답한다. 단순히 모델 복잡도를 높여 점수를 올리는 것이 아니라, 15분 경기 상태가 어떤 위험 신호를 통해 최종 패배와 연결되는지 설명 가능한 feature와 선형 모델로 제시한다.

---

## 8. Reproducibility and Collaboration

### 8.1 재현 가능한 산출물

본 프로젝트는 원격 저장소에 올릴 산출물과 로컬 실험 산출물을 분리한다. 개인별 실험 markdown, 작은 summary CSV/JSON, 모델 바이너리, 실행 output은 커밋하지 않고, 필요한 실험 내용은 `lab/` notebook과 최종 보고서에 통합했다.

| 산출물 | 경로 |
| --- | --- |
| 프로젝트 개요 | `README.md` |
| 데이터 계약 | `docs/data_contract.md` |
| 개발/재현 가이드 | `docs/development_guide.md` |
| 최종 보고서 | `Report/Submission/Team2_report.md` |
| 공통 검증/EDA/modeling notebook | `lab/01_data_validation.ipynb` ~ `lab/04_submission_report_analysis.ipynb` |
| 범준 실험 notebook | `lab/05_bumjun_baseline_feature_expansion.ipynb` ~ `lab/09_bumjun_data3_compact_l1_explainability.ipynb` |
| 승범 실험 notebook | `lab/10_seungbeom_rf_tuning_initial_limit.ipynb` ~ `lab/14_seungbeom_kmeans_interaction_advanced_check.ipynb` |
| 초기 baseline 데이터 | `data_1/processed/riot/riot-scale-2600_team_features.csv` |
| temporal/counter 중간 데이터 | `data_2/processed/riot/` |
| 최종 v16.9 데이터 | `data_3/processed/riot/` |

### 8.2 검증 결과

최종 정리 후 다음 검증을 수행했다.

- `lab/` notebook 14개 전체 실행 완료
- 각 notebook code cell 실행 output에 error 없음
- `lab/`과 `README.md`에서 구 버전별 notebook 경로 제거
- 개인 실험 workspace 경로를 notebook 재현 경로로 사용하지 않도록 정리
- feature/label 단위 테스트와 group split leakage 방지 테스트 통과

테스트 명령과 결과는 다음과 같다.

```bash
PYTHONPYCACHEPREFIX=/tmp/team2_pycache PYTHONPATH=src python3 -m unittest discover -s tests -v
```

검증 결과는 `Ran 4 tests ... OK`였다.

### 8.3 Notebook 버전 관리

분석 notebook은 기존 버전별 notebook 관리 방식에서 공식 제출 폴더인 `lab/`로 마이그레이션했다. 파일명은 시간순 실험 흐름과 담당자별 개선 과정을 동시에 보여주도록 구성했다.

| 단계 | File | Purpose |
| --- | --- | --- |
| 공통 01 | `lab/01_data_validation.ipynb` | 초기 데이터 규모/품질 검증 |
| 공통 02 | `lab/02_eda_feature_interpretation.ipynb` | EDA와 feature 해석 |
| 공통 03 | `lab/03_modeling_threshold.ipynb` | baseline 모델과 threshold tuning |
| 공통 04 | `lab/04_submission_report_analysis.ipynb` | 공통 결과와 최종 보고서 연결 |
| 범준 05~09 | `lab/05_bumjun_*` ~ `lab/09_bumjun_*` | feature 확장, MLP 상한, label 재정의, 안정성, compact L1 설명 모델 |
| 승범 10~14 | `lab/10_seungbeom_*` ~ `lab/14_seungbeom_*` | RF tuning, counter/MLP, final_loss scorecard, Lolalytics context, KMeans/advanced check |

### 8.4 역할 분담

프로젝트 역할 분담은 다음과 같다.

| 담당자 | 주요 역할 | 산출물 |
| --- | --- | --- |
| 정민기 | Git/PR 운영, README, notebook/report 정리 | PR template, 프로젝트 문서, Jupyter 분석 notebook, README |
| 송재혁 | 분석 데이터 기준, feature/label, validation, test | `docs/data_contract.md`, feature/label 로직, 검증 스크립트, fixture test |
| 손범준 | Riot 수집과 Supabase 업로드 파이프라인 | Riot API 수집 스크립트, Supabase upload 스크립트 |
| 양승범 | 모델 학습과 EDA 파이프라인 | baseline 모델 학습, EDA figure 생성, metric 산출 |

PR 리뷰 기록은 `docs/pr_review_record.md`에 남겼으며, 데이터 계약과 Supabase schema 관련 PR은 label leakage 방지, 개인정보 제외, feature version 관리 기준을 중심으로 검토되었다.

---

## 9. Limitations and Future Work

### 9.1 데이터 규모와 표본 편향

최종 데이터셋은 2,525경기, 5,050 team rows로 구성되어 의미 있는 baseline 분석은 가능하지만, 전체 랭크 게임을 대표한다고 보기는 어렵다. 수집 seed가 특정 티어와 서버 설정에 기반하므로, 다른 티어·서버·패치 기간에서는 서렌 패턴이 달라질 수 있다.

### 9.2 관찰 데이터의 인과 해석 한계

본 프로젝트는 15분 feature와 최종 서렌 패배 라벨 사이의 상관 및 예측 가능성을 분석했다. 따라서 골드 차이나 킬 차이가 서렌을 직접 유발한다고 단정할 수 없다. 예를 들어 골드 차이는 라인전, 정글 개입, 오브젝트, 챔피언 조합, 플레이어 심리 등 여러 요인의 결과일 수 있다.

### 9.3 15분 이후 이벤트 미포함

모델은 의도적으로 15분 이후 이벤트를 보지 않는다. 이는 leakage를 막기 위한 장점이지만, 15분 이후 한타나 오브젝트 교전으로 급격히 무너지는 경기를 설명하기 어렵다는 한계도 만든다. False negative 사례 중 일부는 15분 시점에는 불리하지 않았으나 이후 급격히 패배 흐름으로 전환된 경기일 수 있다.

### 9.4 Feature granularity 한계

현재 feature는 팀 단위 aggregate이다. 포지션별 CS/레벨 차이, 챔피언 조합, 스케일링 조합, 특정 라인의 붕괴 여부, 정글 동선, 플레이어 티어, 파티 여부 등은 포함하지 않았다. 이러한 feature가 추가되면 “왜 서렌으로 이어졌는가”를 더 세밀하게 해석할 수 있다.

### 9.5 전령 feature의 제한

이번 `riot-scale-2600` run에서는 `rift_herald_diff_15`가 모두 0으로 관측되어 모델 신호로 작동하지 않았다. raw timeline 스캔 결과, 15분 이전에는 `RIFTHERALD`가 아니라 `HORDE` 이벤트가 7,626건 기록되어 있었다. 따라서 현재 feature명은 과거 전령 중심 오브젝트 정의를 따르지만, 실제 15분 이전 상단 오브젝트 신호는 공허 유충에 해당하는 `HORDE`로 별도 추출해야 한다. 후속 실험에서는 `horde_diff_15`를 추가하고 기존 `rift_herald_diff_15`는 15분 기준 feature에서 제외하거나, 20분 기준 feature로 이동하는 것이 더 적절하다.

### 9.6 Target 정의와 문제정의의 한계

초기 target인 `team_surrendered`는 최종 패배 여부와 서렌 선택 행동이 결합된 label이다. 따라서 이 label에서 성능이 낮게 나온다고 해서 15분 feature 설정이 전부 잘못되었다고 결론낼 수는 없다. 후속 final-loss 실험에서 성능이 크게 오른 것은, 같은 feature가 최종 패배 위험은 잘 설명하지만 서렌 선택 행동에는 관측되지 않은 요인이 많다는 점을 보여준다.

본 보고서는 이 차이를 한계이자 주요 발견으로 다룬다. 즉, 모델은 “15분에 서렌해야 하는가”를 직접 추천하지 않는다. 대신 “15분 상태가 최종 패배 위험과 어떤 방식으로 연결되는가”를 설명한다. 이 구분을 유지하지 않으면 모델의 활용 범위가 과장될 수 있다.

### 9.7 후속 연구 방향

후속 분석으로는 다음을 제안한다.

1. 패치 버전별 서렌 패턴 비교
2. 티어별 서렌 패턴 비교
3. 챔피언/포지션 조합 feature 추가
4. 10분, 15분, 20분 feature를 비교하는 시간대별 모델링
5. SHAP 또는 permutation importance 기반 feature 영향 재검증
6. calibration curve를 통한 확률 예측 신뢰도 검증
7. false positive/false negative match 사례의 정성 분석
8. ARAM, 일반 게임, 자유 랭크 등 다른 queue와 비교

---

## 10. Conclusion

본 프로젝트는 Riot API 기반 랭크 솔로/듀오 경기 데이터를 이용하여, 경기 15분 시점의 팀 단위 지표가 일반 서렌 패배와 최종 패배 위험을 얼마나 설명하는지 분석했다. 초기 데이터셋은 2,525경기, 5,050 match-team rows로 구성되며, `team_surrendered=True` row는 870개였다. Class imbalance가 큰 문제였기 때문에 accuracy만으로 모델을 평가하지 않고 F1, recall, PR-AUC, confusion matrix를 함께 사용했다.

초기 `team_surrendered` 실험에서는 Dummy baseline이 accuracy 0.818을 기록했지만 실제 서렌 패배를 전혀 잡지 못했다. Random Forest는 튜닝 후 test F1 0.522, recall 0.647, precision 0.438을 기록했고, recall 중심 Logistic Regression은 test F1 0.509, recall 0.663, precision 0.414를 기록했다. 이 결과는 15분 상태가 서렌 패배 흐름을 일정 수준 감지할 수 있음을 보여주지만, 동시에 서렌 선택 자체를 고성능으로 예측하는 데는 한계가 있음을 보여준다.

후속 설명력 보강 실험의 핵심 발견은 target을 `final_loss`로 분리했을 때 15분 feature의 설명력이 크게 높아진다는 점이다. 12-feature `core_rule_lolalytics_12_pruned` L1 Logistic Regression은 10-seed 평균 F1 0.7716, PR-AUC 0.8490을 기록했고, `flow_plus_counter_game_length_archetype_interactions` L1 Logistic Regression은 5-seed 평균 F1 0.7855, PR-AUC 0.8584를 기록했다. 이는 feature 설정 자체가 무의미한 것이 아니라, 초기 서렌 label이 행동 요인을 많이 포함해 난도가 높다는 점을 보여준다. 동시에 두 결과는 target과 feature set이 바뀐 후속 실험이므로, 기존 모델 대비 직접 성능 개선 폭으로 과장하지 않는다.

EDA와 후속 실험은 15분 골드 차이, 성장 격차, 킬 차이, 포탑·드래곤 등 오브젝트 손실, 체력/피해량 압력, champion-position prior가 최종 패배 위험과 반복적으로 연결됨을 보여준다. 특히 L1 Logistic Regression과 scorecard는 어떤 feature가 위험을 높이는지 계수와 rule point로 설명할 수 있어, 단순히 점수만 높은 모델보다 수업 프로젝트의 설명력 요구에 더 잘 맞는다.

결론적으로 본 프로젝트의 최종 의의는 “15분에 서렌해야 하는지 추천하는 모델”이 아니라, “15분 경기 상태가 최종 패배/Dead Game 위험과 어떻게 연결되는지 설명 가능한 방식으로 분석한 모델”에 있다. 다만 본 결과는 관찰 데이터 기반 예측 분석이므로 인과관계로 확대 해석해서는 안 되며, 패치·티어·챔피언·포지션별 추가 분석과 15분 이후 사건을 포함한 후속 연구가 필요하다.

---

## References

### External references

[1] Riot Games. “Riot Developer Portal — Match-V5.” https://developer.riotgames.com/apis#match-v5  
[2] F. Pedregosa et al. “Scikit-learn: Machine Learning in Python.” *Journal of Machine Learning Research*, 12, 2825–2830, 2011.  
[3] L. Breiman. “Random Forests.” *Machine Learning*, 45, 5–32, 2001.  
[4] T. Fawcett. “An introduction to ROC analysis.” *Pattern Recognition Letters*, 27(8), 861–874, 2006.  
[5] T. Saito and M. Rehmsmeier. “The Precision-Recall Plot Is More Informative than the ROC Plot When Evaluating Binary Classifiers on Imbalanced Datasets.” *PLOS ONE*, 10(3), e0118432, 2015.  
[6] scikit-learn developers. “RandomForestClassifier.” https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.RandomForestClassifier.html  
[7] scikit-learn developers. “LogisticRegression.” https://scikit-learn.org/stable/modules/generated/sklearn.linear_model.LogisticRegression.html  
[8] scikit-learn developers. “sklearn.metrics.” https://scikit-learn.org/stable/api/sklearn.metrics.html  
[9] R. Tibshirani. “Regression Shrinkage and Selection via the Lasso.” *Journal of the Royal Statistical Society: Series B*, 58(1), 267–288, 1996.  
[10] J. MacQueen. “Some methods for classification and analysis of multivariate observations.” *Proceedings of the Fifth Berkeley Symposium on Mathematical Statistics and Probability*, 1967.  
[11] T. Chen and C. Guestrin. “XGBoost: A Scalable Tree Boosting System.” *KDD*, 2016.  
[12] G. Ke et al. “LightGBM: A Highly Efficient Gradient Boosting Decision Tree.” *NeurIPS*, 2017.  
[13] Lolalytics. “League of Legends champion statistics and match-up / game length aggregates.” https://lolalytics.com/  

### Internal project references

[14] Team 2 project repository. `README.md`.  
[15] Team 2 project repository. `docs/data_contract.md`.  
[16] Team 2 project repository. `docs/development_guide.md`.  
[17] Team 2 project repository. `lab/01_data_validation.ipynb`.  
[18] Team 2 project repository. `lab/07_bumjun_label_reframing_final_loss.ipynb`.  
[19] Team 2 project repository. `lab/09_bumjun_data3_compact_l1_explainability.ipynb`.  
[20] Team 2 project repository. `lab/13_seungbeom_data3_lolalytics_final_loss.ipynb`.  
[21] Team 2 project repository. `lab/14_seungbeom_kmeans_interaction_advanced_check.ipynb`.  

---

## Appendix A. 주요 재현 명령

아래 명령은 프로젝트 루트(`team-2`) 기준이다.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
PYTHONPATH=src python -m unittest discover -s tests -v
```

최종 제출 notebook은 `lab/`에 있다. Jupyter에서 `01`부터 `14`까지 순서대로 실행하거나, 다음처럼 일괄 실행한다.

```bash
python -m nbconvert --execute --to notebook --inplace lab/*.ipynb
```

데이터 묶음은 다음 기준으로 사용한다.

```text
data_1/processed/riot/riot-scale-2600_team_features.csv
data_2/processed/riot/
data_3/processed/riot/
```

개인 실험 workspace와 모델/output 산출물은 커밋 대상이 아니다. 최종 제출 근거는 `Report/Submission/Team2_report.md`, `README.md`, `docs/`, `data_1~3`, `lab/`, `src/`, `scripts/`, `tests/`를 기준으로 확인한다.
