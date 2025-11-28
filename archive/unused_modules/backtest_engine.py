"""
백테스트 엔진 모듈
"""

import pyupbit
import logging
from typing import List
from .config_manager import ConfigManager


class BacktestEngine:
    """백테스팅 엔진"""

    def __init__(self, config_manager: ConfigManager):
        self.config = config_manager

    def run_backtest(self, ticker: str = "KRW-BTC", days: int = 30):
        """백테스팅 실행"""
        logging.info(f"백테스팅 시작: {ticker} ({days}일)")

        try:
            # 데이터 수집
            df = pyupbit.get_ohlcv(ticker, interval="minute60", count=days*24)
            if df is None or len(df) == 0:
                logging.error("백테스팅 데이터를 가져올 수 없습니다.")
                return

            # 백테스팅 변수
            initial_balance = self.config.get(
                'backtest.initial_balance', 1000000)
            commission_rate = self.config.get(
                'backtest.commission_rate', 0.0005)
            balance = initial_balance
            position = 0
            trades = []

            # 간단한 RSI 기반 전략
            for i in range(14, len(df)):
                prices = df['close'].iloc[max(0, i-14):i+1].values
                rsi = self._calculate_rsi(prices)
                current_price = df['close'].iloc[i]

                # 매수 신호 (수수료 고려)
                if position == 0 and rsi < 30 and balance > 50000:
                    invest_amount = balance * 0.1
                    # 매수 시 수수료 차감
                    actual_invest = invest_amount * (1 + commission_rate)
                    if actual_invest <= balance:
                        position = invest_amount / current_price
                        balance -= actual_invest

                        trades.append({
                            'type': 'BUY',
                            'price': current_price,
                            'amount': position,
                            'balance': balance,
                            'timestamp': df.index[i],
                            'commission': invest_amount * commission_rate
                        })

                # 매도 신호 (수수료 고려)
                elif position > 0 and rsi > 70:
                    sell_amount = position * current_price
                    # 매도 시 수수료 차감
                    actual_sell_amount = sell_amount * (1 - commission_rate)
                    balance += actual_sell_amount

                    trades.append({
                        'type': 'SELL',
                        'price': current_price,
                        'amount': position,
                        'balance': balance,
                        'timestamp': df.index[i],
                        'commission': sell_amount * commission_rate
                    })

                    position = 0

            # 마지막 포지션 정리
            if position > 0:
                final_price = df['close'].iloc[-1]
                balance += position * final_price

            # 결과 분석
            total_return = (balance - initial_balance) / initial_balance * 100
            total_trades = len([t for t in trades if t['type'] == 'BUY'])

            print(f"\n📊 백테스팅 결과 ({ticker}, {days}일)")
            print("=" * 50)
            print(f"초기 자금: {initial_balance:,.0f}원")
            print(f"최종 자금: {balance:,.0f}원")
            print(f"총 수익률: {total_return:+.2f}%")
            print(f"총 거래 수: {total_trades}회")
            total_commission = sum(t.get('commission', 0) for t in trades)
            print(f"총 수수료: {total_commission:,.0f}원 ({commission_rate:.2%})")

            if total_trades > 0:
                buy_trades = [t for t in trades if t['type'] == 'BUY']
                sell_trades = [t for t in trades if t['type'] == 'SELL']

                if len(sell_trades) > 0:
                    profits = []
                    commission_rate = self.config.get(
                        'trading.commission_rate', 0.0005)

                    for i, sell in enumerate(sell_trades):
                        if i < len(buy_trades):
                            buy = buy_trades[i]

                            # 수수료를 고려한 수익률 계산
                            actual_buy_price = buy['price'] * \
                                (1 + commission_rate)
                            actual_sell_price = sell['price'] * \
                                (1 - commission_rate)
                            profit_rate = (
                                actual_sell_price - actual_buy_price) / actual_buy_price * 100
                            profits.append(profit_rate)

                    if profits:
                        avg_profit = sum(profits) / len(profits)
                        win_rate = len(
                            [p for p in profits if p > 0]) / len(profits) * 100
                        print(f"평균 거래 수익률: {avg_profit:+.2f}% (수수료 포함)")
                        print(f"승률: {win_rate:.1f}%")

            logging.info(f"백테스팅 완료: 수익률 {total_return:+.2f}%")

        except Exception as e:
            logging.error(f"백테스팅 실행 실패: {e}")

    def _calculate_rsi(self, prices: List[float], period: int = 14) -> float:
        """RSI 계산 (백테스팅용)"""
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
