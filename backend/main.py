"""Find My Home - FastAPI 앱 진입점"""

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.regions import router as regions_router
from app.api.listings import router as listings_router
from app.api.transactions import router as transactions_router

app = FastAPI(
    title="Find My Home API",
    description="KB시세 대비 급매물 탐지 서비스 API",
    version="0.1.0",
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
app.include_router(listings_router)
app.include_router(transactions_router)


@app.get("/", tags=["health"])
def health_check():
    """헬스체크 엔드포인트"""
    return {"status": "ok", "service": "find_my_home"}


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
