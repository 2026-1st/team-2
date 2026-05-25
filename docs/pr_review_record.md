# Team2 PR 리뷰 기록 양식

이 문서는 GitHub Pull Request 리뷰 내용을 팀 내부 문서로 남길 때 사용하는 기록 양식입니다.

리뷰 기록은 단순히 "승인했다"는 결과가 아니라, 리뷰어가 어떤 기준으로 변경 사항을 확인했고 어떤 후속 검증이 남아 있는지를 남기는 데 목적이 있습니다.

---

## 1. 작성 원칙

1. PR 번호, 작성자, 리뷰어, 브랜치, 리뷰 결과를 명확히 남깁니다.
2. 리뷰어가 확인한 변경 범위와 판단 근거를 짧게 기록합니다.
3. 머지 전에 끝난 검증과 이후에 남은 검증을 구분합니다.
4. 보안, 개인정보, 대용량 산출물 포함 여부를 별도 항목으로 확인합니다.
5. `Approve`, `Comment`, `Request changes` 중 실제 GitHub 리뷰 결과와 맞춰 작성합니다.

---

## 2. 리뷰 기록 양식

```markdown
# PR 리뷰 기록: #<PR 번호> <PR 제목>

## 기본 정보

| 항목 | 내용 |
| --- | --- |
| PR | #<번호> |
| 링크 | <GitHub PR URL> |
| 작성자 | <이름> (`<GitHub ID>`) |
| 리뷰어 | <이름> (`<GitHub ID>`) |
| base branch | `<base>` |
| compare branch | `<head>` |
| 리뷰 결과 | Approve / Comment / Request changes |
| 리뷰 제출 시각 | YYYY-MM-DD HH:MM KST |
| 머지 여부 | merged / not merged |

## 변경 범위 요약

- <리뷰 대상 변경 1>
- <리뷰 대상 변경 2>
- <리뷰 대상 변경 3>

## 리뷰어 확인 사항

- [ ] 변경 범위가 PR 설명과 일치함
- [ ] 기능 또는 문서의 책임 범위가 명확함
- [ ] 테스트, 검증 명령, 산출물이 PR에 기록됨
- [ ] `.env`, API key, DB password 등 민감정보가 포함되지 않음
- [ ] raw/interim/processed data, model artifact 등 대용량 산출물이 포함되지 않음
- [ ] 남은 검증 또는 후속 작업이 명시됨

## 리뷰 코멘트 요약

- <리뷰어가 긍정적으로 확인한 점>
- <수정 요청 또는 주의할 점>
- <머지 후 후속 작업>

## 최종 판단

<Approve / Comment / Request changes 판단과 이유를 2-4문장으로 정리합니다.>

## 후속 작업

- [ ] <머지 후 또는 다음 PR에서 확인할 작업>
```

---

## 3. GitHub 리뷰 복붙 양식

GitHub PR의 `Review changes` 창에 바로 붙여넣을 때는 아래 양식을 사용합니다.

### Approve

```markdown
# PR 리뷰

## 리뷰 결과

Approve

## 확인한 내용

- 변경 범위가 PR 설명과 일치하는지 확인했습니다.
- 핵심 구현/문서 변경이 담당 범위 안에 있는지 확인했습니다.
- 검증 명령 또는 산출물이 PR 본문에 기록되어 있는지 확인했습니다.
- `.env`, API key, DB password 등 민감정보가 포함되지 않았는지 확인했습니다.
- raw/interim/processed data, model artifact 등 대용량 산출물이 포함되지 않았는지 확인했습니다.

## 리뷰 코멘트

<좋게 본 점과 승인 근거를 2-4문장으로 작성합니다.>

## 후속 확인 사항

- [ ] <머지 후 또는 다음 PR에서 확인할 작업이 있으면 작성합니다. 없으면 "없음"으로 작성합니다.>
```

### Comment

```markdown
# PR 리뷰

## 리뷰 결과

Comment

## 확인한 내용

- 변경 범위와 PR 설명을 확인했습니다.
- 검증 결과와 보안/데이터 체크 항목을 확인했습니다.

## 코멘트

<승인 또는 변경 요청 전 확인이 필요한 질문/제안을 작성합니다.>

## 확인 요청

- [ ] <작성자에게 확인받을 항목>
```

