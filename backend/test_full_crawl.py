"""풀 테스트 - 모바일 API로 매물 수집 → DB 저장"""
import asyncio
import sys
sys.path.insert(0, ".")

import httpx
from sqlalchemy.orm import Session

from app.models.database import Base, engine, SessionLocal
from app.models.apartment import ApartmentComplex, Listing


# 강남구 주요 동별 좌표
GANGNAM_DONGS = [
    {"name": "대치동", "cortarNo": "1168010600", "lat": 37.4946, "lon": 127.0573},
    {"name": "역삼동", "cortarNo": "1168010300", "lat": 37.5008, "lon": 127.0368},
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15",
    "Accept": "application/json",
    "Accept-Language": "ko-KR,ko;q=0.9",
    "Referer": "https://m.land.naver.com/",
}


def parse_price(price_str):
    """'24억', '9억 5,000' 등을 만원 단위 정수로 변환"""
    if not price_str:
        return None
    price_str = price_str.replace(",", "").strip()
    total = 0
    if "억" in price_str:
        parts = price_str.split("억")
        total += int(parts[0].strip()) * 10000
        if len(parts) > 1 and parts[1].strip():
            total += int(parts[1].strip())
    else:
        total = int(price_str)
    return total


async def crawl_and_save():
    Base.metadata.create_all(bind=engine)
    db: Session = SessionLocal()
    saved_count = 0

    async with httpx.AsyncClient(follow_redirects=True, timeout=30.0) as client:
        for dong in GANGNAM_DONGS:
            print(f"\n=== {dong['name']} 매물 수집 중 ===")
            await asyncio.sleep(1.5)

            resp = await client.get(
                "https://m.land.naver.com/cluster/ajax/articleList",
                params={
                    "rletTpCd": "APT",
                    "tradTpCd": "A1",
                    "z": "15",
                    "lat": str(dong["lat"]),
                    "lon": str(dong["lon"]),
                    "btm": str(dong["lat"] - 0.01),
                    "lft": str(dong["lon"] - 0.01),
                    "top": str(dong["lat"] + 0.01),
                    "rgt": str(dong["lon"] + 0.01),
                    "cortarNo": dong["cortarNo"],
                    "page": "1",
                },
                headers=HEADERS,
            )

            if resp.status_code != 200:
                print(f"  실패: HTTP {resp.status_code}")
                continue

            data = resp.json()
            articles = data.get("body", [])
            print(f"  매물 {len(articles)}건 수신")

            for a in articles:
                atcl_nm = a.get("atclNm", "")
                hscpNm = a.get("hscpNm", atcl_nm)
                atcl_no = a.get("atclNo", "")
                spc2 = a.get("spc2", 0)
                flr_info = a.get("flrInfo", "")
                prc = a.get("hanPrc", "")
                cfm_ymd = a.get("cfmYmd", "")

                # 층수 파싱
                floor = None
                if flr_info and "/" in str(flr_info):
                    try:
                        floor = int(str(flr_info).split("/")[0])
                    except (ValueError, IndexError):
                        pass

                # 단지 upsert
                complex_obj = db.query(ApartmentComplex).filter_by(
                    naver_complex_no=str(a.get("hscpNo", atcl_no))
                ).first()

                if not complex_obj:
                    complex_obj = ApartmentComplex(
                        naver_complex_no=str(a.get("hscpNo", atcl_no)),
                        name=hscpNm,
                        sido="서울특별시",
                        sigungu="강남구",
                        dong=dong["name"],
                    )
                    db.add(complex_obj)
                    db.flush()

                # 매물 upsert
                listing = db.query(Listing).filter_by(
                    naver_article_id=str(atcl_no)
                ).first()

                asking_price = parse_price(prc)
                if not asking_price:
                    continue

                if not listing:
                    listing = Listing(
                        naver_article_id=str(atcl_no),
                        complex_id=complex_obj.id,
                        dong=dong["name"],
                        area_sqm=float(spc2) if spc2 else 0,
                        floor=floor,
                        asking_price=asking_price,
                        listing_url=f"https://m.land.naver.com/article/info/{atcl_no}",
                        is_active=True,
                    )
                    db.add(listing)
                    saved_count += 1
                else:
                    listing.asking_price = asking_price
                    listing.is_active = True

                print(f"  - {hscpNm} | {spc2}㎡ | {flr_info} | {prc}")

            db.commit()

    print(f"\n=== 완료: {saved_count}건 저장 ===")

    # DB 확인
    total_complexes = db.query(ApartmentComplex).count()
    total_listings = db.query(Listing).filter_by(is_active=True).count()
    print(f"DB 단지: {total_complexes}개, 활성 매물: {total_listings}개")
    db.close()


if __name__ == "__main__":
    asyncio.run(crawl_and_save())
