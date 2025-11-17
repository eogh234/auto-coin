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
            trading.run_trading_loop()

    except KeyboardInterrupt:
        logging.info("사용자에 의한 종료")
    except Exception as e:
        logging.error(f"시스템 오류: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
