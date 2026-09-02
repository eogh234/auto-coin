"""
execute_us.py — 미국 주식 야간 실행 스크립트
매일 오후 11:20 KST에 크론탭으로 실행됩니다.
아침 main.py가 저장한 latest_portfolio.json을 읽어
market != 'KR' 인 종목만 골라 미국 장(NYSE/NASDAQ) 주문을 실행합니다.
"""
import json
import os
import sys
import logging
import datetime
import subprocess
from dotenv import load_dotenv

# 공통 로깅 모듈 (최상단에서 초기화)
sys.path.insert(0, "/Users/Daeho/Projects")
from shared.structured_logger import setup_logger
setup_logger("multi-agent-investor", log_subdir="multi-agent-investor")

from kis_client import KisClient
from executor import execute_portfolio
import config

load_dotenv()

logger = logging.getLogger(__name__)

def main():
    logger.info("=" * 43)
    logger.info("🌙 미국 장 야간 주문 실행 시작")
    logger.info("=" * 43)

    # 1. 포트폴리오 파일 확인
    if not os.path.exists(config.LATEST_PORTFOLIO_FILE):
        logger.error(f"포트폴리오 파일 없음: {config.LATEST_PORTFOLIO_FILE}")
        return

    with open(config.LATEST_PORTFOLIO_FILE, "r", encoding="utf-8") as f:
        record = json.load(f)

    # 2. 날짜 유효성 확인 (오늘 생성된 포트폴리오인지 확인)
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    portfolio_date = record.get("date", "")
    if portfolio_date != today:
        logger.warning(
            f"포트폴리오 날짜 불일치: 저장일={portfolio_date}, 오늘={today}"
        )
        logger.warning("아침 main.py가 실행되지 않았을 수 있습니다. 주문을 중단합니다.")
        return

    reasoning  = record.get("reasoning", "이유 없음")
    portfolio  = record.get("portfolio", [])

    # 3. 미국 종목만 필터링 (CRYPTO 명시적 제외)
    us_portfolio = [a for a in portfolio if a.get('market') not in ('KR', 'CRYPTO')]

    if not us_portfolio:
        logger.info("오늘 포트폴리오에 미국 종목이 없습니다. 주문 없이 종료합니다.")
        return

    logger.info(f"📋 오늘 AI 결론: {reasoning}")
    logger.info(f"🇺🇸 미국 주문 대상 ({len(us_portfolio)}개 종목):")
    for a in us_portfolio:
        logger.info(f"  - {a['name']} ({a['ticker']}): {a['weight']}%")

    # 4. KIS 클라이언트 초기화 및 미국 장 주문 실행
    kis = KisClient()
    kis._get_access_token()

    logger.info("미국 장 주문 시작...")
    execute_portfolio(kis, us_portfolio)

    # 5. 디스코드 알림
    discord_msg = "🌙 **[미국 야간 주문 리밸런싱 완료]**\n\n"
    discord_msg += f"**📝 투자 논리 복기:** {reasoning}\n\n"
    discord_msg += "**🇺🇸 야간 체결 대상:**\n"
    for a in us_portfolio:
        discord_msg += f"  - {a['name']} ({a['ticker']}): {a['weight']}%\n"

    discord_msg += "\n✅ 미국 주식 실시간 개별 체결 알림은 위 메시지들과 별개로 확인 가능합니다."
    kis.send_discord_message(discord_msg)
    logger.info("미국 장 주문 완료 및 디스코드 알림 발송.")

    try:
        subprocess.run(
            [sys.executable, "asset_manager.py", "--reason", "미국 자산 리밸런싱 완료 보고"],
            cwd=config.BASE_DIR,
            capture_output=True,
            text=True
        )
    except Exception as w_e:
        logger.error(f"자산운용가 완료 보고 실행 실패: {w_e}")

if __name__ == "__main__":
    main()
