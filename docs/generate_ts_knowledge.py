# -*- coding: utf-8 -*-
import os
import re

def compile_markdown_to_ts(md_path, ts_path):
    if not os.path.exists(md_path):
        print(f"Error: {md_path} not found.")
        return

    with open(md_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Split into sections by ##
    sections = re.split(r'\n##\s+', '\n' + content)
    
    knowledge_map = {}
    
    # Defined plant names to look for in headers
    plant_names = [
        "산마늘", "박새", "은방울꽃",
        "곰취", "동의나물",
        "원추리", "여로",
        "참당귀", "개당귀",
        "우산나물", "삿갓나물",
        "머위", "털머위",
        "미나리", "독미나리",
        "부추", "달래", "수선화", "상사화",
        "도라지", "더덕", "인삼", "미국자리공"
    ]

    for section in sections:
        section = section.strip()
        if not section:
            continue
        
        lines = section.split('\n')
        header = lines[0].strip()
        
        # Check if this is a comparison section (contains vs or comparison keywords)
        if 'vs' in header or '비교' in header or any(name in header for name in plant_names):
            # Clean up header prefix numbers
            clean_header = re.sub(r'^\d+\.\s*', '', header)
            
            # Find which plants are discussed in this section
            matched_plants = []
            for name in plant_names:
                if name in header:
                    matched_plants.append(name)
            
            # If we matched plants, store this section's markdown content
            if matched_plants:
                # Reconstruct the section markdown (prefixed with ## to preserve headers)
                section_markdown = f"## {section}"
                for plant in matched_plants:
                    knowledge_map[plant] = section_markdown

    # Write TypeScript file
    with open(ts_path, 'w', encoding='utf-8') as f:
        f.write("/**\n")
        f.write(" * 심봤다 AI — 로컬 오프라인 RAG 지식 데이터베이스\n")
        f.write(" * 이 파일은 docs/generate_ts_knowledge.py에 의해 shimbatta_knowledge.md로부터 자동 생성되었습니다.\n")
        f.write(" */\n\n")
        f.write("export const HERB_KNOWLEDGE: Record<string, string> = {\n")
        
        for plant, md in sorted(knowledge_map.items()):
            # Escape backticks and backslashes for TS template literals
            escaped_md = md.replace('\\', '\\\\').replace('`', '\\`').replace('$', '\\$')
            f.write(f"  '{plant}': `\n{escaped_md}\n`,\n")
            
        f.write("};\n")
        
    print(f"Success: Compiled {len(knowledge_map)} plants to {ts_path}")

if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    md_file = os.path.join(base_dir, "shimbatta_knowledge.md")
    ts_file = os.path.join(base_dir, "src", "constants", "herbKnowledge.ts")
    compile_markdown_to_ts(md_file, ts_file)
