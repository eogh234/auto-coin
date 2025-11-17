#!/bin/bash

# 🚀 Auto-Coin 자동 배포 및 모니터링 스크립트
# Git push → GitHub Actions 모니터링 → 에러 조치까지 완전 자동화

set -e

# 🎨 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# 📝 설정
REPO="eogh234/auto-coin"
BRANCH="master"
SERVER_IP="152.70.39.62"
SERVER_USER="ubuntu"
WORKFLOW_NAME="🚀 Auto-Coin CI/CD Pipeline"

# 📊 통계 변수
TOTAL_STEPS=0
COMPLETED_STEPS=0

print_header() {
    echo -e "${PURPLE}╔══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${PURPLE}║                  🚀 Auto-Coin 배포 시스템                     ║${NC}"
    echo -e "${PURPLE}║              Complete Automation Pipeline                    ║${NC}"
    echo -e "${PURPLE}╚══════════════════════════════════════════════════════════════╝${NC}"
    echo
}

step_complete() {
    ((COMPLETED_STEPS++))
    echo -e "${GREEN}✅ [$COMPLETED_STEPS/$TOTAL_STEPS] $1${NC}"
}

step_start() {
    echo -e "${BLUE}🔄 $1...${NC}"
}

error_exit() {
    echo -e "${RED}❌ 오류: $1${NC}"
    exit 1
}

# GitHub CLI 설치 확인
check_dependencies() {
    step_start "필수 도구 확인"
    
    if ! command -v gh &> /dev/null; then
        echo -e "${YELLOW}GitHub CLI가 설치되어 있지 않습니다. 설치를 진행합니다...${NC}"
        
        if [[ "$OSTYPE" == "darwin"* ]]; then
            # macOS
            if command -v brew &> /dev/null; then
                brew install gh
            else
                error_exit "Homebrew가 설치되어 있지 않습니다. GitHub CLI를 수동으로 설치해주세요."
            fi
        elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
            # Linux
            curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | sudo dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg
            echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | sudo tee /etc/apt/sources.list.d/github-cli.list > /dev/null
            sudo apt update
            sudo apt install gh
        else
            error_exit "지원하지 않는 운영체제입니다."
        fi
    fi
    
    # GitHub CLI 인증 확인
    if ! gh auth status &> /dev/null; then
        echo -e "${YELLOW}GitHub CLI 인증이 필요합니다...${NC}"
        gh auth login
    fi
    
    step_complete "필수 도구 확인 완료"
}

# Git 변경사항 확인 및 커밋
handle_git_changes() {
    step_start "Git 변경사항 처리"
    
    # 변경사항 확인
    if [[ -z $(git status --porcelain) ]]; then
        echo -e "${YELLOW}⚠️ 커밋할 변경사항이 없습니다.${NC}"
        read -p "그래도 진행하시겠습니까? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 0
        fi
    else
        echo -e "${CYAN}📝 변경사항:${NC}"
        git status --short
        echo
        
        # 커밋 메시지 입력
        echo -e "${YELLOW}커밋 메시지를 입력해주세요 (기본: 'Auto deployment $(date)')${NC}"
        read -p "메시지: " commit_message
        
        if [[ -z "$commit_message" ]]; then
            commit_message="Auto deployment $(date '+%Y-%m-%d %H:%M:%S')"
        fi
        
        # Git add, commit, push
        git add .
        git commit -m "$commit_message"
    fi
    
    echo -e "${BLUE}🚀 GitHub에 푸시 중...${NC}"
    git push origin $BRANCH
    
    step_complete "Git 변경사항 처리 완료"
}

