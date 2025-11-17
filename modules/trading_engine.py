"""
거래 엔진 모듈
"""

import pyupbit
import time
import datetime
import sys
import logging
import json
import os
import gc
import psutil
import signal
import math
from typing import Dict, List, Optional, Tuple, Union
from .config_manager import ConfigManager
from .notification_manager import NotificationManager
from .learning_system import LearningSystem, TradeRecord


class TradingEngine:
    """통합 거래 엔진"""

    def __init__(self, config_manager: ConfigManager, notification_manager: NotificationManager,
                 learning_system: LearningSystem, test_mode: bool = False):
        self.config = config_manager
        self.notifier = notification_manager
        self.learning = learning_system
        self.test_mode = test_mode

        # Upbit API 설정
        if not test_mode:
            access_key = self.config.get('upbit.access_key')
            secret_key = self.config.get('upbit.secret_key')

            if not access_key or not secret_key:
                raise ValueError("Upbit API 키가 설정되지 않았습니다.")

            self.upbit = pyupbit.Upbit(access_key, secret_key)
        else:
            self.upbit = None

        # 거래 상태 관리
        self.positions = {}
        self.cache = {}
        self.running = False
        self.trade_count_today = 0
        self.daily_profit = 0
        self.last_trade_reset = datetime.datetime.now().date()

        # 테스트 모드 상태
        if test_mode:
            self.test_balance = 1000000  # 100만원
            self.test_positions = {}

        # 데이터 파일 경로
        self.data_file = "trading_data.json"

        self._load_trading_data()
        self._setup_signal_handlers()

    def _setup_signal_handlers(self):
        """시그널 처리기 설정"""
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)

    def _signal_handler(self, signum, frame):
        """시그널 처리"""
        logging.info(f"종료 신호 수신: {signum}")
        self.running = False

    def _load_trading_data(self):
        """저장된 거래 데이터 복원"""
        try:
            if os.path.exists(self.data_file):
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                saved_date = datetime.datetime.fromisoformat(
                    data.get('last_trade_reset', '')).date()
                today = datetime.datetime.now().date()

                if saved_date == today:
                    self.trade_count_today = data.get('trade_count_today', 0)
                    self.last_trade_reset = saved_date
                    # 포지션 데이터에서 datetime 문자열을 객체로 변환
                    positions = data.get('positions', {})
                    for ticker, pos_data in positions.items():
                        if 'entry_time' in pos_data:
                            if isinstance(pos_data['entry_time'], str):
                                pos_data['entry_time'] = datetime.datetime.fromisoformat(
                                    pos_data['entry_time'])
                    self.positions = positions
                    self.daily_profit = data.get('daily_profit', 0)

                    logging.info(f"거래 데이터 복원: {self.trade_count_today}회 거래")
                else:
                    self._reset_daily_data()
            else:
                self._reset_daily_data()

        except Exception as e:
            logging.error(f"거래 데이터 로드 실패: {e}")
            self._reset_daily_data()

    def _reset_daily_data(self):
        """일일 데이터 초기화"""
        self.trade_count_today = 0
        self.last_trade_reset = datetime.datetime.now().date()
        self.positions = {}
        self.daily_profit = 0
        logging.info("일일 거래 데이터 초기화")

    def _save_trading_data(self):
        """거래 데이터 저장"""
        try:
            data = {
                'trade_count_today': self.trade_count_today,
                'last_trade_reset': self.last_trade_reset.isoformat(),
                'positions': {k: {
                    **v,
                    'entry_time': v['entry_time'].isoformat() if isinstance(v['entry_time'], datetime.datetime) else v['entry_time']
                } for k, v in self.positions.items()},
                'daily_profit': self.daily_profit,
                'last_update': datetime.datetime.now().isoformat()
            }

            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

        except Exception as e:
            logging.error(f"거래 데이터 저장 실패: {e}")

    def get_balance(self, currency: str = 'KRW') -> float:
        """잔고 조회"""
        if self.test_mode:
            if currency == 'KRW':
                return self.test_balance
            else:
                return self.test_positions.get(f"KRW-{currency}", 0)

        try:
            return self.upbit.get_balance(currency)
        except Exception as e:
            logging.error(f"잔고 조회 실패 ({currency}): {e}")
            return 0

    def calculate_rsi(self, prices: List[float], period: int = 14) -> float:
        """RSI 계산"""
        if len(prices) < period + 1:
            return 50

        gains = []
        losses = []

        for i in range(1, len(prices)):
            diff = prices[i] - prices[i-1]
            if diff >= 0:
                gains.append(diff)
                losses.append(0)
            else:
                gains.append(0)
                losses.append(abs(diff))

        avg_gain = sum(gains[-period:]) / period
        avg_loss = sum(losses[-period:]) / period

        if avg_loss == 0:
            return 100

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))

        return rsi

    def get_signal_context(self, ticker: str) -> Dict:
        """신호 생성 컨텍스트 추출"""
        try:
            df = pyupbit.get_ohlcv(ticker, "minute5", 200)
            if df is None or len(df) < 50:
                return {'market_state': 'UNKNOWN', 'rsi': 50, 'bollinger_position': 0.5}

            prices = df['close'].values
            current_price = prices[-1]

            # RSI 계산
            rsi = self.calculate_rsi(prices)

            # 볼린저밴드 위치
            ma20 = prices[-20:].mean()
            std20 = prices[-20:].std()
            upper_band = ma20 + (2 * std20)
            lower_band = ma20 - (2 * std20)

            if upper_band != lower_band:
                bollinger_position = (
                    current_price - lower_band) / (upper_band - lower_band)
            else:
                bollinger_position = 0.5

            # 시장 상태
            ma5 = prices[-5:].mean()
            ma10 = prices[-10:].mean()

            if ma5 > ma10 > ma20:
                market_state = 'BULL'
            elif ma5 < ma10 < ma20:
                market_state = 'BEAR'
            else:
                market_state = 'SIDEWAYS'

            return {
                'market_state': market_state,
                'rsi': rsi,
                'bollinger_position': max(0, min(1, bollinger_position))
            }

        except Exception as e:
            logging.error(f"신호 컨텍스트 추출 실패: {e}")
            return {'market_state': 'UNKNOWN', 'rsi': 50, 'bollinger_position': 0.5}

    def generate_signal(self, ticker: str) -> str:
        """거래 신호 생성"""
        try:
            # 현재 적응형 매개변수 가져오기
            adaptive_params = self.learning.get_adaptive_params()

            # 시장 데이터 분석
            signal_context = self.get_signal_context(ticker)
            rsi = signal_context['rsi']
            market_state = signal_context['market_state']
            bollinger_pos = signal_context['bollinger_position']

            # 적응형 임계값 적용
            rsi_buy_threshold = adaptive_params.get('rsi_buy_threshold', 30)
            bollinger_buy_ratio = adaptive_params.get(
                'bollinger_buy_ratio', 0.2)

            # 매수 신호 판정
            if market_state == 'BULL' and rsi < rsi_buy_threshold and bollinger_pos < bollinger_buy_ratio:
                return "PREMIUM_BUY"
            elif rsi < (rsi_buy_threshold - 5) and bollinger_pos < (bollinger_buy_ratio + 0.1):
                return "SELECTIVE_BUY"

            # 매도 신호 판정 (포지션이 있는 경우만)
            if ticker in self.positions:
                rsi_sell_threshold = adaptive_params.get(
                    'rsi_sell_threshold', 70)

                if rsi > rsi_sell_threshold or market_state == 'BEAR':
                    return "EMERGENCY_SELL"
                elif bollinger_pos > 0.8:
                    return "CONSERVATIVE_SELL"

            return "HOLD"

        except Exception as e:
            logging.error(f"신호 생성 실패 ({ticker}): {e}")
            return "HOLD"

    def execute_trade(self, ticker: str, action: str) -> bool:
        """거래 실행"""
        try:
            # 일일 거래 한도 체크
            today = datetime.datetime.now().date()
            if today != self.last_trade_reset:
                self._reset_daily_data()
                self._save_trading_data()

            max_daily_trades = self.config.get('trading.max_daily_trades', 50)
            if self.trade_count_today >= max_daily_trades:
                logging.warning(
                    f"일일 거래 한도 달성: {self.trade_count_today}/{max_daily_trades}")
                return False

            # 현재 가격 조회
            current_price = pyupbit.get_current_price(ticker)
            if not current_price:
                return False

            # 투자금액 계산
            krw_balance = self.get_balance('KRW')
            investment_ratio = self.config.get('trading.investment_ratio', 0.1)
            invest_amount = krw_balance * investment_ratio

            min_balance = self.config.get('trading.min_krw_balance', 50000)
            if krw_balance < min_balance:
                logging.warning(
                    f"최소 잔고 부족: {krw_balance:,.0f} < {min_balance:,.0f}")
                return False

            success = False

            if action.endswith("BUY"):
                if self.test_mode:
                    if self.test_balance >= invest_amount:
                        coin_amount = invest_amount / current_price
                        coin_symbol = ticker.replace('KRW-', '')
                        self.test_positions[coin_symbol] = self.test_positions.get(
                            coin_symbol, 0) + coin_amount
                        self.test_balance -= invest_amount
                        success = True
                else:
                    if krw_balance >= invest_amount:
                        result = self.upbit.buy_market_order(
                            ticker, invest_amount)
                        success = result is not None

                if success:
                    # 포지션 기록
                    self.positions[ticker] = {
                        'entry_price': current_price,
                        'entry_time': datetime.datetime.now(),
                        'amount': invest_amount / current_price,
                        'signal_type': action,
                        'invest_amount': invest_amount
                    }

                    self.trade_count_today += 1

                    # 학습 데이터 기록
                    signal_context = self.get_signal_context(ticker)
                    trade_record = TradeRecord(
                        timestamp=datetime.datetime.now(),
                        coin=ticker,
                        action='BUY',
                        signal_type=action,
                        price=current_price,
                        amount=invest_amount / current_price,
                        market_state=signal_context['market_state'],
                        rsi=signal_context['rsi'],
                        bollinger_position=signal_context['bollinger_position']
                    )

                    self.learning.record_trade(trade_record)

                    # 알림 전송
                    color = 0xffd700 if "PREMIUM" in action else 0x00ff00
                    emoji = "💎" if "PREMIUM" in action else "🎯"

                    self.notifier.send_discord(
                        f"{emoji} {action}",
                        f"{ticker} @ {current_price:,.0f} KRW\n투자금: {invest_amount:,.0f}원\n거래: {self.trade_count_today}회",
                        color
                    )

                    logging.info(
                        f"매수 완료: {ticker} @ {current_price:,.0f} | {invest_amount:,.0f}원")

            elif action.endswith("SELL"):
                if ticker not in self.positions:
                    return False

                position = self.positions[ticker]
                entry_price = position['entry_price']
                entry_time = position['entry_time']
                invest_amount = position['invest_amount']

                if self.test_mode:
                    coin_symbol = ticker.replace('KRW-', '')
                    if coin_symbol in self.test_positions and self.test_positions[coin_symbol] > 0:
                        coin_amount = self.test_positions[coin_symbol]
                        sell_amount = coin_amount * current_price
                        self.test_balance += sell_amount
                        del self.test_positions[coin_symbol]
                        success = True
                else:
                    coin_symbol = ticker.split('-')[1]
                    balance = self.get_balance(coin_symbol)
                    if balance > 0.00001:
                        result = self.upbit.sell_market_order(ticker, balance)
                        success = result is not None

                if success:
                    # 수수료를 고려한 수익 계산
                    commission_rate = self.config.get(
                        'trading.commission_rate', 0.0005)

                    # 실제 매수가 (수수료 포함)
                    actual_buy_price = entry_price * (1 + commission_rate)
                    # 실제 매도가 (수수료 포함)
                    actual_sell_price = current_price * (1 - commission_rate)

                    # 수수료를 고려한 수익률 계산
                    profit_rate = (actual_sell_price -
                                   actual_buy_price) / actual_buy_price
                    profit_amount = invest_amount * profit_rate
                    hold_duration = int(
                        (datetime.datetime.now() - entry_time).total_seconds() / 60)

                    self.trade_count_today += 1
                    self.daily_profit += profit_amount

                    # 학습 결과 업데이트
                    self.learning.update_trade_result(
                        coin=ticker,
                        buy_timestamp=entry_time,
                        success=profit_rate > 0,
                        profit_rate=profit_rate,
                        hold_duration=hold_duration
                    )

                    # 포지션 제거
                    del self.positions[ticker]

                    # 알림 전송
                    color = 0xff4444 if "EMERGENCY" in action else 0xffaa00
                    emoji = "🚨" if "EMERGENCY" in action else "📈"

                    self.notifier.send_discord(
                        f"{emoji} {action}",
                        f"{ticker} @ {current_price:,.0f} KRW\n수익률: {profit_rate:.2%}\n수익: {profit_amount:+,.0f}원",
                        color
                    )

                    logging.info(
                        f"매도 완료: {ticker} @ {current_price:,.0f} | 수익률: {profit_rate:.2%}")

            if success:
                self._save_trading_data()

            return success

        except Exception as e:
            logging.error(f"거래 실행 실패 ({ticker}, {action}): {e}")
            return False

    def run_trading_loop(self):
        """메인 거래 루프"""
        self.running = True

        # 주요 코인 목록
        major_tickers = [
            'KRW-BTC', 'KRW-ETH', 'KRW-XRP', 'KRW-ADA', 'KRW-DOGE',
            'KRW-SOL', 'KRW-AVAX', 'KRW-MATIC', 'KRW-DOT', 'KRW-LINK',
            'KRW-UNI', 'KRW-ATOM', 'KRW-ALGO', 'KRW-NEAR', 'KRW-SAND'
        ]

        mode_str = "테스트" if self.test_mode else "실거래"
        self.notifier.send_discord(
            "🚀 자동매매 봇 시작", f"{mode_str} 모드로 시작합니다.", 0x00ff00)

        try:
            while self.running:
                cycle_start = time.time()

                # 상태 보고
                memory_usage = psutil.virtual_memory().percent
                additional_info = f"일일거래: {self.trade_count_today}회\n일일수익: {self.daily_profit:+,.0f}원"
                self.notifier.send_status_report("정상 운영", additional_info)

                # 각 코인 분석 및 거래
                for ticker in major_tickers:
                    if not self.running:
                        break

                    try:
                        signal = self.generate_signal(ticker)

                        if signal != "HOLD":
                            logging.info(f"신호 발생: {ticker} -> {signal}")

                            if self.execute_trade(ticker, signal):
                                logging.info(f"거래 실행 성공: {ticker} {signal}")

                            # 거래 간격
                            time.sleep(2)

                    except Exception as e:
                        logging.error(f"코인 분석 실패 ({ticker}): {e}")
                        continue

                # 사이클 완료, 대기
                cycle_time = time.time() - cycle_start
                sleep_time = max(30, 60 - cycle_time)  # 최소 30초, 목표 1분 주기

                for _ in range(int(sleep_time)):
                    if not self.running:
                        break
                    time.sleep(1)

        except Exception as e:
            logging.error(f"거래 루프 오류: {e}")
            self.notifier.send_discord(
                "🚨 시스템 오류", f"거래 루프에서 오류 발생: {str(e)}", 0xff0000)

        finally:
            self._shutdown()

    def _shutdown(self):
        """안전한 종료"""
        logging.info("거래 시스템 종료 중...")

        # 데이터 저장
        self._save_trading_data()

        # 성과 요약
        performance = self.learning.get_performance_report(days=1)
        learning_summary = ""
        if performance.get('total_trades', 0) > 0:
            learning_summary = f"\n🧠 오늘 학습: {performance['total_trades']}건 분석"

        # 종료 알림
        mode_str = "테스트" if self.test_mode else "실거래"
        self.notifier.send_discord(
            "⏹️ 자동매매 봇 종료",
            f"{mode_str} 모드 종료\n거래: {self.trade_count_today}회\n수익: {self.daily_profit:+,.0f}원{learning_summary}",
            0xffaa00
        )

        logging.info("거래 시스템 종료 완료")
