# 파일명: 01_collect.py
import requests
import json
import os
import time
import random
from dotenv import load_dotenv
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

load_dotenv()
OC = os.getenv("LAW_API_KEY")

# 수집할 법령 목록 (5개 전체)
LAW_LIST = [
    "근로기준법",
    "최저임금법",
    "고용보험법",
    "근로자퇴직급여 보장법",
    "고용상 연령차별금지 및 고령자 고용촉진에 관한 법률", 
    "노인복지법",           
    "기초연금법"
]

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Connection': 'close'
}

def get_session():
    session = requests.Session()
    retries = Retry(
        total=5,
        backoff_factor=1,
        status_forcelist=[500, 502, 503, 504],
        allowed_methods=["GET"]
    )
    session.mount('http://', HTTPAdapter(max_retries=retries))
    session.headers.update(HEADERS)
    return session

session = get_session()

def get_law_id(law_name):
    url = "http://www.law.go.kr/DRF/lawSearch.do"
    params = {
        "OC": OC,
        "target": "law",
        "type": "JSON",
        "query": law_name
    }
    time.sleep(random.uniform(1.0, 2.0))
    res = session.get(url, params=params)
    data = res.json()

    try:
        law_id = data["LawSearch"]["law"][0]["법령ID"]
        law_name_kr = data["LawSearch"]["law"][0]["법령명한글"]
        return law_id, law_name_kr
    except:
        print(f"❌ {law_name} 검색 실패")
        return None, None

def get_law_articles(law_id, law_name_kr):
    url = "http://www.law.go.kr/DRF/lawService.do"
    params = {
        "OC": OC,
        "target": "law",
        "type": "JSON",
        "ID": law_id
    }

    if not os.path.exists("data"):
        os.makedirs("data")

    res = session.get(url, params=params)
    data = res.json()

    filename = f"data/{law_name_kr}_raw.json"
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    article_count = len(data["법령"]["조문"]["조문단위"])
    return article_count

def collect_all():
    print("📥 법령 데이터 수집 시작!\n")
    results = []

    for law_name in LAW_LIST:
        print(f"🔍 {law_name} 검색 중...")
        law_id, law_name_kr = get_law_id(law_name)

        if law_id:
            count = get_law_articles(law_id, law_name_kr)
            print(f"✅ {law_name_kr} 완료! ({count}개 조문)\n")
            results.append({"법령명": law_name_kr, "조문수": count})
        else:
            print(f"❌ {law_name} 실패\n")

    # 결과 출력
    print("=" * 40)
    print("📊 수집 결과 요약")
    print("=" * 40)
    for r in results:
        print(f"✅ {r['법령명']}: {r['조문수']}개 조문")

    # 결과 파일 저장
    with open("data/수집결과요약.txt", "w", encoding="utf-8") as f:
        f.write("📊 수집 결과 요약\n")
        f.write("=" * 40 + "\n")
        for r in results:
            f.write(f"✅ {r['법령명']}: {r['조문수']}개 조문\n")
        f.write("=" * 40 + "\n")
        total = sum(r['조문수'] for r in results)
        f.write(f"📌 전체 조문 수: {total}개\n")

    print(f"\n📌 전체 조문 수: {sum(r['조문수'] for r in results)}개")
    print("📄 요약 파일 저장 완료! → data/수집결과요약.txt")

if __name__ == "__main__":
    collect_all()