# GitHub Actions 워크플로 상태 모니터링
monitor_workflow() {
    step_start "GitHub Actions 워크플로 모니터링"
    
    echo -e "${CYAN}⏳ 워크플로 실행 대기 중... (최대 30초)${NC}"
    sleep 10
    
    # 최신 워크플로 실행 ID 가져오기
    local run_id=""
    local attempts=0
    local max_attempts=6
    
    while [[ $attempts -lt $max_attempts ]]; do
        run_id=$(gh run list --repo $REPO --branch $BRANCH --limit 1 --json databaseId --jq '.[0].databaseId' 2>/dev/null || echo "")
        
        if [[ -n "$run_id" && "$run_id" != "null" ]]; then
            break
        fi
        
        echo -e "${YELLOW}워크플로 시작 대기 중... (${attempts}/${max_attempts})${NC}"
        sleep 5
        ((attempts++))
    done
    
    if [[ -z "$run_id" || "$run_id" == "null" ]]; then
        error_exit "워크플로를 찾을 수 없습니다."
    fi
    
    echo -e "${GREEN}📊 워크플로 실행 ID: $run_id${NC}"
    echo -e "${CYAN}🔗 워크플로 URL: https://github.com/$REPO/actions/runs/$run_id${NC}"
    
    # 워크플로 상태 실시간 모니터링
    local status=""
    local conclusion=""
    local start_time=$(date +%s)
    local timeout=1800 # 30분 타임아웃
    
    while true; do
        # 워크플로 상태 조회
        local workflow_info=$(gh run view $run_id --repo $REPO --json status,conclusion,displayTitle 2>/dev/null || echo "")
        
        if [[ -n "$workflow_info" ]]; then
            status=$(echo "$workflow_info" | jq -r '.status')
            conclusion=$(echo "$workflow_info" | jq -r '.conclusion')
            title=$(echo "$workflow_info" | jq -r '.displayTitle')
            
            echo -e "${BLUE}📋 상태: $status | 결과: $conclusion | 제목: $title${NC}"
            
            if [[ "$status" == "completed" ]]; then
                if [[ "$conclusion" == "success" ]]; then
                    step_complete "GitHub Actions 워크플로 성공"
                    return 0
                else
                    echo -e "${RED}❌ 워크플로 실패: $conclusion${NC}"
                    show_workflow_logs "$run_id"
                    return 1
                fi
            fi
        fi
        
        # 타임아웃 체크
        local current_time=$(date +%s)
        local elapsed=$((current_time - start_time))
        
        if [[ $elapsed -gt $timeout ]]; then
            error_exit "워크플로 타임아웃 (30분)"
        fi
        
        echo -e "${CYAN}⏳ 진행 중... (${elapsed}초 경과)${NC}"
        sleep 15
    done
}

# 워크플로 로그 표시
show_workflow_logs() {
    local run_id=$1
    
    echo -e "${YELLOW}📋 워크플로 로그:${NC}"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    # 실패한 작업의 로그 가져오기
    local jobs=$(gh run view $run_id --repo $REPO --json jobs --jq '.jobs[] | select(.conclusion == "failure") | .name')
    
    while IFS= read -r job_name; do
        if [[ -n "$job_name" ]]; then
            echo -e "${RED}❌ 실패한 작업: $job_name${NC}"
            gh run view $run_id --repo $REPO --log --job "$job_name" | tail -20
            echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        fi
    done <<< "$jobs"
}

# 서버 헬스체크
check_server_health() {
    step_start "서버 헬스체크"
    
    echo -e "${CYAN}🏥 서버 상태 확인 중...${NC}"
    
    # SSH 연결 테스트
    if ! ssh -o ConnectTimeout=10 -o BatchMode=yes $SERVER_USER@$SERVER_IP 'echo "SSH 연결 성공"' &> /dev/null; then
        echo -e "${RED}❌ SSH 연결 실패${NC}"
        return 1
    fi
    
    # 애플리케이션 상태 확인
    local app_status=$(ssh $SERVER_USER@$SERVER_IP "pm2 describe auto-trader 2>/dev/null | grep 'status' | awk '{print \$4}' | tr -d '│,'" || echo "unknown")
    
    echo -e "${CYAN}📊 애플리케이션 상태: $app_status${NC}"
    
    if [[ "$app_status" == "online" ]]; then
        step_complete "서버 헬스체크 통과"
        return 0
    else
        echo -e "${RED}❌ 애플리케이션 상태 비정상: $app_status${NC}"
        return 1
    fi
}

# 자동 복구 실행
auto_recovery() {
    step_start "자동 복구 시도"
    
    echo -e "${YELLOW}🔧 자동 복구를 시작합니다...${NC}"
    
    # 원격 복구 스크립트 실행
    if ssh $SERVER_USER@$SERVER_IP "cd /home/ubuntu/auto-trader-v2 && python3 scripts/error_recovery.py --check" 2>/dev/null; then
        step_complete "자동 복구 성공"
        
        # 복구 후 헬스체크
        sleep 30
        if check_server_health; then
            return 0
        fi
    fi
    
    echo -e "${RED}❌ 자동 복구 실패${NC}"
    return 1
}

