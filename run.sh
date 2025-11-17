#!/bin/bash
"""
🚀 Auto-Trader 통합 실행 스크립트
모든 기능을 하나의 스크립트로 통합 관리
"""

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 로고 출력
print_logo() {
    echo -e "${BLUE}"
    echo "  ╔═══════════════════════════════════════════════╗"
    echo "  ║            🚀 AUTO-TRADER v2.0               ║"
    echo "  ║        통합 암호화폐 자동매매 시스템            ║"
    echo "  ╚═══════════════════════════════════════════════╝"
    echo -e "${NC}"
}

# 도움말 출력
show_help() {
    echo -e "${YELLOW}사용법:${NC}"
    echo "  ./run.sh [옵션]"
    echo ""
    echo -e "${YELLOW}옵션:${NC}"
    echo "  live       - 실거래 모드 실행"
    echo "  test       - 테스트 모드 실행"
    echo "  backtest   - 백테스팅 실행"
    echo "  analyze    - 성과 분석"
    echo "  setup      - 초기 설정"
    echo "  deploy     - 서버 배포"
    echo "  status     - 서버 상태 확인"
    echo "  logs       - 로그 확인"
    echo "  stop       - 서버 중지"
    echo "  help       - 이 도움말 출력"
    echo ""
    echo -e "${YELLOW}예시:${NC}"
    echo "  ./run.sh live          # 실거래 모드로 실행"
    echo "  ./run.sh test          # 테스트 모드로 실행"
    echo "  ./run.sh backtest      # 비트코인 30일 백테스팅"
    echo "  ./run.sh analyze       # 최근 7일 성과 분석"
}

# 의존성 확인
check_dependencies() {
    echo -e "${BLUE}의존성 확인 중...${NC}"
    
    # Python 버전 확인
    if ! python3 --version &> /dev/null; then
        echo -e "${RED}❌ Python3가 설치되지 않았습니다.${NC}"
        exit 1
    fi
    
    # 필수 패키지 확인 및 설치
    if [ ! -f "requirements.txt" ]; then
        echo "pyupbit>=0.2.0" > requirements.txt
        echo "pyyaml>=6.0" >> requirements.txt
        echo "requests>=2.25.0" >> requirements.txt
        echo "psutil>=5.8.0" >> requirements.txt
        echo "pandas>=1.3.0" >> requirements.txt
    fi
    
    pip install -r requirements.txt -q
    
    echo -e "${GREEN}✅ 의존성 확인 완료${NC}"
}

# 설정 파일 생성
setup_config() {
    echo -e "${BLUE}초기 설정을 시작합니다...${NC}"
    
    if [ -f "config.yaml" ]; then
        echo -e "${YELLOW}기존 설정 파일이 있습니다. 덮어쓰시겠습니까? (y/N)${NC}"
        read -r response
        if [[ ! "$response" =~ ^[Yy]$ ]]; then
            echo "설정을 취소합니다."
            return
        fi
    fi
    
    echo -e "${YELLOW}Upbit API 설정:${NC}"
    echo -n "Access Key: "
    read -r access_key
    echo -n "Secret Key: "
    read -rs secret_key
    echo ""
    
    echo -e "${YELLOW}Discord 웹훅 URL (선택사항):${NC}"
    echo -n "Webhook URL: "
    read -r webhook_url
    
    # config.yaml 생성
    cat > config.yaml << EOF
upbit:
  access_key: "$access_key"
  secret_key: "$secret_key"

discord:
  webhook_url: "$webhook_url"
  notification_cooldown: 300
  status_report_interval: 1800
  daily_report_time: "09:00"

trading:
  max_daily_trades: 50
  max_hourly_trades: 5
  daily_loss_limit: 0.05
  investment_ratio: 0.1
  min_krw_balance: 50000

learning:
  learning_interval_hours: 1
  memory_threshold: 0.85
  archive_days: 30
  min_trades_for_learning: 10
EOF
    
    echo -e "${GREEN}✅ 설정 파일이 생성되었습니다.${NC}"
}

# 로컬 실행
run_local() {
    local mode=$1
    echo -e "${BLUE}로컬에서 ${mode} 모드로 실행 중...${NC}"
    
    case $mode in
        "live")
            python3 main.py
            ;;
        "test")
            python3 main.py --test
            ;;
        "backtest")
            python3 main.py --backtest --ticker KRW-BTC --days 30
            ;;
        "analyze")
            python3 main.py --analyze --days 7
            ;;
    esac
}

