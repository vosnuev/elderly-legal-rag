# 파일명: preprocess_law.py
import json
import os

LAW_FILES = [
    {"file": "data/근로기준법_raw.json",           "name": "근로기준법"},
    {"file": "data/최저임금법_raw.json",            "name": "최저임금법"},
    {"file": "data/고용보험법_raw.json",            "name": "고용보험법"},
    {"file": "data/근로자퇴직급여 보장법_raw.json", "name": "근로자퇴직급여 보장법"},
    {"file": "data/기초연금법_raw.json",            "name": "기초연금법"},
    {"file": "data/노인복지법_raw.json",            "name": "노인복지법"},
    {"file": "data/고용상 연령차별금지 및 고령자고용촉진에 관한 법률_raw.json",
     "name": "고령자고용촉진법"},
]

if not os.path.exists("data/preprocessed"):
    os.makedirs("data/preprocessed")

print("🔧 법령 전처리 시작!\n")

for law in LAW_FILES:
    if not os.path.exists(law["file"]):
        print(f"  ⚠️ 파일 없음: {law['file']}")
        continue

    with open(law["file"], "r", encoding="utf-8") as f:
        data = json.load(f)

    articles = data["법령"]["조문"]["조문단위"]
    docs = []
    for article in articles:
        content = article.get("조문내용", "")
        if content:
            docs.append({
                "content":  content,
                "law_name": law["name"],
                "article":  article.get("조문번호", ""),
                "title":    article.get("조문제목", "")
            })

    # ✅ 법령별로 따로 저장!
    output_path = f"data/preprocessed/{law['name']}_전처리.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(docs, f, ensure_ascii=False, indent=2)

    print(f"  ✅ {law['name']}: {len(docs)}개 조문 → {output_path}")

print(f"\n✅ 전체 완료!")
print(f"📁 저장 위치: data/preprocessed/")