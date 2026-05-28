# Development Guide

Team 2 Riot 서렌 예측 프로젝트를 로컬에서 실행, 검증, 재현하기 위한 개발 가이드임. 과제 제출용 개요, 문제점, 결과 해석, 역할 분담은 루트 [README.md](../README.md)를 기준으로 봄.

이 문서는 아래 상황에서 사용함.

- 새 팀원이 로컬 개발 환경을 처음 구성할 때
- fixture 데이터로 빠르게 코드가 정상 동작하는지 확인할 때
- Riot API raw JSON을 team feature CSV로 변환할 때
- 모델 학습, EDA, notebook 산출물을 재생성할 때
- Supabase 업로드를 dry-run 또는 실제 실행으로 검증할 때
- PR 전 보안/산출물 커밋 여부를 점검할 때

## 1. 전체 실행 흐름

분석 흐름은 Supabase에서 직접 데이터를 읽는 구조가 아님. Riot API에서 받은 raw JSON을 로컬 CSV로 변환하고, 이 CSV를 기준으로 validation, model, EDA, notebook을 실행하는 구조임.

```text
Riot API
-> data/raw/riot/runs/<run-id>/
-> data/processed/riot/<run-id>_team_features.csv
-> validation / model / EDA / notebook
-> 필요 시 Supabase 업로드
```

역할 분리:

| 단계 | 주 입력 | 주 출력 | Git 커밋 여부 |
| --- | --- | --- | --- |
| Riot 수집 | Riot API, `.env` | `data/raw/riot/runs/<run-id>/` | 커밋 안 함 |
| CSV 생성 | raw run | `data/processed/riot/<run-id>_team_features.csv` | 커밋 안 함 |
| 검증 | processed CSV | validation JSON | 커밋 안 함 |
| 모델/EDA | processed CSV | metrics, model, figures | 커밋 안 함 |
| Notebook | CSV/metrics/figures | `.ipynb` 결과 | 커밋 가능 |
| Supabase | processed CSV | 원격 table upsert | 코드만 커밋 |

## 2. 환경 설정

Python 3.9 이상 기준임. venv 생성 전에는 `python` 명령이 없을 수 있으므로 `python3`로 venv를 먼저 만듦.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Jupyter에서 프로젝트 커널이 보이지 않으면 커널을 등록함.

```bash
python -m ipykernel install --user --name team2-surrender --display-name "Team2 Surrender (.venv)"
```

Riot API 또는 Supabase 작업이 필요하면 `.env.example`을 복사해 `.env`를 만듦. `.env`는 커밋하지 않음.

```bash
cp .env.example .env
```

필수/선택 환경 변수:

| 변수 | 필요 상황 | 설명 |
| --- | --- | --- |
| `RIOT_API_KEY` | Riot 수집 | Riot Developer API key |
| `RIOT_PLATFORM_ROUTING` | Riot 수집 | KR 서버 기준 `kr` |
| `RIOT_REGIONAL_ROUTING` | Riot 수집 | Match-V5 기준 `asia` |
| `SUPABASE_URL` | Supabase REST 업로드 | Supabase project URL |
| `SUPABASE_ANON_KEY` | Supabase REST 업로드 | dry-run에는 실제 전송 없음 |
| `SUPABASE_SERVICE_ROLE_KEY` | 실제 업로드 | 실제 upsert 시 권장 |
| `SUPABASE_DB_URL` | schema 적용 | Direct/Postgres 연결 문자열 |

## 3. 빠른 로컬 검증

네트워크 없이 fixture 데이터로 전체 코드 흐름을 확인하는 기본 검증임.

```bash
source .venv/bin/activate
PYTHONPATH=src python -m unittest discover -s tests -v
python scripts/check_no_secrets.py
python scripts/verify_local_pipeline.py
```

`verify_local_pipeline.py`가 확인하는 항목:

- `src`, `scripts`, `tests` compile 가능 여부
- feature/label 단위 테스트 통과 여부
- Riot 수집 dry-run 가능 여부
- fixture raw run에서 team feature CSV 생성 가능 여부
- Supabase REST/Postgres 업로드 dry-run row count 확인
- fixture 모델 학습과 EDA 산출물 생성 가능 여부

정상 종료 기준:

```text
verification_status: complete
```

