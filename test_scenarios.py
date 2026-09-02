import unittest
from unittest.mock import MagicMock, patch
import datetime
import executor
import config

class TestInvestmentRobustness(unittest.TestCase):

    def test_market_hours_logic(self):
        """시장 운영 시간 체크 로직 검증"""
        # 평일 오후 1시 (개장 중)
        open_time = datetime.datetime(2026, 4, 13, 13, 0) # 월요일
        with patch('datetime.datetime') as mock_date:
            mock_date.now.return_value = open_time
            self.assertTrue(executor.is_market_open('KR'))

        # 평일 밤 11시 (폐장 중)
        closed_time = datetime.datetime(2026, 4, 13, 23, 0)
        with patch('datetime.datetime') as mock_date:
            mock_date.now.return_value = closed_time
            self.assertFalse(executor.is_market_open('KR'))

        # 일요일 오후 1시 (폐장 중)
        sunday_time = datetime.datetime(2026, 4, 12, 13, 0)
        with patch('datetime.datetime') as mock_date:
            mock_date.now.return_value = sunday_time
            self.assertFalse(executor.is_market_open('KR'))

    @patch('executor.get_current_price')
    @patch('executor.is_market_open')
    def test_stock_execution_skips_when_closed(self, mock_is_open, mock_price):
        """시장 폐장 시 한국 주식 주문이 스킵되는지 확인"""
        mock_is_open.return_value = False
        mock_price.return_value = 70000.0 # 삼성전자 가상 가격
        
        mock_kis = MagicMock()
        target_portfolio = [
            {"name": "삼성전자", "ticker": "005930", "weight": 50, "market": "KR"}
        ]
        
        executor.execute_portfolio(mock_kis, target_portfolio)
        
        # 시장이 닫혔으므로 kis.buy 나 kis.sell 이 호출되지 않아야 함
        self.assertFalse(mock_kis.buy.called)

    @patch('executor.UpbitClient')
    def test_crypto_execution_safety_buffer(self, mock_upbit_class):
        """가상자산 매수 시 안전 마진(99.5%)이 적용되는지 확인"""
        mock_upbit = mock_upbit_class.return_value
        mock_upbit.get_balance.return_value = 100000.0 # 10만원 잔고
        mock_upbit.get_all_balances.return_value = []
        mock_upbit.get_current_price.return_value = 1000.0
        
        target_portfolio = [
            {"name": "비트코인", "ticker": "KRW-BTC", "weight": 100}
        ]
        
        executor.execute_crypto(target_portfolio)
        
        # buy_market_order 가 호출되었을 때, 금액이 100,000원이 아닌 99,500원(또는 그 이하)이어야 함
        self.assertTrue(mock_upbit.buy_market_order.called)
        args, kwargs = mock_upbit.buy_market_order.call_args
        buy_amount = args[1]
        
        self.assertLessEqual(buy_amount, 100000.0 * 0.995)
        print(f"Verified Crypto Buy Amount (with buffer): {buy_amount:.2f}")

if __name__ == '__main__':
    unittest.main()
