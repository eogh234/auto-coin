#!/bin/bash

# 🚀 Auto-Coin 수동 배포 스크립트
# GitHub Actions를 사용할 수 없을 때의 백업 배포 방법

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
REMOTE_DIR="/home/ubuntu/auto-trader-v2"

echo -e "${BLUE}🚀 Auto-Coin 배포 시작...${NC}"

# 🧪 로컬 테스트 실행
echo -e "${YELLOW}🧪 로컬 테스트 실행 중...${NC}"
if command -v python3 &> /dev/null; then
    echo "✅ Python3 환경 확인 완료"
    
    # 코드 스타일 검사 (선택사항)
    if command -v flake8 &> /dev/null; then
        echo "🎨 코드 스타일 검사 중..."
        flake8 modules/ main.py --max-line-length=100 --extend-ignore=E203,W503 || true
    fi
    
    # 간단한 구문 검사
    echo "🔍 Python 구문 검사 중..."
    python3 -m py_compile main.py
    python3 -m py_compile modules/*.py
    
    echo "✅ 로컬 테스트 완료"
else
    echo -e "${RED}❌ Python3을 찾을 수 없습니다${NC}"
    exit 1
fi

# 🔗 서버 연결 확인
echo -e "${YELLOW}🔗 서버 연결 확인 중...${NC}"
if ssh -o ConnectTimeout=10 -o BatchMode=yes $SERVER_USER@$SERVER_IP 'echo "연결 성공"' &> /dev/null; then
    echo "✅ 서버 연결 확인 완료"
else
    echo -e "${RED}❌ 서버에 연결할 수 없습니다. SSH 설정을 확인해주세요${NC}"
    exit 1
fi

# 📦 코드 압축
echo -e "${YELLOW}📦 코드 압축 중...${NC}"
tar -czf auto-coin-deploy.tar.gz \
    --exclude='.git' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='.DS_Store' \
    --exclude='legacy/' \
    --exclude='auto-coin-deploy.tar.gz' \
    .

echo "✅ 코드 압축 완료"

# 🚀 서버 배포
echo -e "${YELLOW}🚀 서버 배포 중...${NC}"
ssh $SERVER_USER@$SERVER_IP << 'EOF'
set -e

echo "🛑 현재 애플리케이션 중지 중..."
pm2 stop auto-trader || echo "⚠️ PM2 프로세스가 실행 중이 아님"

echo "💾 현재 버전 백업 중..."
cd /home/ubuntu
if [ -d "auto-trader-v2-backup" ]; then
    rm -rf auto-trader-v2-backup
fi
if [ -d "auto-trader-v2" ]; then
    mv auto-trader-v2 auto-trader-v2-backup
    echo "✅ 백업 완료"
fi

echo "📁 새 디렉토리 생성..."
mkdir -p auto-trader-v2
EOF

# 📤 파일 업로드
echo -e "${YELLOW}📤 파일 업로드 중...${NC}"
scp auto-coin-deploy.tar.gz $SERVER_USER@$SERVER_IP:/home/ubuntu/auto-coin-deploy.tar.gz

# 🔧 서버에서 설정
ssh $SERVER_USER@$SERVER_IP << 'EOF'
set -e

echo "📦 파일 압축 해제 중..."
cd /home/ubuntu
tar -xzf auto-coin-deploy.tar.gz -C auto-trader-v2
rm auto-coin-deploy.tar.gz

echo "🔧 환경 설정 중..."
cd auto-trader-v2

# 기존 설정 파일 복사
if [ -f "/home/ubuntu/auto-trader-v2-backup/config.yaml" ]; then
    cp /home/ubuntu/auto-trader-v2-backup/config.yaml ./
    echo "✅ 기존 설정 파일 복사 완료"
fi

# 기존 거래 데이터 복사
if [ -f "/home/ubuntu/auto-trader-v2-backup/trading_data.json" ]; then
    cp /home/ubuntu/auto-trader-v2-backup/trading_data.json ./
    echo "✅ 기존 거래 데이터 복사 완료"
fi

# 기존 학습 데이터 복사
if [ -f "/home/ubuntu/auto-trader-v2-backup/trade_history.db" ]; then
    cp /home/ubuntu/auto-trader-v2-backup/trade_history.db ./
    echo "✅ 기존 학습 데이터 복사 완료"
fi

echo "📦 종속성 설치 중..."
pip3 install -r requirements.txt --user

echo "🚀 애플리케이션 시작 중..."
pm2 start main.py --name auto-trader --interpreter python3
pm2 save

echo "✅ 배포 완료!"
EOF

# 🏥 헬스체크
echo -e "${YELLOW}🏥 헬스체크 수행 중...${NC}"
sleep 10

ssh $SERVER_USER@$SERVER_IP << 'EOF'
if pm2 describe auto-trader | grep -q "online"; then
    echo "✅ 애플리케이션이 성공적으로 실행 중입니다"
    echo "📊 현재 상태:"
    pm2 status auto-trader
    echo "📝 최근 로그:"
    pm2 logs auto-trader --lines 5
else
    echo "❌ 애플리케이션 시작에 실패했습니다"
    echo "📝 에러 로그:"
    pm2 logs auto-trader --lines 10
    exit 1
fi
EOF

# 🧹 정리
echo -e "${YELLOW}🧹 임시 파일 정리 중...${NC}"
rm -f auto-coin-deploy.tar.gz

echo -e "${GREEN}🎉 배포가 성공적으로 완료되었습니다!${NC}"
echo -e "${BLUE}📊 모니터링: ssh $SERVER_USER@$SERVER_IP 'pm2 monit'${NC}"
echo -e "${BLUE}📝 로그 확인: ssh $SERVER_USER@$SERVER_IP 'pm2 logs auto-trader'${NC}"
