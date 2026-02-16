"""네이버 부동산 API 도구 - CrewAI Tool 데코레이터 사용"""

import json
import time
import re
import requests
from crewai.tools import tool

# 공통 헤더
HEADERS = {
    "Accept-Encoding": "gzip",
    "Host": "new.land.naver.com",
    "Referer": "https://new.land.naver.com/complexes/102378",
    "Sec-Fetch-Dest": "empty",
    "Sec-Fetch-Mode": "cors",
    "Sec-Fetch-Site": "same-origin",
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
}

BASE_URL = "https://new.land.naver.com/api"


def _request_get(url: str, headers: dict | None = None, allow_redirects: bool = True) -> requests.Response:
    """공통 GET 요청 + 딜레이"""
    h = headers or HEADERS
    time.sleep(0.4)
    resp = requests.get(url, headers=h, timeout=10, allow_redirects=allow_redirects)
    return resp


@tool("search_apartment_complex")
def search_apartment_complex(apartment_name: str) -> str:
    """아파트 이름으로 네이버 부동산에서 단지를 검색합니다.
    아파트 이름(예: '래미안퍼스티지', '반포자이')을 입력하면
    해당하는 단지의 complexNo, 이름, 주소 목록을 반환합니다."""
    results = []

    try:
        # 방법 1: 네이버 부동산 자동완성 API 사용
        autocomplete_url = (
            f"https://new.land.naver.com/api/search?keyword={apartment_name}"
        )
        resp = _request_get(autocomplete_url)
        if resp.status_code == 200:
            data = resp.json()
            # complexes 키에서 단지 정보 추출
            complexes = data.get("complexes", [])
            for c in complexes:
                results.append({
                    "complexNo": c.get("complexNo", ""),
                    "complexName": c.get("complexName", ""),
                    "address": c.get("address", c.get("roadAddress", "")),
                    "totalHouseholdCount": c.get("totalHouseholdCount", ""),
                    "cortarNo": c.get("cortarNo", ""),
                })

        # 방법 2: 자동완성에서 못 찾으면 모바일 검색 시도
        if not results:
            mobile_headers = {
                "User-Agent": HEADERS["User-Agent"],
                "Referer": "https://m.land.naver.com/",
            }
            search_url = f"https://m.land.naver.com/search/result/{apartment_name}"
            resp = _request_get(search_url, headers=mobile_headers, allow_redirects=False)
            if resp.status_code in (301, 302):
                location = resp.headers.get("Location", "")
                # /complex/info/12345 패턴에서 complexNo 추출
                match = re.search(r"/complex/info/(\d+)", location)
                if match:
                    complex_no = match.group(1)
                    results.append({
                        "complexNo": complex_no,
                        "complexName": apartment_name,
                        "address": "",
                    })

    except Exception as e:
        return json.dumps({"error": f"검색 중 오류 발생: {str(e)}"}, ensure_ascii=False)

    if not results:
        return json.dumps(
            {"message": f"'{apartment_name}'에 해당하는 단지를 찾지 못했습니다."},
            ensure_ascii=False,
        )

    return json.dumps(results, ensure_ascii=False)


