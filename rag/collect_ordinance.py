# 파일명: collect_ordinance.py
import requests
import json
import os
import time
import random
from dotenv import load_dotenv

load_dotenv()
OC = os.getenv("LAW_API_KEY")

if not os.path.exists("data/ordinance"):
    os.makedirs("data/ordinance")

KEYWORDS = [
    "노인복지",
    "고령자",
    "노인일자리",
    "노인돌봄",
    "경로당",
    "노인여가",
    "노인맞춤돌봄",
    "기초연금",
]

def search_ordinances(keyword, page=1):
    url = "http://www.law.go.kr/DRF/lawSearch.do"
    params = {
        "OC": OC,
        "target": "ordin",
        "type": "JSON",
        "query": keyword,
        "display": 100,
        "page": page,
    }
    try:
        time.sleep(random.uniform(0.5, 1.0))
        res = requests.get(url, params=params, timeout=10)
        data = res.json()

        # ✅ 조례는 OrdinSearch!
        search = data.get("OrdinSearch", {})
        total  = search.get("totalCnt", 0)
        laws   = search.get("law", [])

        if isinstance(laws, dict):
            laws = [laws]

        return laws, int(total)
    except Exception as e:
        print(f"    ❌ 오류: {e}")
        return [], 0

def get_ordinance_detail(mst_id, ordinance_name):
    """조례 상세 내용 수집 (자치법규일련번호 사용!)"""
    url = "http://www.law.go.kr/DRF/lawService.do"
    params = {
        "OC": OC,
        "target": "ordin",
        "type": "JSON",
        "MST": mst_id,   # ✅ 법령ID 아니고 자치법규일련번호!
    }
    try:
        time.sleep(random.uniform(0.5, 1.0))
        res = requests.get(url, params=params, timeout=10)
        return res.json()
    except Exception as e:
        print(f"    ❌ 상세 오류 ({ordinance_name}): {e}")
        return None

def collect_all():
    print("📥 노인/고령층 관련 조례 수집 시작!\n")
    print("=" * 50)

    all_ordinances = []
    seen_ids = set()

    for keyword in KEYWORDS:
        print(f"\n🔍 '{keyword}' 검색 중...")
        page = 1
        keyword_count = 0

        while True:
            laws, total = search_ordinances(keyword, page)

            if not laws:
                print(f"  결과 없음")
                break

            print(f"  {page}페이지: {len(laws)}개 (전체 {total}개)")

            for law in laws:
                # ✅ 키 이름 수정!
                ordin_id   = law.get("자치법규ID", "")
                mst_id     = law.get("자치법규일련번호", "")
                ordin_name = law.get("자치법규명", "")
                org        = law.get("지자체기관명", "")
                kind       = law.get("자치법규종류", "")
                date       = law.get("시행일자", "")

                if ordin_id in seen_ids:
                    continue
                seen_ids.add(ordin_id)

                print(f"    📄 [{org}] {ordin_name}")

                detail = get_ordinance_detail(mst_id, ordin_name)

                all_ordinances.append({
                    "키워드":       keyword,
                    "조례명":       ordin_name,
                    "자치법규ID":   ordin_id,
                    "일련번호":     mst_id,
                    "지자체기관명": org,
                    "종류":         kind,
                    "시행일자":     date,
                    "상세내용":     detail
                })
                keyword_count += 1

            if page * 100 >= int(total):
                break
            page += 1

        print(f"  ✅ '{keyword}' 완료: {keyword_count}개")

        # 키워드별 중간 저장
        keyword_data = [o for o in all_ordinances if o["키워드"] == keyword]
        with open(f"data/ordinance/{keyword}_조례_raw.json", "w", encoding="utf-8") as f:
            json.dump(keyword_data, f, ensure_ascii=False, indent=2)

    # 전체 저장
    with open("data/ordinance/전체_조례_raw.json", "w", encoding="utf-8") as f:
        json.dump(all_ordinances, f, ensure_ascii=False, indent=2)

    print("\n" + "=" * 50)
    print(f"✅ 전체 완료! 총 {len(all_ordinances)}개 조례 수집")
    print(f"📁 저장 위치: data/ordinance/")

if __name__ == "__main__":
    collect_all()