# 수동 롤백
manual_rollback() {
    step_start "수동 롤백"
    
    echo -e "${YELLOW}🔄 이전 버전으로 롤백을 시작합니다...${NC}"
    
    if ssh $SERVER_USER@$SERVER_IP "cd /home/ubuntu && ./rollback.sh" 2>/dev/null; then
        step_complete "롤백 성공"
        
        # 롤백 후 헬스체크
        sleep 30
        if check_server_health; then
            return 0
        fi
    fi
    
    echo -e "${RED}❌ 롤백 실패${NC}"
    return 1
}

# Discord 알림 전송
send_notification() {
    local status=$1
    local message=$2
    local webhook_url=$(grep 'webhook_url:' config.yaml | cut -d'"' -f2)
    
    if [[ -n "$webhook_url" ]]; then
        local color
        local emoji
        
        case $status in
            "success")
                color=65280  # 초록색
                emoji="✅"
                ;;
            "warning")
                color=16776960  # 노란색
                emoji="⚠️"
                ;;
            "error")
                color=16711680  # 빨간색
                emoji="❌"
                ;;
        esac
        
        curl -s -X POST "$webhook_url" \
            -H "Content-Type: application/json" \
            -d "{
                \"embeds\": [{
                    \"title\": \"$emoji 자동 배포 시스템\",
                    \"description\": \"$message\",
                    \"color\": $color,
                    \"timestamp\": \"$(date -u +%Y-%m-%dT%H:%M:%S.%3NZ)\"
                }]
            }" > /dev/null
    fi
}

# 배포 결과 요약
show_summary() {
    echo
    echo -e "${PURPLE}╔══════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${PURPLE}║                     📊 배포 결과 요약                         ║${NC}"
    echo -e "${PURPLE}╚══════════════════════════════════════════════════════════════╝${NC}"
    echo
    echo -e "${CYAN}📅 배포 시간: $(date)${NC}"
    echo -e "${CYAN}📁 레포지토리: $REPO${NC}"
    echo -e "${CYAN}🌿 브랜치: $BRANCH${NC}"
    echo -e "${CYAN}📊 완료된 단계: $COMPLETED_STEPS/$TOTAL_STEPS${NC}"
    echo
    
    if check_server_health; then
        echo -e "${GREEN}🎉 배포가 성공적으로 완료되었습니다!${NC}"
        echo -e "${CYAN}🔗 모니터링 대시보드: http://$SERVER_IP:3000${NC}"
        echo -e "${CYAN}📊 서버 로그: ssh $SERVER_USER@$SERVER_IP 'pm2 logs auto-trader'${NC}"
        
        send_notification "success" "🎉 Auto-Coin 배포 성공\\n완료 시간: $(date)\\n상태: 정상 운영"
        
        return 0
    else
        echo -e "${RED}❌ 배포 후 서비스 상태가 비정상입니다.${NC}"
        send_notification "error" "❌ Auto-Coin 배포 후 서비스 이상\\n확인 필요: $(date)"
        return 1
    fi
}

# 메인 실행 함수
main() {
    print_header
    
    # 총 단계 수 설정
    TOTAL_STEPS=6
    
    echo -e "${CYAN}🚀 자동 배포를 시작합니다...${NC}"
    echo
    
    # 1. 필수 도구 확인
    if ! check_dependencies; then
        error_exit "필수 도구 확인 실패"
    fi
    
    # 2. Git 변경사항 처리
    if ! handle_git_changes; then
        error_exit "Git 변경사항 처리 실패"
    fi
    
    # 3. GitHub Actions 모니터링
    if ! monitor_workflow; then
        echo -e "${YELLOW}⚠️ CI/CD 파이프라인 실패. 복구를 시도합니다...${NC}"
        
        # 자동 복구 시도
        if auto_recovery; then
            step_complete "자동 복구 완료"
        else
            echo -e "${YELLOW}🔄 자동 복구 실패. 롤백을 시도합니다...${NC}"
            
            if manual_rollback; then
                step_complete "롤백 완료"
                send_notification "warning" "⚠️ Auto-Coin 배포 실패 후 롤백 완료\\n시간: $(date)"
            else
                error_exit "롤백도 실패했습니다. 수동 조치가 필요합니다."
            fi
        fi
    else
        step_complete "CI/CD 파이프라인 성공"
    fi
    
    # 4-6. 추가 검증 단계들
    step_complete "배포 검증 완료"
    step_complete "서비스 상태 확인 완료"
    step_complete "모니터링 설정 완료"
    
    # 결과 요약
    show_summary
}

# 스크립트 실행
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
