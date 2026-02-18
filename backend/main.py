"""Find My Home - FastAPI 앱 진입점"""

import logging

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.regions import router as regions_router
from app.api.transactions import router as transactions_router
from app.api.complexes import router as complexes_router
from app.api.dashboard import router as dashboard_router
from app.models.database import engine, Base
from app.models.apartment import ApartmentComplex, KBPrice, RealTransaction, ComplexComparison  # noqa: F401
from app.crawler.scheduler import start_scheduler, stop_scheduler

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

app = FastAPI(
    title="Find My Home API",
    description="KB시세 대비 급매물 탐지 서비스 API",
    version="0.2.0",
)

# -----------------------------------------------------------
# CORS 설정 - React dev server (localhost:3000) 허용
# -----------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------------------------------------
# 라우터 등록
# -----------------------------------------------------------
app.include_router(regions_router)
app.include_router(transactions_router)
app.include_router(complexes_router)
app.include_router(dashboard_router)


# -----------------------------------------------------------
# 스케줄러 연동 (서버 시작/종료 시)
# -----------------------------------------------------------
@app.on_event("startup")
async def on_startup():
    """서버 시작 시 DB 테이블 생성 후 스케줄러를 등록합니다."""
    Base.metadata.create_all(bind=engine)
    start_scheduler()


@app.on_event("shutdown")
async def on_shutdown():
    """서버 종료 시 스케줄러를 정리합니다."""
    stop_scheduler()


@app.get("/", tags=["health"])
def health_check():
    """헬스체크 엔드포인트"""
    return {"status": "ok", "service": "find_my_home", "version": "0.2.0"}


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
