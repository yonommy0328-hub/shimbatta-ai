/**
 * 심봤다 AI — LLMService (2단계 로컬 LLM 추론 + 오프라인 RAG 적용)
 *
 * llama.rn을 통해 GGUF 모델을 로컬에서 추론
 * 1단계 Vision AI 결과를 기반으로 로컬 RAG 지식을 결합하여 약초 효능/경고 텍스트 생성
 */

import RNFS from 'react-native-fs';
import {DEFAULT_LLM_MODEL_NAME} from '../constants/model';
import {findAvailableGGUFModel} from './ModelManager';
import {HERB_KNOWLEDGE} from '../constants/herbKnowledge';

// llama.rn 타입 정의
type LlamaContext = {
  completion: (
    params: {
      messages: Array<{role: string; content: string}>;
      n_predict?: number;
      temperature?: number;
      top_p?: number;
      stop?: string[];
    },
    onToken?: (token: {token: string}) => void,
  ) => Promise<{text: string; timings?: any}>;
  release: () => Promise<void>;
};

/** LLM 서비스 상태 */
export type LLMModelStatus = 'idle' | 'loading' | 'ready' | 'generating' | 'error';

/** LLM 생성 옵션 */
export interface GenerateOptions {
  /** 최대 토큰 수 (기본값: 512) */
  maxTokens?: number;
  /** 온도 (기본값: 0.7) */
  temperature?: number;
  /** Top-p (기본값: 0.9) */
  topP?: number;
  /** 토큰 스트리밍 콜백 */
  onToken?: (partialText: string) => void;
}

/** 시스템 프롬프트 — 약초 전문가 역할 */
const SYSTEM_PROMPT = `당신은 한국 산야초 전문가이자 어르신들의 안전을 지키는 약초 가이드입니다.
사용자가 카메라로 촬영하여 식별한 식물에 대해 다음 형식으로 답변해 주세요:

📋 답변 형식:
1. 식물 이름과 별명 (어르신들이 부르는 이름도 포함)
2. 효능 및 쓰임새 (한의학적 효능, 민간요법)
3. 채취 시기와 방법
4. 요리법 또는 복용법
5. ⚠️ 유사 독초 주의사항 (반드시 포함!)
6. 보관 방법

📌 주의사항:
- 어르신이 이해하기 쉬운 쉬운 말로 설명하세요
- 한자어나 어려운 전문용어는 피하세요
- 핵심은 굵은 글씨로 강조하세요
- 유사한 독초가 있다면 반드시 경고하세요
- 확실하지 않으면 "전문가에게 확인하세요"라고 안내하세요`;

/**
 * LLMService 클래스
 *
 * GGUF 모델의 로딩, 프롬프트 구성, 토큰 스트리밍 추론을 담당
 */
class LLMServiceClass {
  private context: LlamaContext | null = null;
  private status: LLMModelStatus = 'idle';
  private statusListeners: Set<(status: LLMModelStatus) => void> = new Set();

  /** 현재 모델 상태 */
  getStatus(): LLMModelStatus {
    return this.status;
  }

  /** 상태 변경 리스너 등록 */
  onStatusChange(listener: (status: LLMModelStatus) => void): () => void {
    this.statusListeners.add(listener);
    return () => this.statusListeners.delete(listener);
  }

  private setStatus(newStatus: LLMModelStatus) {
    this.status = newStatus;
    this.statusListeners.forEach(listener => listener(newStatus));
  }

  /**
   * GGUF 모델 로딩
   *
   * @param modelPath - GGUF 모델 파일 경로
   * @param nThreads - 추론 스레드 수 (기본값: 4)
   */
  async loadModel(modelPath?: string, nThreads: number = 4): Promise<void> {
    if (this.status === 'loading' || this.status === 'ready') {
      return;
    }

    this.setStatus('loading');

    try {
      const {initLlama} = await import('llama.rn');

      // 기본 모델 경로: 앱 내부 저장소
      const defaultModelPath = `${RNFS.DocumentDirectoryPath}/models/${DEFAULT_LLM_MODEL_NAME}`;
      let path = modelPath || defaultModelPath;

      // 모델 파일 존재 확인
      let exists = await RNFS.exists(path);

      // 설정된 모델이 없고 외부 경로를 지정하지 않았다면, models 내의 임의의 다른 GGUF 검색
      if (!exists && !modelPath) {
        console.log('[LLMService] 설정된 기본 모델을 찾지 못해, models/ 디렉토리 내 GGUF 자동 검색을 시도합니다.');
        const autoDetectedPath = await findAvailableGGUFModel();
        if (autoDetectedPath) {
          path = autoDetectedPath;
          exists = true;
        }
      }

      if (!exists) {
        throw new Error(
          `모델 파일을 찾을 수 없습니다: ${path}\n` +
          '앱 설치 후 모델 파일을 다운로드해야 합니다.',
        );
      }

      // 파일 크기 확인
      const stat = await RNFS.stat(path);
      console.log(`[LLMService] 모델 파일 크기: ${(Number(stat.size) / (1024 * 1024)).toFixed(1)}MB`);

      // llama.cpp 컨텍스트 초기화
      this.context = await initLlama({
        model: path,
        n_ctx: 2048,        // 컨텍스트 윈도우 (메모리 절약)
        n_threads: nThreads,
        n_gpu_layers: 0,    // 안전을 위해 CPU만 사용 (GPU는 기기별 호환성 이슈)
        use_mlock: true,    // 메모리 잠금 (스왑 방지)
      });

      this.setStatus('ready');
      console.log('[LLMService] 모델 로딩 완료');
    } catch (error) {
      console.error('[LLMService] 모델 로딩 실패:', error);
      this.setStatus('error');
      throw error;
    }
  }

