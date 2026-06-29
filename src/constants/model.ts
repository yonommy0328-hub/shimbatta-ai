/**
 * 심봤다 AI — Model Constants (모델 설정 상수)
 *
 * 앱 내에서 로드하는 LLM 모델(GGUF) 및 Vision 모델(TFLite)의 설정을 관리합니다.
 * 출시 직전 더 작은 모델로 교체하여 배포할 때 아래 상수 값을 변경해 주세요.
 */

/**
 * 기본 GGUF LLM 모델 파일 이름
 * (예: qwen2.5-0.5b-instruct.Q4_K_M.gguf, qwen2.5-1.5b-instruct.Q4_K_M.gguf 등)
 */
export const DEFAULT_LLM_MODEL_NAME = 'Qwen2.5-0.5B-Instruct-Q4_K_M.gguf';

/**
 * 기본 TFLite Vision 모델 파일 이름
 */
export const DEFAULT_VISION_MODEL_NAME = 'herb_classifier.tflite';
