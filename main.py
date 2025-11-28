#!/usr/bin/env python3
"""
🚀 Auto-Coin Trading Bot - 모듈화된 버전
리팩토링된 암호화폐 자동매매 시스템

주요 기능:
- 자동 거래 실행 (실거래/테스트 모드)
- AI 기반 학습 시스템
- Discord 알림
- 백테스팅
- 성과 분석

사용법:
  python main.py                    # 실거래 모드
  python main.py --test             # 테스트 모드
  python main.py --backtest         # 백테스팅 모드
  python main.py --analyze          # 성과 분석 모드
"""

import sys
import logging
import argparse

# 모듈 임포트
from modules import (
    ConfigManager,
    NotificationManager,
    LearningSystem,
    TradingEngine,
    BacktestEngine,
    PerformanceAnalyzer
)

# 데이터 동기화 시스템 임포트
try:
    from scripts.data_sync_integration import integrate_with_trading_bot
    DATA_SYNC_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ 데이터 동기화 시스템을 사용할 수 없습니다: {e}")
    DATA_SYNC_AVAILABLE = False


def setup_logging():
    """로깅 설정"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('auto_trader.log', encoding='utf-8'),
            logging.StreamHandler()
        ]
    )


def main():
    """메인 함수"""
    setup_logging()

    parser = argparse.ArgumentParser(description='Auto-Coin Trading Bot')
    parser.add_argument('--test', action='store_true', help='테스트 모드 실행')
    parser.add_argument('--backtest', action='store_true', help='백테스팅 모드')
    parser.add_argument('--analyze', action='store_true', help='성과 분석 모드')
    parser.add_argument('--ticker', type=str,
                        default='KRW-BTC', help='백테스팅 대상 코인')
    parser.add_argument('--days', type=int, default=30, help='분석 기간 (일)')

    args = parser.parse_args()

    try:
        # 핵심 시스템 초기화
        config = ConfigManager()
        notifier = NotificationManager(config)
        learning = LearningSystem(config)

        if args.analyze:
            # 성과 분석 모드
            analyzer = PerformanceAnalyzer(learning)
            analyzer.show_performance_report(args.days)

        elif args.backtest:
            # 백테스팅 모드
            backtest = BacktestEngine(config)
            backtest.run_backtest(args.ticker, args.days)

        else:
            # 거래 모드 (실거래 또는 테스트)
            trading = TradingEngine(config, notifier, learning, args.test)

            # 데이터 동기화 시스템 통합
            sync_integration = None
            if DATA_SYNC_AVAILABLE and not args.test:  # 실거래 모드에서만
                try:
                    logging.info("🔄 업비트 데이터 동기화 시스템 통합 중...")
                    sync_integration = integrate_with_trading_bot(trading)
                    logging.info("✅ 데이터 동기화 시스템 통합 완료")

                    # 동기화 상태 리포트
                    status_report = sync_integration.generate_sync_status_report()
                    logging.info(f"데이터 동기화 상태:\n{status_report}")

                except Exception as e:
                    logging.warning(f"⚠️ 데이터 동기화 시스템 통합 실패: {e}")
                    logging.warning("기본 모드로 계속 실행합니다.")

            try:
                # 거래 시스템 실행
                trading.run_trading_loop()
            finally:
                # 종료 시 동기화 시스템 정리
                if sync_integration:
                    sync_integration.stop_background_sync()
                    logging.info("🔄 데이터 동기화 시스템 정상 종료")

    except KeyboardInterrupt:
        logging.info("사용자에 의한 종료")
    except Exception as e:
        logging.error(f"시스템 오류: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