## 4. 분석 데이터 기준

분석 데이터 기준은 [Riot 서렌 예측 분석 데이터 기준서](data_contract.md)에 따름.

핵심 규칙:

- 한 행은 한 경기의 한 팀임
- 한 경기에서 블루/레드 두 행 생성함
- `queue_id=420`만 사용함
- 15분 이전 정보만 feature로 사용함
- 경기 종료 상태는 label 생성에만 사용함
- `match_id` 기준 group split으로 같은 경기가 train/valid/test에 동시에 들어가지 않게 함
- PUUID, 소환사명, API key, Supabase key는 공유 산출물에 넣지 않음

## 5. Riot 데이터 수집

API key가 정상 설정됐는지 먼저 확인함.

```bash
python scripts/check_riot_key.py --tier EMERALD --division I --page 1
```

작은 규모 수집 예시:

```bash
python scripts/collect_riot_matches.py \
  --run-id riot-smoke \
  --tier EMERALD \
  --division I \
  --pages 1 \
  --max-seeds 10 \
  --matches-per-puuid 5 \
  --max-unique-matches 10 \
  --resume
```

주요 옵션:

| 옵션 | 의미 |
| --- | --- |
| `--run-id` | raw run과 이후 산출물 이름 기준 |
| `--pages` | League-V4 page 수 |
| `--max-seeds` | seed account 수 |
| `--matches-per-puuid` | seed별 match id 요청 수 |
| `--max-unique-matches` | 최종 수집할 unique match 수 |
| `--resume` | 이미 받은 JSON 재사용 |
| `--dry-run` | 네트워크 호출 없이 경로와 설정만 확인 |

수집 결과는 `data/raw/riot/runs/<run-id>/` 아래에 저장됨. manifest에는 안전한 match id와 count만 남기고 PUUID나 소환사 식별자는 기록하지 않음.

## 6. Team Feature CSV 생성과 검증

수집된 raw run을 팀 단위 feature CSV로 변환함.

```bash
python scripts/build_team_dataset.py \
  --run-id riot-smoke \
  --out data/processed/riot/riot-smoke_team_features.csv \
  --manifest data/processed/riot/riot-smoke_team_features_manifest.json
```

생성된 CSV가 분석 데이터 기준을 만족하는지 검증함.

```bash
python scripts/validate_team_dataset.py \
  --input data/processed/riot/riot-smoke_team_features.csv \
  --report data/processed/riot/riot-smoke_team_features_validation.json \
  --allow-small
```

최종 분석 기준 파일명:

```text
data/processed/riot/riot-scale-2600_team_features.csv
```

`riot-scale-2600_team_features.csv`가 없고 `data/raw/riot/runs/riot-scale-2600/`도 없으면 다음 중 하나가 필요함.

- 같은 run id로 Riot 데이터를 다시 수집함
- 팀 내에서 동일한 processed CSV를 공유받음
- Supabase에 업로드된 동일 데이터가 있다면 별도 export 절차를 통해 CSV로 복원함

## 7. 모델 학습과 EDA

모델 학습:

```bash
python scripts/train_models.py \
  --input data/processed/riot/riot-scale-2600_team_features.csv \
  --metrics-json outputs/metrics/riot-scale-2600_model_comparison.json \
  --metrics-csv outputs/tables/riot-scale-2600_model_comparison.csv \
  --model-dir models/riot-scale-2600
```

EDA figure 생성:

```bash
python scripts/run_eda.py \
  --input data/processed/riot/riot-scale-2600_team_features.csv \
  --figure-dir reports/figures/riot-scale-2600 \
  --metrics-csv outputs/tables/riot-scale-2600_model_comparison.csv
```

주요 산출물:

- `outputs/metrics/*_model_comparison.json`
- `outputs/tables/*_model_comparison.csv`
- `models/<run-id>/*.joblib`
- `reports/figures/<run-id>/*.png`
- `outputs/verification/*.json`

위 산출물은 재생성 가능하므로 git에 올리지 않음.

## 8. Notebook 실행

메인 notebook과 버전별 notebook은 `riot-scale-2600` 산출물을 기준으로 읽음.

필요한 validation, model, metric, figure, local upload verification 산출물을 한 번에 준비하고 메인 notebook까지 실행함.

