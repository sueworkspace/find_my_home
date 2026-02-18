#!/bin/bash
# =============================================================
# EC2 초기 세팅 스크립트 (Ubuntu 22.04/24.04)
#
# 사용법: SSH 접속 후 실행
#   curl -fsSL https://raw.githubusercontent.com/sueworkspace/find_my_home/main/deploy/ec2-setup.sh | bash
#   또는 직접: bash ec2-setup.sh
# =============================================================
set -e

echo "===== [1/4] 시스템 패키지 업데이트 ====="
sudo apt-get update -y
sudo apt-get upgrade -y

echo "===== [2/4] Docker 설치 ====="
# Docker 공식 GPG 키 추가
sudo apt-get install -y ca-certificates curl gnupg
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

# Docker 저장소 추가
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt-get update -y
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# sudo 없이 docker 실행 가능하게
sudo usermod -aG docker $USER

echo "===== [3/4] Git 설치 및 레포 클론 ====="
sudo apt-get install -y git

if [ ! -d "$HOME/find_my_home" ]; then
    git clone https://github.com/sueworkspace/find_my_home.git "$HOME/find_my_home"
else
    echo "레포가 이미 존재합니다. pull합니다."
    cd "$HOME/find_my_home" && git pull
fi

echo "===== [4/4] 방화벽 설정 ====="
# UFW가 설치되어 있으면 포트 열기
if command -v ufw &> /dev/null; then
    sudo ufw allow 22/tcp    # SSH
    sudo ufw allow 80/tcp    # HTTP
    sudo ufw allow 443/tcp   # HTTPS (추후)
    sudo ufw --force enable
fi

echo ""
echo "============================================"
echo "  EC2 초기 세팅 완료!"
echo ""
echo "  다음 단계:"
echo "  1. 로그아웃 후 재접속 (docker 그룹 적용)"
echo "  2. cd ~/find_my_home"
echo "  3. backend/.env 파일에 API 키 설정"
echo "  4. docker compose up -d --build"
echo "============================================"