@tool("get_complex_listings")
def get_complex_listings(complex_no: str) -> str:
    """단지 번호(complexNo)로 현재 매물 목록을 조회합니다.
    매매/전세 매물의 가격, 층수, 면적, 거래유형 등을 반환합니다."""
    try:
        # 1) 단지 기본 정보 조회
        complex_url = f"{BASE_URL}/complexes/{complex_no}?sameAddressGroup=false"
        resp = _request_get(complex_url)
        complex_info = {}
        if resp.status_code == 200:
            data = resp.json()
            complex_data = data.get("complexDetail", data)
            complex_info = {
                "complexName": complex_data.get("complexName", ""),
                "address": complex_data.get("address", complex_data.get("roadAddress", "")),
                "totalHouseholdCount": complex_data.get("totalHouseholdCount", ""),
                "approvalDate": complex_data.get("useApproveYmd", ""),
            }

        # 2) 매매 매물 조회
        listings = []
        for trade_type, trade_name in [("A1", "매매"), ("B1", "전세")]:
            articles_url = (
                f"{BASE_URL}/complexes/{complex_no}/articles?"
                f"realEstateType=APT&tradeType={trade_type}"
                f"&tag=%3A%3A%3A%3A%3A%3A&rentPriceMin=0&rentPriceMax=900000000"
                f"&priceMin=0&priceMax=900000000&areaMin=0&areaMax=900000000"
                f"&oldBuildYears&recentlyBuildYears&minHouseHoldCount"
                f"&maxHouseHoldCount&showArticle=false&sameAddressGroup=true"
                f"&sortedBy=prc&page=1"
            )
            resp = _request_get(articles_url)
            if resp.status_code == 200:
                data = resp.json()
                article_list = data.get("articleList", [])
                for article in article_list:
                    price = article.get("dealOrWarrantPrc", "")
                    # 가격 문자열 → 숫자 변환 ("12억 5,000" → 125000)
                    price_manwon = _parse_price(price)

                    listings.append({
                        "complex_name": complex_info.get("complexName", ""),
                        "address": complex_info.get("address", ""),
                        "articleNo": article.get("articleNo", ""),
                        "area_pyeong": article.get("areaName", ""),
                        "area_m2": article.get("area1", article.get("area2", "")),
                        "floor": article.get("floorInfo", ""),
                        "price_text": price,
                        "price_manwon": price_manwon,
                        "trade_type": trade_name,
                        "direction": article.get("direction", ""),
                        "article_confirm_date": article.get("articleConfirmYmd", ""),
                        "realtor_name": article.get("realtorName", ""),
                    })

        result = {
            "complex_info": complex_info,
            "total_listings": len(listings),
            "listings": listings,
        }
        return json.dumps(result, ensure_ascii=False)

    except Exception as e:
        return json.dumps({"error": f"매물 조회 중 오류 발생: {str(e)}"}, ensure_ascii=False)


@tool("get_article_detail")
def get_article_detail(article_no: str) -> str:
    """매물 번호(articleNo)로 상세 정보를 조회합니다.
    매물의 상세 가격, 면적, 방향, 설명 등을 반환합니다."""
    try:
        detail_url = (
            f"https://fin.land.naver.com/front-api/v1/article/basicInfo?"
            f"articleId={article_no}"
        )
        detail_headers = {
            **HEADERS,
            "Host": "fin.land.naver.com",
            "Referer": f"https://fin.land.naver.com/article/info/{article_no}",
        }
        resp = _request_get(detail_url, headers=detail_headers)
        if resp.status_code == 200:
            data = resp.json()
            return json.dumps(data, ensure_ascii=False)
        else:
            return json.dumps(
                {"error": f"상세 조회 실패 (HTTP {resp.status_code})"},
                ensure_ascii=False,
            )
    except Exception as e:
        return json.dumps({"error": f"상세 조회 중 오류: {str(e)}"}, ensure_ascii=False)


def _parse_price(price_str: str) -> int:
    """네이버 부동산 가격 문자열을 만원 단위 정수로 변환.
    예: '12억 5,000' → 125000, '3억' → 30000, '5,500' → 5500
    """
    if not price_str:
        return 0
    price_str = price_str.replace(",", "").replace(" ", "")
    total = 0
    # '억' 단위 처리
    if "억" in price_str:
        parts = price_str.split("억")
        try:
            total += int(parts[0]) * 10000
        except ValueError:
            pass
        remainder = parts[1] if len(parts) > 1 else ""
        if remainder:
            try:
                total += int(remainder)
            except ValueError:
                pass
    else:
        try:
            total = int(price_str)
        except ValueError:
            pass
    return total


if __name__ == "__main__":
    # 간단한 테스트
    print("=== 아파트 검색 테스트 ===")
    result = search_apartment_complex.run("래미안퍼스티지")
    print(result)
    print()

    parsed = json.loads(result)
    if isinstance(parsed, list) and len(parsed) > 0:
        cno = parsed[0]["complexNo"]
        print(f"=== 매물 조회 테스트 (complexNo: {cno}) ===")
        listings_result = get_complex_listings.run(cno)
        print(listings_result[:2000])