```bash
python scripts/prepare_jupyter_analysis_artifacts.py --run-id riot-scale-2600 --execute-notebook
```

버전별 notebook 일괄 실행:

```bash
python scripts/execute_jupyter_versions.py
```

Notebook 목록:

- `notebooks/team2_riot_surrender_analysis.ipynb`
- `notebooks/team2_riot_surrender_analysis.executed.ipynb`
- `notebooks/versions/v01_data_validation_riot_scale_2600.ipynb`
- `notebooks/versions/v02_eda_feature_interpretation_riot_scale_2600.ipynb`
- `notebooks/versions/v03_modeling_threshold_riot_scale_2600.ipynb`
- `notebooks/versions/v04_submission_report_riot_scale_2600.ipynb`

Notebook output 커밋 전 확인 항목:

- error output 없음
- `.env`, API key, Supabase key 없음
- PUUID, summoner name 없음
- 결과 수치가 README와 충돌하지 않음

## 9. Supabase 사용

Supabase는 모델 학습의 직접 입력이 아님. 팀이 생성한 가공 CSV를 공유하거나 확인하기 위한 저장소 역할임. 분석 notebook은 Supabase를 직접 조회하지 않고 로컬 CSV와 재생성 산출물을 읽음.

스키마 파일 dry-run:

```bash
python scripts/apply_supabase_schema.py --dry-run
```

CSV 업로드 dry-run:

```bash
python scripts/upload_team_features_supabase.py \
  --input data/processed/riot/riot-scale-2600_team_features.csv
```

실제 업로드가 필요할 때만 `--execute`를 붙임.

```bash
python scripts/upload_team_features_supabase.py \
  --input data/processed/riot/riot-scale-2600_team_features.csv \
  --execute
```

Postgres 직접 업로드 스크립트도 dry-run 기본값임.

```bash
python scripts/upload_team_features_postgres.py \
  --input data/processed/riot/riot-scale-2600_team_features.csv
```

## 10. 자주 발생하는 문제

### Jupyter kernel이 보이지 않음

venv 활성화 후 kernel 등록 명령을 다시 실행함.

```bash
source .venv/bin/activate
python -m ipykernel install --user --name team2-surrender --display-name "Team2 Surrender (.venv)"
```

### `ModuleNotFoundError: No module named 'team2_surrender'`

저장소 루트에서 실행 중인지 확인함. 테스트는 `PYTHONPATH=src`를 붙여 실행함.

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
```

Notebook에서는 root 탐색 코드가 `src/team2_surrender`를 기준으로 동작하므로, 저장소 내부에서 notebook을 열어야 함.

### `FileNotFoundError`가 notebook에서 발생함

필요한 CSV, metrics, model, figure 산출물이 없는 상태임. 아래 명령으로 준비함.

```bash
python scripts/prepare_jupyter_analysis_artifacts.py --run-id riot-scale-2600
```

이 명령도 실패하면 `data/processed/riot/riot-scale-2600_team_features.csv` 또는 `data/raw/riot/runs/riot-scale-2600/` 존재 여부를 먼저 확인함.

### `python` 명령이 없음

venv 생성 전이면 `python3`를 사용함.

```bash
python3 -m venv .venv
source .venv/bin/activate
```

venv 활성화 후에는 `python` 명령을 사용 가능해야 함.

### Supabase direct connection 오류

Direct connection이 IPv6로 해석되면 로컬 네트워크에서 연결이 실패할 수 있음. 이 경우 Supabase Dashboard의 connection pooling/session pooler 연결 문자열을 `SUPABASE_DB_URL`에 설정한 뒤 다시 실행함.

## 11. 커밋 전 점검

커밋 전 아래 항목을 확인함.

- `.env` 미포함
- Riot API key, Supabase key, DB URL/password 미포함
- PUUID, summoner name 등 재식별 위험 raw identifier 미포함
- `data/raw`, `data/interim`, `data/processed`, `models`, `outputs`, `reports/figures` 미포함
- README 결과 수치와 notebook 결과 수치 충돌 없음

검사 명령:

```bash
python scripts/check_no_secrets.py
git status --short
```

커밋 메시지는 lightweight Conventional Commits 형식을 사용함.

```text
docs: 프로젝트 README와 개발 가이드 분리
fix: 모델링 모듈 import 경로 수정
```
