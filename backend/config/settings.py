from typing import Dict, List

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql://suelee@localhost:5432/find_my_home"
    CRAWLER_DELAY_SECONDS: float = 1.5
    CRAWLER_INTERVAL_MINUTES: int = 60       # (하위호환용, 전체 파이프라인)
    CRAWLER_MAX_RETRIES: int = 3

    # 증분 크롤링 설정
    NAVER_CRAWL_INTERVAL_MINUTES: int = 150  # 네이버 증분 크롤링 간격 (2.5시간)
    KB_PRICE_CRON_HOUR: int = 6              # KB시세 수집 시각 (매일)
    KB_PRICE_CRON_MINUTE: int = 0
    MIN_HOUSEHOLD_COUNT: int = 200           # 최소 세대수 필터

    # 공공데이터포털 API 인증키 (data.go.kr)
    DATA_GO_KR_API_KEY: str = ""

    # 배치 크롤링 설정
    BATCH_COOLDOWN_SECONDS: int = 600      # API 호출 한도 도달 시 쿨다운 (10분)
    BATCH_API_CALL_LIMIT: int = 180        # 쿨다운 트리거 API 호출 수

    # 크롤링 대상 지역 목록 — 서울 25구 + 경기 28시 + 인천 8구 = 61개
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
    ]

    class Config:
        env_file = ".env"
        extra = "ignore"  # .env의 WP_* 등 미정의 변수 무시


settings = Settings()
