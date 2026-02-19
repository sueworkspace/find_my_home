#!/bin/bash
# Sprint 9 마무리 자동화 스크립트
#
# 실거래가 배치 수집 완료 후 자동 실행:
#   1) KB시세 전체 수집
#   2) 비교 엔진 업데이트 (ComplexComparison 갱신)
#   3) EC2 배포 (git pull + docker restart)
#
# 사용법:
#   cd backend && bash scripts/finish_sprint9.sh BATCH_PID
#   예: bash scripts/finish_sprint9.sh 17152

BATCH_PID=${1:-17152}
LOG_FILE="/tmp/finish_sprint9.log"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="$(dirname "$SCRIPT_DIR")"
EC2_HOST="ubuntu@54.180.152.129"
EC2_KEY="$HOME/Downloads/find-my-home-key.pem"

log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

log "=== Sprint 9 마무리 스크립트 시작 ==="
log "실거래가 배치 PID: $BATCH_PID"

# ────────────────────────────────────
# 1) 실거래가 배치 완료 대기
# ────────────────────────────────────
log "실거래가 배치 완료 대기 중..."
while kill -0 "$BATCH_PID" 2>/dev/null; do
  PROGRESS=$(python3 -c "
import json
try:
    with open('$SCRIPT_DIR/collect_progress.json') as f:
        d = json.load(f)
    done = len(d.get('done', []))
    print(f'{done}/1414 ({done/1414*100:.1f}%)')
except:
    print('읽기 실패')
" 2>/dev/null)
  log "진행 중: $PROGRESS"
  sleep 60  # 1분마다 체크
done
log "실거래가 배치 수집 완료!"

# ────────────────────────────────────
# 2) KB시세 전체 수집
# ────────────────────────────────────
log "KB시세 수집 시작..."
cd "$BACKEND_DIR" || exit 1
source venv/bin/activate 2>/dev/null || true
python scripts/collect_kb_prices.py >> "$LOG_FILE" 2>&1
if [ $? -ne 0 ]; then
  log "KB시세 수집 에러 발생 (로그 확인: $LOG_FILE)"
else
  log "KB시세 수집 완료"
fi

# ────────────────────────────────────
# 3) 비교 엔진 업데이트 (API 호출)
# ────────────────────────────────────
log "비교 엔진 업데이트 시작..."
COMPARE_RESULT=$(curl -s -X POST "http://localhost:8000/api/complexes/compare" 2>&1)
log "비교 엔진 결과: $COMPARE_RESULT"

# ────────────────────────────────────
# 4) EC2 배포
# ────────────────────────────────────
log "EC2 배포 시작..."
ssh -i "$EC2_KEY" -o StrictHostKeyChecking=no "$EC2_HOST" "
  set -e
  cd ~/find_my_home
  echo '--- git pull ---'
  git pull origin main
  echo '--- docker compose restart ---'
  sudo docker compose up -d --build
  echo '--- 컨테이너 상태 ---'
  sudo docker compose ps
" 2>&1 | tee -a "$LOG_FILE"

if [ $? -eq 0 ]; then
  log "EC2 배포 완료!"
else
  log "EC2 배포 실패. 로그를 확인하세요: $LOG_FILE"
fi

log "=== Sprint 9 마무리 완료 ==="
