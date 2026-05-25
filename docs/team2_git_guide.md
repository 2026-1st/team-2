# Team2 Git / GitHub 운영 가이드

이 문서는 수업 공용 `../.github/docs/Git_가이드.md`와 `../.github/docs/프로젝트_안내.md`를 Team2 프로젝트 상황에 맞게 정리한 팀 내부 Git 운영 규칙입니다.

- 적용 대상: Team2 기계학습기초 프로젝트 저장소
- 원본 기준: 수업 Git / GitHub 가이드, 프로젝트 안내 문서
- 핵심 목표: `main` 브랜치를 항상 제출 가능한 상태로 유지하고, 브랜치·PR·커밋 메시지 품질을 채점 기준에 맞게 관리

---

## 1. 기본 원칙

1. **`main`에 직접 커밋하지 않는다.**
   - 모든 작업은 별도 브랜치에서 진행한 뒤 Pull Request(PR)로 병합한다.
2. **작업 전에는 최신 `main`을 가져온다.**
   - 오래된 코드에서 작업하면 충돌과 중복 작업이 늘어난다.
3. **커밋은 의미 있는 단위로 작게 남긴다.**
   - `수정`, `최종`, `진짜최종` 같은 메시지는 사용하지 않는다.
4. **PR에는 변경 내용과 검증 방법을 적는다.**
   - 팀원이 무엇을 봐야 하는지 알 수 있어야 한다.
5. **비밀값과 대용량 산출물은 커밋하지 않는다.**
   - `.env`, API key, raw/interim/processed data, 모델 파일, 대용량 output은 Git에 올리지 않는다.

---

## 2. Team2 권장 브랜치 전략

`main`은 최종 제출 가능한 코드만 유지합니다. 작업별로 아래 패턴의 브랜치를 만듭니다.

| 패턴 | 용도 | 예시 |
|------|------|------|
| `feature/<설명>` | 새 기능·분석 코드 | `feature/riot-collector`, `feature/15min-features` |
| `fix/<설명>` | 버그 수정 | `fix/team-label-bug`, `fix/seed-split` |
| `docs/<설명>` | 문서 작성·수정 | `docs/git-guide`, `docs/readme-runbook` |
| `exp/<설명>` | 실험·모델 비교 | `exp/logistic-baseline`, `exp/rf-gb-compare` |
| `data/<설명>` | 데이터 계약·샘플·검증 로직 | `data/validation-rules` |
| `chore/<설명>` | 환경·설정·정리 | `chore/requirements-cleanup` |

브랜치 이름은 영어 소문자와 하이픈을 권장합니다.

---

## 3. 기본 작업 흐름

### 3.1 작업 시작

```bash
# 1) main 최신화
git switch main
git pull origin main

# 2) 작업 브랜치 생성
git switch -c feature/15min-features
```

### 3.2 작업 중 상태 확인

```bash
git status
git diff
git log --oneline --decorate -5
```

### 3.3 변경사항 커밋

```bash
# 필요한 파일만 add
git add src/team2_surrender/features.py tests/test_labels_features.py

# 명확한 메시지로 commit
git commit -m "feat: 15분 팀 피처 추출 로직 추가"
```

### 3.4 원격 업로드와 PR 생성

```bash
git push origin feature/15min-features
```

그 다음 GitHub에서 `main <- feature/15min-features` 방향으로 Pull Request를 만듭니다.

---

## 4. 커밋 메시지 규칙

수업 가이드 기준처럼 아래 형식을 사용합니다.

```text
<타입>: <무엇을 했는지 간결하게>
```

### 4.1 타입 목록