# 서버 배포
deploy_server() {
    echo -e "${BLUE}서버 배포를 시작합니다...${NC}"
    
    # 서버 정보 입력
    echo -n "서버 IP: "
    read -r server_ip
    echo -n "사용자명 (기본: ubuntu): "
    read -r username
    username=${username:-ubuntu}
    
    echo -e "${YELLOW}서버에 파일을 업로드하는 중...${NC}"
    
    # 원격 디렉토리 생성
    ssh "${username}@${server_ip}" "mkdir -p /home/${username}/auto-trader"
    
    # 핵심 파일들 업로드
    scp main.py "${username}@${server_ip}:/home/${username}/auto-trader/"
    scp -r modules "${username}@${server_ip}:/home/${username}/auto-trader/"
    scp config.yaml "${username}@${server_ip}:/home/${username}/auto-trader/"
    scp requirements.txt "${username}@${server_ip}:/home/${username}/auto-trader/"
    
    # 서버에서 실행 준비
    ssh "${username}@${server_ip}" << 'EOF'
cd /home/ubuntu/auto-trader
pip3 install -r requirements.txt
pip3 install pm2

# PM2 ecosystem 파일 생성
cat > ecosystem.config.js << 'ECOSYSTEM'
module.exports = {
  apps: [{
    name: 'auto-trader-live',
    script: 'python3',
    args: 'main.py',
    interpreter: 'none',
    env: {
      NODE_ENV: 'production'
    },
    log_file: './logs/combined.log',
    out_file: './logs/out.log',
    error_file: './logs/error.log',
    restart_delay: 3000,
    max_restarts: 10
  }, {
    name: 'auto-trader-test',
    script: 'python3',
    args: 'main.py --test',
    interpreter: 'none',
    env: {
      NODE_ENV: 'development'
    },
    log_file: './logs/test-combined.log',
    out_file: './logs/test-out.log',
    error_file: './logs/test-error.log'
  }]
};
ECOSYSTEM

mkdir -p logs
EOF
    
    echo -e "${GREEN}✅ 서버 배포 완료${NC}"
    echo -e "${YELLOW}서버에서 실행하려면:${NC}"
    echo "  ssh ${username}@${server_ip}"
    echo "  cd /home/${username}/auto-trader"
    echo "  pm2 start ecosystem.config.js --only auto-trader-live"
}

# 서버 상태 확인
check_server_status() {
    echo -n "서버 IP: "
    read -r server_ip
    echo -n "사용자명 (기본: ubuntu): "
    read -r username
    username=${username:-ubuntu}
    
    echo -e "${BLUE}서버 상태 확인 중...${NC}"
    
    ssh "${username}@${server_ip}" << 'EOF'
echo "=== PM2 프로세스 상태 ==="
pm2 list

echo -e "\n=== 시스템 리소스 ==="
free -h
df -h | head -5

echo -e "\n=== 최근 로그 (마지막 10줄) ==="
cd /home/ubuntu/auto-trader
if [ -f "logs/out.log" ]; then
    tail -10 logs/out.log
else
    echo "로그 파일을 찾을 수 없습니다."
fi
EOF
}

# 로그 확인
check_logs() {
    echo -n "서버 IP: "
    read -r server_ip
    echo -n "사용자명 (기본: ubuntu): "
    read -r username
    username=${username:-ubuntu}
    
    echo -e "${BLUE}실시간 로그를 확인합니다... (Ctrl+C로 종료)${NC}"
    
    ssh "${username}@${server_ip}" "cd /home/${username}/auto-trader && tail -f logs/out.log"
}

# 서버 중지
stop_server() {
    echo -n "서버 IP: "
    read -r server_ip
    echo -n "사용자명 (기본: ubuntu): "
    read -r username
    username=${username:-ubuntu}
    
    echo -e "${YELLOW}서버를 중지합니다...${NC}"
    
    ssh "${username}@${server_ip}" "pm2 stop all && pm2 delete all"
    
    echo -e "${GREEN}✅ 서버가 중지되었습니다.${NC}"
}

# 메인 실행 로직
main() {
    print_logo
    
    if [ $# -eq 0 ]; then
        show_help
        exit 0
    fi
    
    case $1 in
        "live")
            check_dependencies
            run_local "live"
            ;;
        "test")
            check_dependencies
            run_local "test"
            ;;
        "backtest")
            check_dependencies
            run_local "backtest"
            ;;
        "analyze")
            check_dependencies
            run_local "analyze"
            ;;
        "setup")
            setup_config
            ;;
        "deploy")
            check_dependencies
            deploy_server
            ;;
        "status")
            check_server_status
            ;;
        "logs")
            check_logs
            ;;
        "stop")
            stop_server
            ;;
        "help"|"--help"|"-h")
            show_help
            ;;
        *)
            echo -e "${RED}알 수 없는 명령어: $1${NC}"
            show_help
            exit 1
            ;;
    esac
}

# 스크립트 실행
main "$@"