  /**
   * 약초 정보 생성 (LLM 추론 + 로컬 RAG 지식 주입)
   *
   * @param plantName - 1단계 Vision AI에서 식별한 식물 이름
   * @param confidence - 예측 확률
   * @param options - 생성 옵션
   * @returns 생성된 약초 정보 텍스트
   */
  async generateHerbInfo(
    plantName: string,
    confidence: number,
    options: GenerateOptions = {},
  ): Promise<string> {
    const {
      maxTokens = 512,
      temperature = 0.7,
      topP = 0.9,
      onToken,
    } = options;

    if (!this.context || this.status !== 'ready') {
      // 모델이 없으면 시뮬레이션 모드 (오프라인 안전 폴백 - 로컬 지식 즉시 연동)
      return this.generateFallback(plantName, confidence, onToken);
    }

    this.setStatus('generating');
    let fullText = '';

    try {
      const plantKnowledge = HERB_KNOWLEDGE[plantName];
      const userMessage = this.buildUserPrompt(plantName, confidence, plantKnowledge);

      const result = await this.context.completion(
        {
          messages: [
            {role: 'system', content: SYSTEM_PROMPT},
            {role: 'user', content: userMessage},
          ],
          n_predict: maxTokens,
          temperature,
          top_p: topP,
          stop: ['<|im_end|>', '<|endoftext|>', '</s>'],
        },
        onToken
          ? (tokenData: {token: string}) => {
              fullText += tokenData.token;
              onToken(fullText);
            }
          : undefined,
      );

      fullText = result.text;
      this.setStatus('ready');

      if (result.timings) {
        console.log('[LLMService] 추론 시간:', result.timings);
      }

      return fullText;
    } catch (error) {
      console.error('[LLMService] 추론 실패:', error);
      this.setStatus('ready');
      return this.generateFallback(plantName, confidence, onToken);
    }
  }

  /**
   * 사용자 프롬프트 생성 (로컬 RAG 적용)
   */
  private buildUserPrompt(plantName: string, confidence: number, plantKnowledge?: string): string {
    const confidencePercent = Math.round(confidence * 100);

    let prompt = `카메라로 촬영한 식물이 "${plantName}"(으)로 식별되었습니다. (식별 확률: ${confidencePercent}%)\n\n`;

    if (plantKnowledge) {
      prompt += `아래 제공된 [식물 비교 지식] 문서에 적힌 내용을 바탕으로 어르신들이 쉽고 친절하게 대조해볼 수 있도록 약초 정보(효능, 구분 요령, 유사 독초 경고 및 대처법 등)를 정리해 주세요.\n\n`;
      prompt += `[식물 비교 지식]\n${plantKnowledge}\n\n`;
    } else {
      prompt += `이 식물의 효능, 채취 시기, 주의사항을 어르신이 이해하기 쉽게 설명해 주세요. 유사한 독초가 있다면 반드시 경고해 주세요.\n\n`;
    }

    prompt += `주의: 절대로 지식 문서에 없는 내용을 사실인 것처럼 지어내지 말고, 확실치 않은 경우에는 전문가의 동정을 받아야 한다고 덧붙여 주십시오.`;

    return prompt;
  }

  /**
   * 폴백 응답 생성 (LLM 없을 때 하드코딩 또는 로컬 지식 문서 내용 직접 송출)
   */
  private async generateFallback(
    plantName: string,
    confidence: number,
    onToken?: (partialText: string) => void,
  ): Promise<string> {
    const plantKnowledge = HERB_KNOWLEDGE[plantName];
    let text = '';

    if (plantKnowledge) {
      text = `🌿 **${plantName}**의 식별 및 안전 비교 정보입니다.\n\n${plantKnowledge}`;
    } else {
      const fallbackTexts: Record<string, string> = {
        '더덕': `🌿 더덕\n\n` +
          `✅ 효능: 폐 건강, 기관지에 좋고 자양강장에 도움됩니다.\n` +
          `📅 채취 시기: 가을 (9~10월)\n` +
          `🍳 먹는 방법: 구이, 무침, 술 담그기\n` +
          `⚠️ 주의: 더덕 뿌리는 도라지와 비슷하나 향이 다릅니다.`,
      };

      text = fallbackTexts[plantName] ||
        `🌿 ${plantName}\n\n` +
        `식별 확률: ${Math.round(confidence * 100)}%\n\n` +
        `ℹ️ 이 식물에 대한 상세 정보를 불러오지 못했습니다.\n` +
        `AI 모델이 로딩되면 더 자세한 정보를 제공해 드립니다.\n\n` +
        `⚠️ 확실하지 않은 식물은 절대 채취하거나 먹지 마세요!\n` +
        `가까운 산림청 또는 약초 전문가에게 문의하세요.`;
    }

    // 타이핑 효과 시뮬레이션
    if (onToken) {
      for (let i = 0; i < text.length; i++) {
        await new Promise<void>(resolve => setTimeout(resolve, 5)); // 5ms로 타이핑 속도 향상
        onToken(text.substring(0, i + 1));
      }
    }

    return text;
  }

  /**
   * 모델 언로딩 (메모리 해제)
   */
  async unload(): Promise<void> {
    if (this.context) {
      await this.context.release();
      this.context = null;
    }
    this.status = 'idle';
    console.log('[LLMService] 모델 언로딩 완료');
  }
}

/** LLMService 싱글톤 인스턴스 */
export const LLMService = new LLMServiceClass();
