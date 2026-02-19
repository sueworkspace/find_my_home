#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────
# Find My Home — 로컬 PostgreSQL → EC2 Docker DB 동기화
#
# 사용법:
#   bash scripts/sync_db_to_ec2.sh                       # 전체 DB 동기화
#   bash scripts/sync_db_to_ec2.sh --table complexes     # 특정 테이블만
# ──────────────────────────────────────────────────────────
set -euo pipefail

# ── 설정값 ──────────────────────────────────────────────
LOCAL_DB="find_my_home"
LOCAL_USER="suelee"
EC2_HOST="54.180.152.129"
EC2_USER="ubuntu"
EC2_KEY="$HOME/Downloads/find-my-home-key.pem"
EC2_TMP_DIR="/home/ubuntu/tmp"
DUMP_FILE="/tmp/find_my_home_$(date +%Y%m%d_%H%M%S).dump"

# ── --table 인수 파싱 ──────────────────────────────────
TABLE_OPT=""
if [[ "${1:-}" == "--table" && -n "${2:-}" ]]; then
  TABLE_OPT="-t ${2}"
  echo ">> 특정 테이블만 동기화: ${2}"
fi

# ── [1/4] pg_dump ──────────────────────────────────────
echo "[1/4] 로컬 DB 덤프 중... ($DUMP_FILE)"
# shellcheck disable=SC2086
pg_dump -U "$LOCAL_USER" -Fc $TABLE_OPT "$LOCAL_DB" -f "$DUMP_FILE"
echo "     덤프 완료 ($(du -h "$DUMP_FILE" | cut -f1))"

# ── [2/4] EC2로 전송 ──────────────────────────────────
echo "[2/4] EC2로 덤프 파일 전송 중..."
ssh -i "$EC2_KEY" -o StrictHostKeyChecking=no "$EC2_USER@$EC2_HOST" "mkdir -p $EC2_TMP_DIR"
scp -i "$EC2_KEY" -o StrictHostKeyChecking=no "$DUMP_FILE" "$EC2_USER@$EC2_HOST:$EC2_TMP_DIR/"
echo "     전송 완료"

# ── [3/4] EC2에서 pg_restore ──────────────────────────
DUMP_BASENAME=$(basename "$DUMP_FILE")
echo "[3/4] EC2 Docker 컨테이너에서 복원 중..."
ssh -i "$EC2_KEY" -o StrictHostKeyChecking=no "$EC2_USER@$EC2_HOST" bash -s <<REMOTE_SCRIPT
  set -euo pipefail

  # postgres 컨테이너 이름 찾기
  CONTAINER=\$(docker ps --format '{{.Names}}' | grep -E '(find_my_home_db|db)' | head -1)
  if [[ -z "\$CONTAINER" ]]; then
    echo "ERROR: postgres 컨테이너를 찾을 수 없습니다."
    exit 1
  fi
  echo "     컨테이너: \$CONTAINER"

  # 덤프 파일을 컨테이너 안으로 복사
  docker cp "$EC2_TMP_DIR/$DUMP_BASENAME" "\$CONTAINER:/tmp/$DUMP_BASENAME"

  # pg_restore 실행
  docker exec "\$CONTAINER" pg_restore -U suelee -d find_my_home --clean --if-exists "/tmp/$DUMP_BASENAME" || true

  # 컨테이너 내 임시파일 삭제
  docker exec "\$CONTAINER" rm -f "/tmp/$DUMP_BASENAME"
REMOTE_SCRIPT
echo "     복원 완료"

# ── [4/4] 임시파일 정리 ───────────────────────────────
echo "[4/4] 임시파일 정리 중..."
rm -f "$DUMP_FILE"
ssh -i "$EC2_KEY" -o StrictHostKeyChecking=no "$EC2_USER@$EC2_HOST" "rm -f $EC2_TMP_DIR/$DUMP_BASENAME"
echo "     정리 완료"

echo ""
echo "=== DB 동기화 완료 (로컬 → EC2) ==="
