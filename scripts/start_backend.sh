#!/bin/bash
# Find My Home 백엔드 시작 스크립트 (launchd용)

PROJ="/Users/suelee/Desktop/vibe_coding/find_my_home/backend"
VENV="$PROJ/venv"

# venv 활성화 후 uvicorn 실행
source "$VENV/bin/activate"
cd "$PROJ"
exec uvicorn main:app --host 0.0.0.0 --port 8000
