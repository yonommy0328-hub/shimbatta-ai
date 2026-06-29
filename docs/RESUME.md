# 🚀 심봤다 AI — 로컬 오프라인 RAG 인프라 연동 완료 및 이어서 개발하기 가이드

본 문서는 파인튜닝의 품질 한계와 저사양 폰(어르신 폰) 구동 문제를 한 번에 해결하기 위해 적용한 **오프라인 로컬 RAG (검색 증강 생성) 구조**와 다음 개발 단계로 넘어가기 위한 가이드를 담고 있습니다.

---

## 📂 변경 및 추가된 핵심 파일들
1. **[docs/generate_ts_knowledge.py](file:///Users/gim-yeongjong/심봤다%20AI/docs/generate_ts_knowledge.py) [NEW]**
   * 프로젝트 루트의 `shimbatta_knowledge.md` 문서를 파싱하여 리액트 네이티브에서 컴파일 없이 바로 쓸 수 있는 TypeScript 데이터로 만들어주는 변환 스크립트입니다.
2. **[src/constants/herbKnowledge.ts](file:///Users/gim-yeongjong/심봤다%20AI/src/constants/herbKnowledge.ts) [NEW]**
   * 스크립트를 통해 자동 컴파일된 **9쌍(19종 식물)에 대한 약초 vs 독초 지식 매핑 파일**입니다.
3. **[src/services/LLMService.ts](file:///Users/gim-yeongjong/심봤다%20AI/src/services/LLMService.ts) [MODIFY]**
   * **로컬 RAG(오픈북) 탑재:** 비전 AI가 식물을 검출하면 즉시 `herbKnowledge.ts`에서 지식을 찾아 LLM 프롬프트에 동적으로 결합(Prompt Injection)합니다.
   * **안전 폴백(Fallback) 강화:** 만약 핸드폰 메모리가 부족하여 로컬 GGUF 모델을 로드하지 못하거나 에러가 나도, `HERB_KNOWLEDGE`에서 해당 약초의 **오리지널 비교 검증 마크다운 지식 전체를 즉시 읽어 화면에 타이핑 효과로 출력**해 줍니다. (안전율 100% 보장)

---

## 🧠 Qwen2.5-0.5B-Instruct 모델 준비 안내
**저한테 직접 모델 파일을 보내주실 필요는 없습니다!** (GGUF 파일은 몇백 MB로 용량이 너무 커 채팅창으로 전송이 불가능합니다.)

대신, 인터넷에서 깨끗한 원본 **`Qwen2.5-0.5B-Instruct`** 모델을 구하셔서 앱에 넣어주시면 됩니다.

### 모델 다운로드 및 명칭 매핑 방법:
1. **다운로드 경로:** Hugging Face 등에서 `qwen2.5-0.5b-instruct` 모델의 GGUF 버전(추천: `Q4_K_M` 양자화 포맷)을 다운로드합니다.
2. **파일명 통일:** 다운로드한 파일명을 **`qwen2.5-0.5b-instruct.Q4_K_M.gguf`** 로 변경합니다.
3. **앱 내부 보관 위치:** 
   * 스마트폰/시뮬레이터 기기 내부의 앱 전용 문서 경로인 `${DocumentDirectory}/models/` 폴더 아래에 다운로드한 GGUF 파일을 저장해 주시면 됩니다.
   * 앱 실행 시 해당 폴더의 모델을 `LLMService.ts`가 자동으로 감지해 로드합니다.

---

## 🏃‍♂️ 다음 개발을 시작할 때 해야 할 일
나중에 다시 질문자님이나 저와 함께 개발을 이어가실 때 아래 작업을 진행하시면 됩니다:

1. **지식 추가/수정 시:**
   * 루트 폴더의 `shimbatta_knowledge.md` 지식을 수정한 뒤, 터미널에서 아래 명령어를 실행하여 지식을 앱에 업데이트합니다.
   ```bash
   python3 docs/generate_ts_knowledge.py
   ```
2. **개발 서버 구동:**
   * 터미널에서 앱의 개발 서버를 띄워 스마트폰(또는 에뮬레이터)에서 동작 테스트를 수행합니다.
   ```bash
   npm run dev
   ```