| 타입 | 의미 | Team2 예시 |
|------|------|------------|
| `feat` | 새 기능 추가 | `feat: Riot match 수집 스크립트 추가` |
| `fix` | 버그 수정 | `fix: 서렌 라벨 판정 조건 수정` |
| `docs` | 문서 수정 | `docs: README 실행 방법 보강` |
| `refactor` | 동작 변화 없는 구조 개선 | `refactor: Riot client 응답 파싱 분리` |
| `data` | 데이터 계약·샘플·검증 관련 변경 | `data: team_features 스키마 검증 항목 추가` |
| `exp` | 실험·모델 비교 추가 | `exp: Logistic Regression baseline 추가` |
| `chore` | 설정·환경·기타 정리 | `chore: requirements 정리` |

### 4.2 좋은 예

```text
feat: 15분 팀 단위 feature 생성 로직 추가
fix: 900초 미만 경기 제외 조건 수정
docs: Supabase schema 적용 방법 추가
exp: Random Forest baseline 교차검증 추가
data: processed dataset 검증 기준 문서화
```

### 4.3 피해야 할 예

```text
수정함
업데이트
final
진짜최종
asdf
```

---

## 5. Pull Request(PR) 규칙

PR은 `main`에 병합하기 전 팀원이 변경사항을 확인하는 단계입니다.

리뷰 결과를 별도 문서로 남길 때는 `docs/pr_review_record.md`의 리뷰 기록 양식을 사용합니다.

### 5.1 PR 생성 전 체크리스트

- [ ] 브랜치가 최신 `main` 기준인지 확인
- [ ] 불필요한 notebook output, `.DS_Store`, 임시 파일 제거
- [ ] `.env` 또는 API key가 포함되지 않았는지 확인
- [ ] raw/interim/processed data, models, outputs 등 대용량 산출물이 포함되지 않았는지 확인
- [ ] 관련 테스트 또는 smoke command를 실행했는지 확인
- [ ] README 또는 문서 업데이트가 필요한 변경인지 확인

### 5.2 PR 설명 템플릿

```markdown
## 변경 사항
- 

## 관련 이슈
closes #이슈번호

## 검증
- [ ] `PYTHONPATH=src pytest`
- [ ] 필요한 경우 smoke command 실행

## 리뷰 요청 사항
- 
```

### 5.3 Team2 PR 예시

```markdown
## 변경 사항
- `src/team2_surrender/features.py`에 15분 팀 단위 feature 생성 로직 추가
- `tests/test_labels_features.py`에 synthetic fixture 기반 테스트 추가

## 관련 이슈
closes #12

## 검증
- [x] `PYTHONPATH=src pytest tests/test_labels_features.py`

## 리뷰 요청 사항
- `game_duration_sec < 900` 제외 조건이 과제 요구사항과 맞는지 확인 부탁드립니다.
```

---

## 6. 이슈(Issue) 활용 규칙

작업을 시작하기 전에 GitHub Issue로 할 일을 나누면 Git 활용 평가와 협업 기록에 도움이 됩니다.

### 6.1 이슈 제목 예시

```text
[DATA] Riot raw match 수집 smoke run 실행
[FEATURE] 15분 팀 단위 feature 생성
[MODEL] Logistic Regression baseline 구현
[DOCS] README 실행 방법 정리
[FIX] group split leakage 점검
```

### 6.2 이슈 본문 예시

```markdown
## 배경
현재 processed dataset 생성 후 필수 컬럼 검증이 필요하다.

## 할 일
- [ ] 필수 컬럼 목록 확인
- [ ] target 양 클래스 존재 여부 검증
- [ ] match_id 기준 group split 가능 여부 확인

## 완료 기준
- `scripts/validate_team_dataset.py`로 구조 검증 가능
```

커밋 또는 PR 설명에 `closes #이슈번호`를 적으면 PR merge 시 이슈가 자동으로 닫힙니다.

---

## 7. 파일별 커밋 주의사항

### 7.1 커밋하면 좋은 파일

- `README.md`
- `docs/*.md`, `docs/*.sql`
- `src/team2_surrender/*.py`
- `scripts/*.py`
- `tests/*.py`
- `requirements.txt`
- 필요한 경우 작은 예시 fixture 또는 문서용 샘플

