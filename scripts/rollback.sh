#!/bin/bash

# 🔄 Auto-Coin 롤백 스크립트
# 배포 실패 시 이전 버전으로 복구

set -e

# 🎨 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 📝 설정
SERVER_IP="152.70.39.62"
SERVER_USER="ubuntu"
APP_NAME="auto-trader"

echo -e "${BLUE}🔄 Auto-Coin 롤백 시작...${NC}"

# 🔗 서버 연결 확인
echo -e "${YELLOW}🔗 서버 연결 확인 중...${NC}"
if ssh -o ConnectTimeout=10 -o BatchMode=yes $SERVER_USER@$SERVER_IP 'echo "연결 성공"' &> /dev/null; then
    echo "✅ 서버 연결 확인 완료"
else
    echo -e "${RED}❌ 서버에 연결할 수 없습니다${NC}"
    exit 1
fi

# 🔄 롤백 실행
echo -e "${YELLOW}🔄 이전 버전으로 롤백 중...${NC}"
ssh $SERVER_USER@$SERVER_IP << 'EOF'
set -e

echo "🛑 현재 애플리케이션 중지 중..."
pm2 stop auto-trader || echo "⚠️ PM2 프로세스가 실행 중이 아님"

echo "🔍 백업 버전 확인 중..."
cd /home/ubuntu
if [ -d "auto-trader-v2-backup" ]; then
    echo "✅ 백업 버전 발견"
    
    echo "🗑️ 현재 버전 제거 중..."
    if [ -d "auto-trader-v2" ]; then
        rm -rf auto-trader-v2
    fi
    
    echo "🔄 백업 버전 복원 중..."
    mv auto-trader-v2-backup auto-trader-v2
    
    echo "🚀 이전 버전 시작 중..."
    cd auto-trader-v2
    pm2 start main.py --name auto-trader --interpreter python3
    pm2 save
    
    echo "✅ 롤백 완료!"
else
    echo "❌ 백업 버전을 찾을 수 없습니다"
    exit 1
fi
EOF

# 🏥 헬스체크
echo -e "${YELLOW}🏥 롤백 후 상태 확인 중...${NC}"
sleep 10

ssh $SERVER_USER@$SERVER_IP << 'EOF'
if pm2 describe auto-trader | grep -q "online"; then
    echo "✅ 롤백된 애플리케이션이 성공적으로 실행 중입니다"
    echo "📊 현재 상태:"
    pm2 status auto-trader
    echo "📝 최근 로그:"
    pm2 logs auto-trader --lines 5
else
    echo "❌ 롤백 후에도 애플리케이션 시작에 실패했습니다"
    echo "📝 에러 로그:"
    pm2 logs auto-trader --lines 10
    exit 1
fi
EOF

echo -e "${GREEN}🎉 롤백이 성공적으로 완료되었습니다!${NC}"
echo -e "${BLUE}📊 모니터링: ssh $SERVER_USER@$SERVER_IP 'pm2 monit'${NC}"