### Request changes

```markdown
# PR 리뷰

## 리뷰 결과

Request changes

## 변경 요청 사항

- [ ] <수정이 필요한 항목 1>
- [ ] <수정이 필요한 항목 2>

## 근거

<왜 이 변경이 머지 전에 필요한지 구체적으로 작성합니다.>

## 재검토 기준

- [ ] 수정 커밋 반영
- [ ] 관련 검증 명령 재실행
- [ ] PR 본문 또는 문서에 결과 기록
```

---

## 4. PR #3 리뷰 기록

### PR 리뷰 기록: #3 data: team feature 계약과 Supabase schema 추가

#### 기본 정보

| 항목 | 내용 |
| --- | --- |
| PR | #3 |
| 링크 | https://github.com/2026-1st/team-2/pull/3 |
| 작성자 | 송재혁 (`WhySongSerious`) |
| 리뷰어 | 정민기 (`mingi123`) |
| base branch | `main` |
| compare branch | `data/team-feature-contract` |
| 리뷰 결과 | Approve |
| 리뷰 제출 시각 | 2026-05-25 13:48 KST |
| 머지 여부 | merged, 2026-05-25 13:48 KST |

#### 변경 범위 요약

- Riot API 기반 LoL 서렌 예측 데이터셋의 분석 단위, 제외 기준, 라벨 정의, 15분 feature 컬럼 계약을 문서화함.
- Supabase 저장을 위한 `collection_runs`, `riot_matches`, `team_features` 테이블 스키마를 추가함.
- Supabase schema SQL 적용과 필수 테이블 생성 여부 확인을 위한 보조 스크립트를 추가함.

#### 리뷰어 확인 사항

- [x] 변경 범위가 PR 설명과 일치함
- [x] 데이터 계약 문서에서 분석 단위를 "한 경기의 한 팀"으로 명확히 정의함
- [x] 15분 이전 타임라인과 이벤트만 feature로 사용하도록 제한해 label leakage 방지 기준을 갖춤
- [x] 라벨 생성 기준이 feature와 분리되어 있음
- [x] Supabase 스키마가 `collection_runs`, `riot_matches`, `team_features`로 역할이 분리되어 있음
- [x] `(match_id, team_id, feature_version)` primary key로 feature version 관리가 가능함
- [x] PUUID, 소환사명, Riot ID 등 재식별 가능한 값이 스키마와 문서에 포함되지 않음
- [x] 커밋 메시지가 팀 convention에 맞음
- [ ] 실제 Supabase 개발 DB에 schema를 적용하는 검증은 별도 확인 필요

#### 리뷰 코멘트 요약

- 데이터 계약 문서에서 분석 단위를 "한 경기의 한 팀"으로 명확히 잡은 점을 긍정적으로 확인함.
- 15분 이전 타임라인과 이벤트만 feature로 사용하도록 제한한 점이 leakage 방지 관점에서 적절하다고 판단함.
- Supabase 스키마는 세 테이블의 역할 분리와 복합 primary key 설계가 이후 feature version 관리에 적합하다고 판단함.
- 재식별 가능한 raw identifier가 스키마와 문서에 포함되지 않은 것을 확인함.
- 실제 Supabase 개발 DB 적용 검증은 아직 남은 후속 작업으로 기록함.

#### 최종 판단

정민기 리뷰어는 PR #3을 `Approve`로 승인했습니다. 현재 PR 범위는 데이터 계약과 Supabase 스키마 정의로 잘 분리되어 있고, label leakage 방지 기준과 개인정보 제외 기준이 문서와 스키마에 반영되어 있다는 점이 승인 근거입니다. 단, 실제 Supabase 개발 DB에 schema를 적용하는 검증은 머지 후 또는 다음 작업에서 별도로 확인해야 합니다.

#### 후속 작업

- [ ] `scripts/apply_supabase_schema.py --dry-run` 실행 결과 확인
- [ ] Supabase 개발 DB에 `docs/supabase_schema.sql` 적용 결과 확인
- [ ] 필수 테이블 `collection_runs`, `riot_matches`, `team_features` 생성 여부 확인

#### 원문 리뷰 정보

- GitHub review id: `4354278544`
- Review state: `APPROVED`
- Inline review comment: 없음
- General PR conversation comment: 없음
