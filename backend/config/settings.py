from typing import Dict, List

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql://suelee@localhost:5432/find_my_home"

    # KB시세 수집 스케줄
    KB_PRICE_CRON_HOUR: int = 6
    KB_PRICE_CRON_MINUTE: int = 0

    # 공공데이터포털 API 인증키 (data.go.kr)
    DATA_GO_KR_API_KEY: str = ""

    # 실거래가 수집 대상 지역 — 수도권 + 5대 광역시 = 110개
    TARGET_REGIONS: List[Dict[str, str]] = [
        # ── 서울특별시 25구 ──
        {"sido": "서울특별시", "sigungu": "강남구"},
        {"sido": "서울특별시", "sigungu": "서초구"},
        {"sido": "서울특별시", "sigungu": "송파구"},
        {"sido": "서울특별시", "sigungu": "용산구"},
        {"sido": "서울특별시", "sigungu": "마포구"},
        {"sido": "서울특별시", "sigungu": "성동구"},
        {"sido": "서울특별시", "sigungu": "강동구"},
        {"sido": "서울특별시", "sigungu": "영등포구"},
        {"sido": "서울특별시", "sigungu": "양천구"},
        {"sido": "서울특별시", "sigungu": "강서구"},
        {"sido": "서울특별시", "sigungu": "관악구"},
        {"sido": "서울특별시", "sigungu": "동작구"},
        {"sido": "서울특별시", "sigungu": "구로구"},
        {"sido": "서울특별시", "sigungu": "금천구"},
        {"sido": "서울특별시", "sigungu": "광진구"},
        {"sido": "서울특별시", "sigungu": "중구"},
        {"sido": "서울특별시", "sigungu": "종로구"},
        {"sido": "서울특별시", "sigungu": "서대문구"},
        {"sido": "서울특별시", "sigungu": "은평구"},
        {"sido": "서울특별시", "sigungu": "노원구"},
        {"sido": "서울특별시", "sigungu": "도봉구"},
        {"sido": "서울특별시", "sigungu": "강북구"},
        {"sido": "서울특별시", "sigungu": "성북구"},
        {"sido": "서울특별시", "sigungu": "동대문구"},
        {"sido": "서울특별시", "sigungu": "중랑구"},
        # ── 경기도 28시 ──
        {"sido": "경기도", "sigungu": "성남시"},
        {"sido": "경기도", "sigungu": "수원시"},
        {"sido": "경기도", "sigungu": "용인시"},
        {"sido": "경기도", "sigungu": "화성시"},
        {"sido": "경기도", "sigungu": "고양시"},
        {"sido": "경기도", "sigungu": "부천시"},
        {"sido": "경기도", "sigungu": "광명시"},
        {"sido": "경기도", "sigungu": "하남시"},
        {"sido": "경기도", "sigungu": "과천시"},
        {"sido": "경기도", "sigungu": "안양시"},
        {"sido": "경기도", "sigungu": "의왕시"},
        {"sido": "경기도", "sigungu": "군포시"},
        {"sido": "경기도", "sigungu": "김포시"},
        {"sido": "경기도", "sigungu": "남양주시"},
        {"sido": "경기도", "sigungu": "안산시"},
        {"sido": "경기도", "sigungu": "시흥시"},
        {"sido": "경기도", "sigungu": "평택시"},
        {"sido": "경기도", "sigungu": "오산시"},
        {"sido": "경기도", "sigungu": "광주시"},
        {"sido": "경기도", "sigungu": "이천시"},
        {"sido": "경기도", "sigungu": "여주시"},
        {"sido": "경기도", "sigungu": "의정부시"},
        {"sido": "경기도", "sigungu": "양주시"},
        {"sido": "경기도", "sigungu": "파주시"},
        {"sido": "경기도", "sigungu": "구리시"},
        {"sido": "경기도", "sigungu": "동두천시"},
        {"sido": "경기도", "sigungu": "포천시"},
        {"sido": "경기도", "sigungu": "안성시"},
        # ── 인천광역시 8구 ──
        {"sido": "인천광역시", "sigungu": "연수구"},
        {"sido": "인천광역시", "sigungu": "남동구"},
        {"sido": "인천광역시", "sigungu": "부평구"},
        {"sido": "인천광역시", "sigungu": "계양구"},
        {"sido": "인천광역시", "sigungu": "서구"},
        {"sido": "인천광역시", "sigungu": "미추홀구"},
        {"sido": "인천광역시", "sigungu": "중구"},
        {"sido": "인천광역시", "sigungu": "동구"},
        # ── 부산광역시 16구군 ──
        {"sido": "부산광역시", "sigungu": "해운대구"},
        {"sido": "부산광역시", "sigungu": "수영구"},
        {"sido": "부산광역시", "sigungu": "남구"},
        {"sido": "부산광역시", "sigungu": "동래구"},
        {"sido": "부산광역시", "sigungu": "연제구"},
        {"sido": "부산광역시", "sigungu": "부산진구"},
        {"sido": "부산광역시", "sigungu": "북구"},
        {"sido": "부산광역시", "sigungu": "사상구"},
        {"sido": "부산광역시", "sigungu": "사하구"},
        {"sido": "부산광역시", "sigungu": "강서구"},
        {"sido": "부산광역시", "sigungu": "금정구"},
        {"sido": "부산광역시", "sigungu": "기장군"},
        {"sido": "부산광역시", "sigungu": "중구"},
        {"sido": "부산광역시", "sigungu": "서구"},
        {"sido": "부산광역시", "sigungu": "동구"},
        {"sido": "부산광역시", "sigungu": "영도구"},
        # ── 대구광역시 7구1군 ──
        {"sido": "대구광역시", "sigungu": "수성구"},
        {"sido": "대구광역시", "sigungu": "달서구"},
        {"sido": "대구광역시", "sigungu": "북구"},
        {"sido": "대구광역시", "sigungu": "동구"},
        {"sido": "대구광역시", "sigungu": "서구"},
        {"sido": "대구광역시", "sigungu": "남구"},
        {"sido": "대구광역시", "sigungu": "중구"},
        {"sido": "대구광역시", "sigungu": "달성군"},
        # ── 광주광역시 5구 ──
        {"sido": "광주광역시", "sigungu": "서구"},
        {"sido": "광주광역시", "sigungu": "북구"},
        {"sido": "광주광역시", "sigungu": "남구"},
        {"sido": "광주광역시", "sigungu": "동구"},
        {"sido": "광주광역시", "sigungu": "광산구"},
        # ── 대전광역시 5구 ──
        {"sido": "대전광역시", "sigungu": "서구"},
        {"sido": "대전광역시", "sigungu": "유성구"},
        {"sido": "대전광역시", "sigungu": "대덕구"},
        {"sido": "대전광역시", "sigungu": "동구"},
        {"sido": "대전광역시", "sigungu": "중구"},
        # ── 세종특별자치시 ──
        {"sido": "세종특별자치시", "sigungu": "세종시"},
        # ── 울산광역시 4구1군 ──
        {"sido": "울산광역시", "sigungu": "남구"},
        {"sido": "울산광역시", "sigungu": "북구"},
        {"sido": "울산광역시", "sigungu": "동구"},
        {"sido": "울산광역시", "sigungu": "중구"},
        {"sido": "울산광역시", "sigungu": "울주군"},
    ]

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
