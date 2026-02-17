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

    # 크롤링 대상 지역 목록 (시/도 + 시/군/구)
    # .env에서는 JSON 문자열로 설정 가능
    TARGET_REGIONS: List[Dict[str, str]] = [
        {"sido": "서울특별시", "sigungu": "강남구"},
        {"sido": "서울특별시", "sigungu": "서초구"},
        {"sido": "서울특별시", "sigungu": "송파구"},
    ]

    class Config:
        env_file = ".env"


settings = Settings()
