#!/bin/bash
# =============================================================
# DuckDNS 무료 도메인 + Let's Encrypt HTTPS 설정
#
# 사전 조건:
#   1. https://www.duckdns.org 에서 계정 생성 (GitHub 로그인)
#   2. 서브도메인 등록 (예: findmyhome)
#   3. 토큰 복사
#
# 사용법 (EC2에서 실행):
#   bash deploy/setup-domain.sh <서브도메인> <토큰>
#   예: bash deploy/setup-domain.sh findmyhome abc123-your-token
#
# 결과: https://findmyhome.duckdns.org 로 접속 가능
# =============================================================
set -e

SUBDOMAIN="${1:?서브도메인을 입력하세요 (예: findmyhome)}"
TOKEN="${2:?DuckDNS 토큰을 입력하세요}"
DOMAIN="${SUBDOMAIN}.duckdns.org"

echo "===== DuckDNS 도메인 설정: ${DOMAIN} ====="

# 1) DuckDNS IP 등록
echo "[1/3] DuckDNS에 현재 IP 등록..."
RESULT=$(curl -s "https://www.duckdns.org/update?domains=${SUBDOMAIN}&token=${TOKEN}&ip=")
if [ "$RESULT" = "OK" ]; then
    echo "  DuckDNS 등록 성공!"
else
    echo "  DuckDNS 등록 실패: $RESULT"
    exit 1
fi

# 2) 자동 IP 갱신 cron 등록 (5분마다)
echo "[2/3] IP 자동 갱신 cron 등록..."
CRON_CMD="*/5 * * * * curl -s 'https://www.duckdns.org/update?domains=${SUBDOMAIN}&token=${TOKEN}&ip=' > /dev/null 2>&1"
(crontab -l 2>/dev/null | grep -v duckdns; echo "$CRON_CMD") | crontab -

# 3) Let's Encrypt HTTPS 설정 (certbot)
echo "[3/3] Let's Encrypt HTTPS 설정..."
sudo apt-get install -y certbot

# certbot standalone으로 인증서 발급 (nginx 잠시 중지)
cd ~/find_my_home
docker compose stop frontend 2>/dev/null || true

sudo certbot certonly --standalone \
    -d "${DOMAIN}" \
    --non-interactive \
    --agree-tos \
    --email "noreply@${DOMAIN}" \
    --preferred-challenges http

# certbot 자동 갱신 타이머 확인
sudo systemctl enable certbot.timer 2>/dev/null || true

echo ""
echo "============================================"
echo "  도메인 설정 완료!"
echo ""
echo "  도메인: https://${DOMAIN}"
echo "  인증서: /etc/letsencrypt/live/${DOMAIN}/"
echo ""
echo "  다음 단계:"
echo "  nginx.conf에 SSL 설정을 추가하고"
echo "  docker compose up -d --build 실행"
echo "============================================"
