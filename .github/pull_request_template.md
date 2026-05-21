## 🔗 관련 이슈
<!-- 예: Closes #12 / Related to #12. 없으면 "없음"이라고 적습니다. -->
- 

## 👤 담당 / 리뷰
- PR 작성·통합 담당: 정민기
- 내용 담당:
- 리뷰어:

## 📋 작업 내용 요약
<!-- 이 PR에서 무엇을 추가/수정했는지 2~4줄로 요약합니다. -->
- 

### 주요 변경사항
- 

## 💡 구현 방법 / 판단 근거
<!-- 기술적 선택, 데이터 기준, leakage 방지, 모델 선택 이유 등을 적습니다. -->
- 

## 📸 실행 결과 / 산출물
<!-- UI가 아니어도 주요 표, metric, notebook 실행 결과, validation 결과를 적습니다. -->
- 

## 🧪 검증
<!-- 실행한 명령과 핵심 결과를 적습니다. -->
- [ ] `PYTHONPYCACHEPREFIX=/tmp/team2-pycache python3 scripts/check_no_secrets.py`
- [ ] `PYTHONPATH=src PYTHONPYCACHEPREFIX=/tmp/team2-pycache python3 scripts/verify_local_pipeline.py`
- [ ] 관련 notebook 실행 완료
- [ ] 관련 validation/model metric 확인 완료

### 테스트 케이스 / 시나리오
1. 
2. 
3. 

## 🔐 보안 / 데이터 체크
- [ ] `.env`를 커밋하지 않았습니다.
- [ ] Riot API key, Supabase key, DB URL/password가 포함되지 않았습니다.
- [ ] `data/raw`, `data/interim`, `data/processed`, `models`, `outputs`, `reports/figures`를 커밋하지 않았습니다.
- [ ] PUUID, summoner name 등 재식별 위험 raw identifier를 산출물에 포함하지 않았습니다.

## 🔍 리뷰 포인트
<!-- 리뷰어가 특히 봐야 할 부분 -->
- 

## ⚠️ 주의사항 / 한계
<!-- Breaking change, 데이터 편향, 실행 조건, 추가 필요 작업 등 -->
- 

## 📝 추가 메모
- 

---

## ✅ PR 체크리스트
- [ ] 작업 범위가 하나의 역할/기능 단위로 작게 나뉘었습니다.
- [ ] 커밋 메시지가 `feat:`, `fix:`, `docs:`, `data:`, `exp:`, `test:`, `chore:` 형식을 따릅니다.
- [ ] README 또는 관련 문서가 필요한 만큼 업데이트되었습니다.
- [ ] PR 작성자가 변경 내용을 설명할 수 있습니다.
- [ ] 리뷰어가 검증 결과를 확인했습니다.
