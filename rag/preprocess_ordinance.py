# 파일명: preprocess_ordinance.py
import json
import os

RAW_FILE = "data/ordinance/전체_조례_raw.json"

if not os.path.exists(RAW_FILE):
    print(f"❌ 파일 없음: {RAW_FILE}")
    print("   collect_ordinance.py 를 먼저 실행해주세요!")
    exit()

print("🔧 조례 전처리 시작!")

with open(RAW_FILE, "r", encoding="utf-8") as f:
    ordinances = json.load(f)

print(f"  총 {len(ordinances)}개 조례 로드됨")

all_docs = []

for ordin in ordinances:
    try:
        ordin_name = ordin.get("조례명", "")
        org        = ordin.get("지자체기관명", "")
        kind       = ordin.get("종류", "")
        date       = ordin.get("시행일자", "")
        keyword    = ordin.get("키워드", "")
        detail     = ordin.get("상세내용", {})

        # 조문 내용 추출
        articles = []
        if detail:
            try:
                units = (
                    detail.get("자치법규", {})
                          .get("조문", {})
                          .get("조문단위", [])
                )
                if isinstance(units, dict):
                    units = [units]
                for unit in units:
                    content = unit.get("조문내용", "")
                    if content:
                        articles.append({
                            "조문번호": unit.get("조문번호", ""),
                            "조문제목": unit.get("조문제목", ""),
                            "조문내용": content
                        })
            except Exception:
                pass

        # 조문이 있으면 조문별로 저장
        if articles:
            for article in articles:
                content = (
                    f"[{org}] {ordin_name} "
                    f"제{article['조문번호']}조({article['조문제목']}): "
                    f"{article['조문내용']}"
                )
                if len(content.strip()) > 20:
                    all_docs.append({
                        "content":    content,
                        "type":       "조례",
                        "조례명":     ordin_name,
                        "지자체":     org,
                        "종류":       kind,
                        "시행일자":   date,
                        "키워드":     keyword,
                        "조문번호":   article["조문번호"],
                        "조문제목":   article["조문제목"],
                    })
        else:
            # 조문 없으면 조례명+기관명으로 기본 문서 생성
            content = f"[{org}] {ordin_name} ({kind}, 시행일: {date})"
            all_docs.append({
                "content":  content,
                "type":     "조례",
                "조례명":   ordin_name,
                "지자체":   org,
                "종류":     kind,
                "시행일자": date,
                "키워드":   keyword,
            })

    except Exception:
        continue

print(f"  변환 완료: {len(all_docs)}개")

if len(all_docs) == 0:
    print("❌ 처리할 조례가 없어요!")
    exit()

# 샘플 확인
print("\n샘플 3개:")
for doc in all_docs[:3]:
    print(f"  {doc['content'][:80]}...")

# JSON 저장
output_path = "data/전처리완료_조례.json"
with open(output_path, "w", encoding="utf-8") as f:
    json.dump(all_docs, f, ensure_ascii=False, indent=2)

print(f"\n✅ 전처리 완료! → {output_path}")
print(f"총 {len(all_docs)}개 조례 저장됨")