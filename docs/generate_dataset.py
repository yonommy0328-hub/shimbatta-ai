# -*- coding: utf-8 -*-
"""
심봤다 AI — 지식 기반 학습 데이터셋(JSONL) 생성 스크립트
본 스크립트는 docs/fine_tuning_knowledge.md 파일을 파싱하여
Google Colab 및 파인튜닝용 JSONL (instruction-output) 데이터셋을 생성합니다.
"""

import os
import json
import re

def parse_markdown_knowledge(md_path):
    if not os.path.exists(md_path):
        print(f"오류: {md_path} 파일을 찾을 수 없습니다. 경로를 확인해 주세요.")
        return None

    with open(md_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # ## 기준으로 대분류 분할 (정확히 ##만 매칭, ###는 분할하지 않음)
    sections = re.split(r'\n##\s+', '\n' + content)
    pairs = []

    for section in sections:
        section = section.strip()
        if not section:
            continue

        lines = section.split('\n')
        header = lines[0].strip()

        # 식용 vs 독초 대비 섹션 매칭 (예: "1. 산마늘(식용) vs 박새·은방울꽃(독초)")
        if 'vs' in header and ('식용' in header or '독초' in header):
            pair_info = {
                "title": header,
                "edible": None,
                "toxics": []
            }

            # ### 기준으로 식물 상세정보 분할 (정확히 ###만 매칭)
            subsections = re.split(r'\n###\s+', '\n' + section)
            for sub in subsections[1:]:
                sub = sub.strip()
                if not sub:
                    continue
                sub_lines = sub.split('\n')
                sub_header = sub_lines[0].strip()

                # 식물 이름 추출: "[식용 약초] 산마늘 (Allium ochotense)" -> "산마늘"
                name_match = re.search(r'\]\s*([^(]+)', sub_header)
                if name_match:
                    plant_name = name_match.group(1).strip()
                else:
                    plant_name = sub_header.split('(')[0].replace('[식용 약초]', '').replace('[독초]', '').strip()

                # 속성 추출 (bullet points 파싱)
                properties = {}
                current_prop = None
                for line in sub_lines[1:]:
                    line = line.strip()
                    if not line:
                        continue
                    
                    # * **속성명**: 내용 패턴 매칭
                    prop_match = re.match(r'^[\*\-]\s*\*\*([^*]+)\*\*:\s*(.*)', line)
                    if prop_match:
                        current_prop = prop_match.group(1).strip()
                        properties[current_prop] = prop_match.group(2).strip()
                    elif (line.startswith('*') or line.startswith('-') or line.startswith(' ')) and current_prop:
                        # 속성 텍스트 줄바꿈 연결
                        properties[current_prop] += " " + line.lstrip('*-\t ').strip()
                    elif current_prop and not line.startswith('#'):
                        # 일반 텍스트 추가 연결
                        properties[current_prop] += " " + line

                plant_data = {
                    "name": plant_name,
                    "header": sub_header,
                    "properties": properties
                }

                if '식용' in sub_header:
                    pair_info["edible"] = plant_data
                elif '독초' in sub_header:
                    pair_info["toxics"].append(plant_data)

            if pair_info["edible"]:
                pairs.append(pair_info)

    return pairs

def generate_jsonl_dataset(parsed_pairs, output_path):
    dataset = []

    # 각 약초-독초 쌍에 대해 다양한 프롬프트 패턴 생성 (데이터 증강)
    for pair in parsed_pairs:
        edible = pair["edible"]
        ed_name = edible["name"]
        
        # 유연한 부분 매칭을 위한 헬퍼 함수
        def get_prop(plant, keywords, default=""):
            for prop_name, prop_val in plant["properties"].items():
                for kw in keywords:
                    if kw in prop_name:
                        return prop_val
            return default

        ed_efficacy = get_prop(edible, ["효능"])
        ed_structure = get_prop(edible, ["구조", "형태", "잎 및 뿌리"])
        ed_texture = get_prop(edible, ["주름", "질감", "솜털", "마디", "관절"])
        ed_sensory = get_prop(edible, ["냄새", "광택", "수액", "향", "감각"])
        ed_habitat = get_prop(edible, ["자생"])

        for toxic in pair["toxics"]:
            tx_name = toxic["name"]
            tx_class = get_prop(toxic, ["분류"])
            tx_structure = get_prop(toxic, ["구조", "형태", "잎 및 뿌리"])
            tx_texture = get_prop(toxic, ["주름", "질감", "솜털", "마디", "관절"])
            tx_sensory = get_prop(toxic, ["냄새", "광택", "수액", "향", "감각"])
            tx_habitat = get_prop(toxic, ["자생"])
            tx_poison = get_prop(toxic, ["독성", "부작용"])

            # ----------------------------------------------------
            # 패턴 1: 1단계 비전 식별 연동형 (식용 약초 검출 상황)
            # ----------------------------------------------------
            prompt_1 = f"카메라로 촬영한 식물이 \"{ed_name}\"(으)로 식별되었습니다. (식별 확률: 95%) 이 식물의 효능과 채취법, 그리고 주의해야 할 유사 독초에 대해 어르신이 이해하기 쉽게 설명해 주세요."
            
            response_1 = (
                f"🌿 **{ed_name}**로 식별되었습니다! (확률: 95%)\n\n"
                f"어르신들이 산에서 안전하게 채취하고 건강하게 드실 수 있도록 {ed_name} 정보를 정리해 드립니다.\n\n"
                f"### 1. 어르신 맞춤형 효능\n- {ed_efficacy}\n\n"
                f"### 2. 생김새와 자생 환경\n- **잎 구조:** {ed_structure}\n- **자생지:** {ed_habitat}\n\n"
                f"### 3. ⚠️ 유사 독초 [{tx_name}] 주의 경고 (필독!)\n"
                f"**{ed_name}**은 맹독성 독초인 **{tx_name}**와 아주 비슷하게 생겨 혼동하기 쉽습니다. 아래 차이점을 반드시 대조해 보세요!\n\n"
                f"- **잎 주름과 촉감:**\n"
                f"  * **{ed_name} (식용):** {ed_texture}\n"
                f"  * **{tx_name} (독초):** {tx_texture}\n"
                f"- **냄새 및 광택:**\n"
                f"  * **{ed_name} (식용):** {ed_sensory}\n"
                f"  * **{tx_name} (독초):** {tx_sensory}\n\n"
                f"💡 **안전 요령:** 마늘 냄새가 나지 않거나 잎에 깊은 주름이 있다면 절대 채취해서는 안 됩니다!"
            )
            dataset.append({
                "conversations": [
                    {"role": "user", "content": prompt_1},
                    {"role": "assistant", "content": response_1}
                ]
            })

            # ----------------------------------------------------
            # 패턴 2: 직접 비교 질문형 (약초 vs 독초 구분법)
            # ----------------------------------------------------
            prompt_2 = f"{ed_name}와 {tx_name}의 생김새와 감각적 차이점을 어떻게 구분하나요? 상세히 알려주세요."
            
            response_2 = (
                f"🌿 **{ed_name}(식용)**와 ⚠️ **{tx_name}(독초)**은 겉모습이 매우 닮아 오인 중독 사고가 빈번합니다. 아래의 핵심 차이점을 꼭 기억해 두세요!\n\n"
                f"### 1. 잎 구조 및 질감 차이\n"
                f"- **{ed_name} (식용):** {ed_structure} {ed_texture}\n"
                f"- **{tx_name} (독초):** {tx_structure} {tx_texture}\n\n"
                f"### 2. 냄새와 광택 (오감으로 구분하는 방법)\n"
                f"- **{ed_name} (식용):** {ed_sensory}\n"
                f"- **{tx_name} (독초):** {tx_sensory}\n\n"
                f"### 3. 자생 환경 차이\n"
                f"- **{ed_name} (식용):** {ed_habitat}\n"
                f"- **{tx_name} (독초):** {tx_habitat}\n\n"
                f"⚠️ **{tx_name}을 섭취했을 때의 위험:**\n"
                f"{tx_poison}\n\n"
                f"💡 확실하게 구분이 안 되는 것은 절대 뜯지도 먹지도 마세요!"
            )
            dataset.append({
                "conversations": [
                    {"role": "user", "content": prompt_2},
                    {"role": "assistant", "content": response_2}
                ]
            })

            # ----------------------------------------------------
            # 패턴 3: 독성 부작용 및 증상 상세 질문형
            # ----------------------------------------------------
            prompt_3 = f"독초인 {tx_name}의 독성 성분은 무엇이며, 실수로 먹으면 어떤 중독 증상이 나타나나요?"
            
            response_3 = (
                f"⚠️ 맹독성 독초인 **{tx_name}**의 독성 정보와 중독 시 발생하는 치명적인 증상은 다음과 같습니다.\n\n"
                f"### 1. 식물학적 분류 및 독성 성분\n"
                f"- **분류:** {tx_class}\n"
                f"- **독성 정보:** {tx_poison}\n\n"
                f"### 2. 주요 중독 증상\n"
                f"실수로 섭취할 경우 침 흘림, 격렬한 구토, 복통, 설사를 시작으로 사지 마비, 심장 부정맥, 호흡 곤란이 발생하며 심한 경우 심정지로 급사할 수 있어 매우 치명적입니다.\n\n"
                f"### 3. 섭취 후 응급 처치 요령\n"
                f"- 의식이 있는 경우 즉시 목 안쪽을 자극해 구토를 유도하여 독소가 몸에 흡수되는 양을 줄여야 합니다.\n"
                f"- **[가장 중요]** 환자가 먹고 남은 식물의 잔여물을 비닐봉지에 밀봉하여 반드시 병원 응급실로 같이 가져가야 해독 요령 및 정밀 진단을 빠르게 받을 수 있습니다."
            )
            dataset.append({
                "conversations": [
                    {"role": "user", "content": prompt_3},
                    {"role": "assistant", "content": response_3}
                ]
            })

    # 공통 응급 처치 및 자생 환경 지식 패턴 추가
    prompt_common = "산에서 독초를 잘못 뜯어 먹었을 때 어떻게 대처해야 하나요? 응급 처치 요령을 알려주세요."
    response_common = (
        "⚠️ **야생 독초 섭취 시 응급 처치 및 골든타임 행동 요령**\n\n"
        "야생 식물을 섭취한 후 구토, 설사, 복통, 어지럼증 등의 증상이 나타나면 즉시 다음 수칙을 따라야 합니다.\n\n"
        "### 1. 즉각적인 구토 유도 (의식이 있을 때만!)\n"
        "- 독소가 소화기계에 완전히 흡수되기 전 즉시 목구멍 안쪽을 자극하여 구토를 하도록 유도합니다.\n"
        "- 단, 의식이 혼미하거나 없는 상태에서 구토를 시도하면 토사물이 기도를 막아 질식할 위험이 있으므로 절대 억지로 구토를 시도해서는 안 됩니다.\n\n"
        "### 2. 먹다 남은 식물 챙기기 (가장 결정적인 행동)\n"
        "- **환자가 먹다 남은 식물이나 채취해 둔 잔여 식물을 반드시 비닐봉지에 넣고 밀봉하여 응급실에 함께 가져가야 합니다.**\n"
        "- 병원의 임상 독성 전문가가 식물을 육안/성분으로 신속하게 판정(동정)해야 정확한 해독제 처방 및 맞춤형 대증 요령 치료를 결정할 수 있습니다.\n\n"
        "### 3. 즉시 119 신고 및 병원 이송\n"
        "- 자가 치료를 하려 하지 말고, 민간요법을 맹신하지 마시고 즉각 병원 응급실로 환자를 이송해 수액 치료 및 전문 처방을 받아야 장기 손상을 막을 수 있습니다."
    )
    dataset.append({
        "conversations": [
            {"role": "user", "content": prompt_common},
            {"role": "assistant", "content": response_common}
        ]
    })

    # JSONL 파일 쓰기
    with open(output_path, 'w', encoding='utf-8') as f:
        for item in dataset:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')

    print(f"성공: {len(dataset)}개의 Q&A 학습 데이터가 생성되었습니다.")
    print(f"저장 경로: {output_path}")

if __name__ == "__main__":
    # 프로젝트 내 상대경로 설정
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    md_file = os.path.join(base_dir, "docs", "fine_tuning_knowledge.md")
    output_file = os.path.join(base_dir, "docs", "shimbatta_train_dataset.jsonl")

    print("--- 심봤다 AI 파인튜닝 데이터셋 생성 시작 ---")
    pairs = parse_markdown_knowledge(md_file)
    if pairs:
        generate_jsonl_dataset(pairs, output_file)