### 7.2 커밋하지 말아야 할 파일

현재 `.gitignore` 기준으로 아래 파일·디렉터리는 Git에 올리지 않습니다.

- `.env`, `.env.*` (`.env.example`만 예외)
- `data/raw/`
- `data/interim/`
- `data/processed/`
- `models/`
- `outputs/`
- `reports/figures/`
- `__pycache__/`, `.ipynb_checkpoints/`
- `.DS_Store`

특히 Riot API key, Supabase service role key, PUUID 등 민감하거나 재식별 위험이 있는 값은 절대 커밋하지 않습니다.

---

## 8. Notebook 사용 규칙

Notebook은 실험 기록에는 유용하지만, output 때문에 파일이 커지고 diff가 복잡해질 수 있습니다.

권장 규칙:

1. 중요한 재현 로직은 가능하면 `scripts/` 또는 `src/`로 옮긴다.
2. notebook은 EDA·결과 확인용으로 사용한다.
3. 커밋 전 output을 정리한다.

```bash
jupyter nbconvert --clear-output --inplace notebooks/*.ipynb
```

또는 Jupyter에서 `Kernel → Restart & Clear Output` 후 저장합니다.

---

## 9. 충돌 해결 기본 절차

작업 브랜치에서 최신 `main`과 충돌이 날 수 있습니다.

```bash
# 작업 브랜치에서 main 반영
git fetch origin
git merge origin/main
```

충돌 표시가 있는 파일을 열어 아래 표시를 정리합니다.

```text
<<<<<<< HEAD
내 변경
=======
상대 변경
>>>>>>> origin/main
```

정리 후:

```bash
git add <충돌 해결 파일>
git commit -m "fix: main 병합 충돌 해결"
```

충돌 해결이 애매하면 혼자 덮어쓰지 말고 해당 파일 담당자에게 리뷰를 요청합니다.

---

## 10. 최종 제출 전 Git 체크리스트

수업 프로젝트 안내 기준으로 최종 코드·노트북은 **2026년 6월 8일**까지 GitHub 저장소에 업로드되어야 합니다.

최종 제출 전 `main` 또는 지정된 `release` 브랜치에서 확인합니다.

- [ ] `main` 또는 `release` 브랜치에 정리된 형태로 merge 완료
- [ ] `README.md`에 실행 방법과 필요 환경 명시
- [ ] `.env.example`은 최신이고 `.env`는 미커밋 상태
- [ ] raw/interim/processed data와 모델 산출물은 미커밋
- [ ] 주요 스크립트 실행 방법이 문서화됨
- [ ] 테스트 또는 smoke 검증 결과가 PR/README/보고서에 남아 있음
- [ ] 마감 이후 변경은 오탈자·주석 보강 등 경미한 변경만 수행하고 커밋 메시지에 명확히 기록

---

## 11. Team2 추천 최소 루틴

매 작업마다 아래 순서만 지켜도 대부분의 Git 사고를 줄일 수 있습니다.

```bash
# 작업 시작
git switch main
git pull origin main
git switch -c feature/my-task

# 작업 중
git status
git diff

# 커밋
git add <필요한 파일>
git commit -m "feat: 작업 내용을 한 줄로 설명"

# 업로드
git push origin feature/my-task

# GitHub에서 PR 생성 후 팀원 리뷰
```

PR이 merge된 뒤에는 다시 `main`을 최신화하고 다음 작업 브랜치를 만듭니다.

```bash
git switch main
git pull origin main
```

---

## 12. 참고 문서

- 수업 공용 Git 가이드: `../.github/docs/Git_가이드.md`
- 수업 프로젝트 안내: `../.github/docs/프로젝트_안내.md`
- Team2 데이터 계약: `docs/data_contract.md`
- Team2 실행 안내: `README.md`
