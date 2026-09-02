#!/bin/bash
# ============================================================
# Antigravity Investment System - Scheduler Setup Script
# ============================================================
# 이 스크립트는 다음을 설정합니다:
#   1. crontab: orchestrator.py (09:05 KST), execute_us.py (23:20 KST)
#   2. crypto_monitor.py: 백그라운드 데몬 재시작
# ============================================================

set -e

INVEST_DIR="/Users/Daeho/Projects/auto-coin"
PYTHON="$INVEST_DIR/venv/bin/python"
LOG_DIR="$INVEST_DIR"

echo "============================================================"
echo " 🚀 Antigravity 투자 시스템 스케줄러 설정 시작"
echo "============================================================"

# ----------------------------------------------------------
# 1. crypto_monitor.py 기존 프로세스 종료 후 재시작
# ----------------------------------------------------------
echo ""
echo "[1/3] 🔄 crypto_monitor.py 데몬 재시작..."

# 기존 프로세스 종료
EXISTING=$(pgrep -f "crypto_monitor.py" 2>/dev/null || true)
if [ -n "$EXISTING" ]; then
    echo "   기존 프로세스 (PID: $EXISTING) 종료 중..."
    kill $EXISTING 2>/dev/null || true
    sleep 2
fi

# 백그라운드 재시작
nohup "$PYTHON" "$INVEST_DIR/crypto_monitor.py" \
    >> "$LOG_DIR/crypto_monitor.log" 2>&1 &

CRYPTO_PID=$!
echo "   ✅ crypto_monitor.py 시작됨 (PID: $CRYPTO_PID)"

# ----------------------------------------------------------
# 2. crontab 등록
# ----------------------------------------------------------
echo ""
echo "[2/3] ⏰ crontab 스케줄 등록..."

# 기존 crontab에서 관련 항목 제거 후 새로 추가
CRON_CLEAN=$(crontab -l 2>/dev/null | grep -v "auto-coin" | grep -v "Antigravity" | grep -v "orchestrator" | grep -v "execute_us" || true)

NEW_CRON="$CRON_CLEAN
# ---- Antigravity Investment System ----
# 한국 시장 오전 실행: 매일 09:05 KST (국내주식/코인 체결)
5 9 * * 1-5 cd $INVEST_DIR && $PYTHON $INVEST_DIR/orchestrator.py >> $LOG_DIR/execution_log.txt 2>&1
# 미국 시장 야간 회의: 매일 23:15 KST (낮 입출금 반영 & 야간 포트폴리오 갱신)
15 23 * * 1-5 cd $INVEST_DIR && $PYTHON $INVEST_DIR/orchestrator.py >> $LOG_DIR/execution_log.txt 2>&1
# 미국 시장 야간 실행: 매일 23:20 KST (미국주식 체결)
20 23 * * 1-5 cd $INVEST_DIR && $PYTHON $INVEST_DIR/execute_us.py >> $LOG_DIR/execution_log.txt 2>&1"

echo "$NEW_CRON" | crontab -

echo "   ✅ crontab 등록 완료:"
crontab -l | grep -A5 "Antigravity"

# ----------------------------------------------------------
# 3. 현재 상태 확인
# ----------------------------------------------------------
echo ""
echo "[3/3] 📋 시스템 상태 최종 확인..."
echo ""
echo "   실행 중인 프로세스:"
ps aux | grep -E "crypto_monitor|orchestrat" | grep -v grep | awk '{print "   PID:"$2, $11, $12}' || echo "   (없음)"

echo ""
echo "============================================================"
echo " ✅ 스케줄러 설정 완료!"
echo "============================================================"
echo ""
echo " 📅 실행 스케줄 (평일 기준):"
echo "   ⏰ 09:05 KST — orchestrator.py (아침 회의 + 한국 주식/코인 체결)"
echo "   🌙 23:15 KST — orchestrator.py (야간 회의 + 낮 입출금 반영/포트폴리오 갱신)"
echo "   🚀 23:20 KST — execute_us.py  (미국 주식 체결)"
echo "   👀 상시    — crypto_monitor.py (가격 변동성 감시)"
echo ""
echo " 📂 로그 위치: $LOG_DIR/execution_log.txt"
echo "             $LOG_DIR/crypto_monitor.log"
echo ""
