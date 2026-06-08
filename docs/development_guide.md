# Development Guide

Team 2 Riot 15분 경기 상태 기반 패배 위험 분석 프로젝트를 로컬에서 실행, 검증, 재현하기 위한 개발 가이드입니다. 과제 제출용 개요와 최종 구조는 루트 [README.md](../README.md)를 기준으로 봅니다.

---

## 1. 현재 제출 구조

최종 제출 기준 산출물은 다음 구조를 사용합니다.

```text
.
├── data_1/                     # 초기 공통 baseline 재현용 최소 가공 데이터
├── data_2/                     # temporal/counter 확장 중간 데이터
├── data_3/                     # 최종 v16.9 정합 데이터와 외부 champion context
├── lab/                        # 공식 Jupyter notebook 14개
├── Report/Submission/          # 최종 보고서
├── docs/                       # 데이터 계약/개발 가이드/스키마 문서
├── scripts/                    # 수집·가공·검증 스크립트
├── src/team2_surrender/        # 재사용 가능한 Python 모듈
└── tests/                      # 단위 테스트
```

개인 실험 workspace, 모델 바이너리, 실행 output, figure 파일, zip 파일은 커밋하지 않습니다. 개인별 작은 markdown summary나 중간 CSV/JSON도 원격에 따로 올리지 않고, 필요한 내용은 `lab/*.ipynb`와 최종 보고서에 통합합니다.

---

## 2. 데이터 묶음

| 폴더 | 역할 | 커밋 기준 |
| --- | --- | --- |
| `data_1/` | 초기 `riot-scale-2600` baseline 재현용 최소 데이터 | 포함 |
| `data_2/processed/riot/` | temporal/counter 확장 과정 데이터 | 포함 |
| `data_3/processed/riot/` | 최종 v16.9 데이터와 Lolalytics context | 포함 |
| `data_2/verification/`, `data_3/verification/` | 로컬 검증 JSON summary | 제외 |
| `data/raw`, `data/interim`, 로컬 생성 processed snapshot | 수집/가공 중간 산출물 | 제외 |

---

## 3. 환경 설정

Python 3.9 이상 기준입니다.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Jupyter kernel 등록이 필요하면 다음을 실행합니다.

```bash
python -m ipykernel install --user --name team2-surrender --display-name "Team2 Surrender (.venv)"
```

Riot API 또는 Supabase 작업이 필요하면 `.env.example`을 참고해 `.env`를 만들 수 있습니다. `.env`는 커밋하지 않습니다.

```bash
cp .env.example .env
```

---

## 4. 빠른 검증

코드 단위 검증은 다음 명령을 사용합니다.

```bash
source .venv/bin/activate
PYTHONPATH=src python -m unittest discover -s tests -v
```

현재 핵심 테스트는 다음을 확인합니다.

- 조기 서렌/짧은 경기 제외
- 15분 기준 팀 관점 feature 추출
- team-level surrender label 생성
- `match_id` group split leakage 방지

---

## 5. 공식 notebook 실행

공식 notebook은 `lab/`에 있습니다. 순서대로 실행합니다.

| 범위 | 내용 |
| --- | --- |
| `lab/01` ~ `lab/04` | 공통 데이터 검증, EDA, baseline, 보고서 연결 |
| `lab/05` ~ `lab/09` | 범준 final-loss 설명력 실험 |
| `lab/10` ~ `lab/14` | 승범 final-loss archetype/interaction 실험 |

일괄 실행:

```bash
python -m nbconvert --execute --to notebook --inplace lab/*.ipynb
```

개인별 실행 예시:

```bash
python -m nbconvert --execute --to notebook --inplace \
  lab/05_bumjun_baseline_feature_expansion.ipynb \
  lab/06_bumjun_mlp_model_ceiling.ipynb \
  lab/07_bumjun_label_reframing_final_loss.ipynb \
  lab/08_bumjun_generalization_risk_explanation.ipynb \
  lab/09_bumjun_data3_compact_l1_explainability.ipynb
```

Notebook output 커밋 전 확인 항목:

- error output 없음
- 그래프 output 존재
- `.env`, API key, Supabase key 없음
- PUUID, summoner name 없음
- README/최종 보고서의 문제정의와 충돌하지 않음

---

## 6. Riot 수집·가공 파이프라인

수집/가공 스크립트는 재현 경로를 남기기 위한 코드입니다. 원본 API 응답과 로컬 생성 중간 산출물은 용량과 보안 관리상 커밋하지 않습니다.

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

팀 단위 feature 생성 예시:

```bash
python scripts/build_team_dataset.py \
  --run-id riot-smoke \
  --out /tmp/riot-smoke_team_features.csv \
  --manifest /tmp/riot-smoke_team_features_manifest.json
```

검증 예시:

```bash
python scripts/validate_team_dataset.py \
  --input /tmp/riot-smoke_team_features.csv \
  --report /tmp/riot-smoke_team_features_validation.json \
  --allow-small
```

---

## 7. Supabase 사용

Supabase는 모델 학습의 직접 입력이 아니라 팀 데이터 공유와 확인을 위한 저장소입니다. 분석 notebook은 로컬 제출 데이터 묶음을 읽습니다.

스키마 dry-run:

```bash
python scripts/apply_supabase_schema.py --dry-run
```

업로드 스크립트는 기본적으로 dry-run 또는 명시적 실행 옵션을 사용합니다. 실제 업로드 전에는 `.env`와 권한을 별도로 확인합니다.

---

## 8. 커밋 전 점검

커밋 전 아래 항목을 확인합니다.

- `.env` 미포함
- Riot API key, Supabase key, DB URL/password 미포함
- PUUID, summoner name 등 재식별 위험 raw identifier 미포함
- 개인 실험 workspace 미포함
- 모델/figure/output/zip 미포함
- 개인 PR에서 본인 notebook 외 파일이 섞이지 않음

검사 명령:

```bash
git status --short
git diff --stat --cached
PYTHONPATH=src python -m unittest discover -s tests -v
```

커밋 메시지는 lightweight Conventional Commits 형식을 사용합니다.

```text
exp: 범준 final-loss 설명력 실험 notebook 추가
exp: 승범 final-loss archetype 실험 notebook 추가
chore: 제출용 lab 구조와 보고서 기준 정리
```

---

## 9. 자주 발생하는 문제

### Jupyter kernel이 보이지 않음

```bash
source .venv/bin/activate
python -m ipykernel install --user --name team2-surrender --display-name "Team2 Surrender (.venv)"
```

### `ModuleNotFoundError: No module named 'team2_surrender'`

저장소 루트에서 실행 중인지 확인합니다. 테스트는 `PYTHONPATH=src`를 붙여 실행합니다.

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
```

### Notebook에서 파일을 찾지 못함

다음 제출 데이터 묶음이 있는지 확인합니다.

```text
data_1/processed/riot/
data_2/processed/riot/
data_3/processed/riot/
```

### `python` 명령이 없음

venv 생성 전이면 `python3`를 사용합니다.

```bash
python3 -m venv .venv
source .venv/bin/activate
```
