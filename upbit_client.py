import pyupbit
import os
from dotenv import load_dotenv

load_dotenv()

class UpbitClient:
    def __init__(self):
        self.access_key = os.environ.get("UPBIT_ACCESS_KEY")
        self.secret_key = os.environ.get("UPBIT_SECRET_KEY")
        # Initialize only if keys exist to prevent crashing on mock runs
        if self.access_key and self.secret_key:
            self.upbit = pyupbit.Upbit(self.access_key, self.secret_key)
        else:
            self.upbit = None
            
    def get_current_price(self, ticker: str) -> float:
        """
        코인 현재가 반환
        """
        price = pyupbit.get_current_price(ticker)
        return float(price) if price else 0.0

    def get_balance(self, ticker: str="KRW") -> float:
        """
        자산 잔고 반환 (KRW 포함)
        """
        if not self.upbit:
            print("⚠️ 업비트 API 키가 없어 가상 모드로 0원 반환합니다.")
            return 0.0
        balance = self.upbit.get_balance(ticker)
        return float(balance) if balance else 0.0

    def get_all_balances(self) -> list:
        """
        모든 보유 자산 잔고 반환 (KRW 포함)
        """
        if not self.upbit:
            return [{"currency": "KRW", "balance": "5000000.0"}]
        balances = self.upbit.get_balances()
        return balances if balances else []

    def buy_market_order(self, ticker: str, price_krw: float):
        """
        지정된 금액(원) 만큼 시장가 매수
        """
        if not self.upbit:
            print(f"⚠️ [모의투자] {ticker} 코인을 {price_krw}원 어치 매수합니다.")
            return {"msg": "모의주문 성공"}
        return self.upbit.buy_market_order(ticker, price_krw)

    def sell_market_order(self, ticker: str, volume: float):
        """
        지정된 수량 만큼 시장가 매도
        """
        if not self.upbit:
            print(f"⚠️ [모의투자] {ticker} 코인을 {volume}개 매도합니다.")
            return {"msg": "모의주문 성공"}
        return self.upbit.sell_market_order(ticker, volume)
