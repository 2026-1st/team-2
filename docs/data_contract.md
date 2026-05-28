# Riot 서렌 예측 분석 데이터 기준서

이 문서는 Riot API로 만든 LoL 서렌 예측 데이터셋의 포함 기준, 제외 기준, feature, label 정의를 정리한 문서임.
데이터를 수집하거나 feature를 만들 때는 아래 기준을 따름.

## 분석 단위

데이터셋의 한 행은 "한 경기의 한 팀"임.

- 조건을 만족하는 경기 1개에서는 두 행을 만듦. 블루 팀은 `team_id=100`, 레드 팀은 `team_id=200`임.
- 모델에 넣는 feature는 15분 타임라인 프레임 또는 timestamp가 `<= 900000` ms인 이벤트만 사용함.
- 라벨은 경기 종료 상태에서 따로 만들고, feature에는 넣지 않음.

## 포함 / 제외 규칙

아래 조건에 걸리는 경기는 데이터셋에서 제외함.

1. `queue_id != 420`
2. `game_duration_sec < 900`
3. 참가자 중 한 명이라도 `gameEndedInEarlySurrender == true`인 경우
4. 15분 타임라인 프레임이 없는 경우
5. 필수 참가자 프레임 값이 누락된 경우

## 필수 컬럼

### 메타데이터

| 컬럼 | 타입 | 설명 |
| --- | --- | --- |
| `match_id` | string | Riot match id. 예: `KR_...` |
| `team_id` | int | `100`은 블루, `200`은 레드 |
| `feature_version` | string | `v1_15min`부터 시작 |
| `queue_id` | int | 랭크 솔로 게임 기준이므로 반드시 `420` |
| `game_version` | string | Riot 게임 버전 / 패치 문자열 |
| `game_duration_sec` | int | 경기 길이, 초 단위 |
| `collected_at` | timestamp | 수집 또는 처리 시각 |

### 라벨

| 컬럼 | 타입 | 의미 |
| --- | --- | --- |
| `team_surrendered` | bool | 해당 팀이 최종적으로 일반 서렌으로 패배했으면 True |

라벨 규칙:

```text
team_surrendered = true
이 팀이 패배 팀이고, 팀 참가자 중 한 명 이상이 gameEndedInSurrender == true인 경우
```

조기 서렌이나 리메이크에 가까운 경기는 서렌 패배로 세지 않고 제외함.

### 피처

모든 `*_diff_15` 컬럼은 우리 팀 기준의 차이값임.

```text
this_team_value - opponent_team_value
```

| 컬럼 | 타입 | 출처 |
| --- | --- | --- |
| `gold_diff_15` | int | 15분 participantFrames의 totalGold 팀 합 차이 |
| `kill_diff_15` | int | 15분까지 발생한 `CHAMPION_KILL` 이벤트 |
| `tower_diff_15` | int | 15분까지 발생한 포탑 `BUILDING_KILL` 이벤트 |
| `dragon_diff_15` | int | 15분까지 발생한 `ELITE_MONSTER_KILL` / `DRAGON` 이벤트 |
| `rift_herald_diff_15` | int | 15분까지 발생한 `ELITE_MONSTER_KILL` / `RIFTHERALD` 이벤트 |
| `cs_diff_15` | int | 15분 minionsKilled + jungleMinionsKilled 팀 합 차이 |
| `avg_level_diff_15` | float | 15분 기준 팀 평균 레벨 차이 |
| `first_blood` | int | `1`은 이 팀 선취점, `-1`은 상대 팀 선취점, `0`은 15분 전 선취점 없음 |
| `first_tower` | int | `1`은 이 팀 첫 포탑, `-1`은 상대 팀 첫 포탑, `0`은 15분 전 첫 포탑 없음 |
| `ward_placed_diff_15` | int | 15분까지 발생한 `WARD_PLACED` 이벤트, `wardType=UNDEFINED` 제외 |
| `ward_kill_diff_15` | int | 15분까지 발생한 `WARD_KILL` 이벤트, `wardType=UNDEFINED` 제외 |

## 개인정보 제약

가공 데이터나 공유용 데이터에는 아래 정보를 넣지 않음.

- PUUID
- 암호화된 소환사 ID
- 소환사 이름 / Riot ID
- 참가자 이름
- 원본 API key 또는 Supabase key

재현성을 위해 원본 JSON은 gitignore 처리된 `data/raw/riot/` 아래에 로컬로 보관할 수 있음. 다만 공개 산출물에는 팀 단위로 가공한 필드만 사용함.

## 데이터 분할 규칙

모델 학습용 데이터를 나눌 때는 반드시 `match_id` 기준으로 묶어서 split함. 같은 경기에서 나온 블루/레드 행이 train/validation/test에 따로 들어가면 안 됨.
