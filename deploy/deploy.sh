#!/bin/bash
# =============================================================
# EC2 배포 스크립트 (로컬 Mac에서 실행)
#
# 사용법:
#   bash deploy/deploy.sh <EC2_IP> <SSH_KEY_PATH>
#
# 예시:
#   bash deploy/deploy.sh 3.35.123.45 ~/.ssh/find-my-home.pem
# =============================================================
set -e

EC2_IP="${1:?EC2 IP 주소를 입력하세요 (예: bash deploy.sh 3.35.123.45 ~/.ssh/key.pem)}"
SSH_KEY="${2:?SSH 키 경로를 입력하세요}"
EC2_USER="ubuntu"
REMOTE_DIR="find_my_home"

echo "===== EC2 배포 시작: ${EC2_USER}@${EC2_IP} ====="

# 1) 최신 코드 push (로컬 → GitHub)
echo "[1/4] GitHub에 최신 코드 push..."
git push origin main 2>/dev/null || echo "push 실패 또는 이미 최신"

# 2) EC2에서 최신 코드 pull
echo "[2/4] EC2에서 코드 pull..."
ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no "${EC2_USER}@${EC2_IP}" \
    "cd ~/${REMOTE_DIR} && git pull origin main"

# 3) .env 파일 동기화 (로컬 → EC2)
echo "[3/4] .env 파일 동기화..."
scp -i "$SSH_KEY" -o StrictHostKeyChecking=no \
    backend/.env "${EC2_USER}@${EC2_IP}:~/${REMOTE_DIR}/backend/.env"

# 4) Docker Compose 재빌드 및 실행
echo "[4/4] Docker Compose 재빌드..."
ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no "${EC2_USER}@${EC2_IP}" \
    "cd ~/${REMOTE_DIR} && docker compose up -d --build"

echo ""
echo "============================================"
echo "  배포 완료!"
echo "  http://${EC2_IP} 에서 접속 가능"
echo "============================================"
