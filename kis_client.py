import os
import sys
import requests
import json
import time
from dotenv import load_dotenv

load_dotenv()

# 토큰 파일 경로 (프로세스 간 공유 캐시)
TOKEN_CACHE_FILE = os.path.join(os.path.dirname(__file__), ".kis_token.json")

class KisClient:
    def __init__(self):
        self.app_key = os.environ.get("APP_KEY")
        self.app_secret = os.environ.get("APP_SECRET")
        self.cano = os.environ.get("CANO")
        self.acnt_prdt_cd = os.environ.get("ACNT_PRDT_CD")
        self.url_base = os.environ.get("URL_BASE")
        self.access_token = None
        self.token_expired_at = 0
        # 시작 시 파일 캐시에서 토큰 복구 (프로세스 재시작 후에도 재사용)
        self._load_token_cache()

    def _load_token_cache(self):
        """파일 캐시에서 토큰 로드 (유효한 경우에만 복구)"""
        try:
            if os.path.exists(TOKEN_CACHE_FILE):
                with open(TOKEN_CACHE_FILE, "r") as f:
                    cache = json.load(f)
                expired_at = cache.get("expired_at", 0)
                if time.time() < expired_at:
                    self.access_token = cache.get("access_token")
                    self.token_expired_at = expired_at
        except Exception:
            pass  # 캐시 파일 손상 등 — 무시하고 새로 발급

    def _save_token_cache(self):
        """발급된 토큰을 파일 캐시에 저장 (다른 프로세스가 재사용)"""
        try:
            with open(TOKEN_CACHE_FILE, "w") as f:
                json.dump({
                    "access_token": self.access_token,
                    "expired_at": self.token_expired_at
                }, f)
        except Exception:
            pass  # 저장 실패 — 다음 번에 새로 발급하면 됨

    def _get_access_token(self):
        # 메모리 캐시가 유효하면 즉시 반환
        if self.access_token and time.time() < self.token_expired_at:
            return self.access_token

        url = f"{self.url_base}/oauth2/tokenP"
        headers = {"content-type": "application/json"}
        body = {
            "grant_type": "client_credentials",
            "appkey": self.app_key,
            "appsecret": self.app_secret
        }

        res = requests.post(url, headers=headers, data=json.dumps(body))

        if res.status_code == 200:
            data = res.json()
            self.access_token = data["access_token"]
            # 유효기간(보통 24시간)에서 안전하게 1시간(3600초) 뺀 시간을 만료 시간으로 설정
            self.token_expired_at = time.time() + int(data.get("expires_in", 86400)) - 3600
            self._save_token_cache()  # 파일에도 저장 → 다른 프로세스가 재사용
            return self.access_token
        else:
            raise Exception(f"API Token 요청 실패: {res.status_code} - {res.text}")

    def _get_hashkey(self, data):
        url = f"{self.url_base}/uapi/hashkey"
        headers = {
            "content-type": "application/json",
            "appkey": self.app_key,
            "appsecret": self.app_secret
        }
        res = requests.post(url, headers=headers, data=json.dumps(data))
        if res.status_code == 200:
            return res.json()["HASH"]
        else:
            raise Exception(f"Hashkey 요청 실패: {res.text}")

    def get_current_price(self, ticker: str):
        """
        국내 주식/ETF 현재가 조회
        """
        token = self._get_access_token()
        url = f"{self.url_base}/uapi/domestic-stock/v1/quotations/inquire-price"
        headers = {
            "Content-Type": "application/json",
            "authorization": f"Bearer {token}",
            "appKey": self.app_key,
            "appSecret": self.app_secret,
            "tr_id": "FHKST01010100", # 현재가조회
            "custtype": "P"
        }
        params = {
            "FID_COND_MRKT_DIV_CODE": "J",
            "FID_INPUT_ISCD": ticker
        }
        
        res = requests.get(url, headers=headers, params=params)
        data = res.json()
        
        if res.status_code == 200 and data.get("rt_cd") == "0":
            return float(data["output"]["stck_prpr"])
        else:
            raise Exception(f"현재가 조회 실패 ({ticker}): {data.get('msg1', data)})")

    def get_balance(self):
        """
        국내 주식 잔고 조회
        """
        token = self._get_access_token()
        url = f"{self.url_base}/uapi/domestic-stock/v1/trading/inquire-balance"
        headers = {
            "Content-Type": "application/json",
            "authorization": f"Bearer {token}",
            "appKey": self.app_key,
            "appSecret": self.app_secret,
            "tr_id": "TTTC8434R", # 실전투자 기준
            "custtype": "P"
        }
        params = {
            "CANO": self.cano,
            "ACNT_PRDT_CD": self.acnt_prdt_cd,
            "AFHR_FLPR_YN": "N",
            "OFL_YN": "",
            "INQR_DVSN": "02",
            "UNPR_DVSN": "01",
            "FUND_STTL_ICLD_YN": "N",
            "FNCG_AMT_AUTO_RDPT_YN": "N",
            "PRCS_DVSN": "01",
            "CTX_AREA_FK100": "",
            "CTX_AREA_NK100": ""
        }
        
        res = requests.get(url, headers=headers, params=params)
        return res.json()

    def get_us_balance(self):
        """
        해외 주식 잔고 조회 (미국 주식)
        """
        token = self._get_access_token()
        url = f"{self.url_base}/uapi/overseas-stock/v1/trading/inquire-balance"
        headers = {
            "Content-Type": "application/json",
            "authorization": f"Bearer {token}",
            "appKey": self.app_key,
            "appSecret": self.app_secret,
            "tr_id": "TTTS3012R", # 해외주식 잔고
            "custtype": "P"
        }
        params = {
            "CANO": self.cano,
            "ACNT_PRDT_CD": self.acnt_prdt_cd,
            "OVRS_EXCG_CD": "NASD", # 주요 거래소 명시 (NASD, NYSE, AMEX)
            "TR_CRCY_CD": "USD",
            "CTX_AREA_FK200": "",
            "CTX_AREA_NK200": ""
        }
        
        res = requests.get(url, headers=headers, params=params)
        return res.json()

    def order_cash(self, is_buy: bool, ticker: str, quantity: int, order_type: str = "01", price: str = "0"):
        """
        국내 주식 주문 (매수/매도)
        order_type: "01" (시장가), "00" (지정가)
        """
        token = self._get_access_token()
        url = f"{self.url_base}/uapi/domestic-stock/v1/trading/order-cash"
        
        body = {
            "CANO": self.cano,
            "ACNT_PRDT_CD": self.acnt_prdt_cd,
            "PDNO": ticker,
            "ORD_DVSN": order_type,
            "ORD_QTY": str(quantity),
            "ORD_UNPR": str(price)
        }
        
        hashkey = self._get_hashkey(body)
        
        headers = {
            "Content-Type": "application/json",
            "authorization": f"Bearer {token}",
            "appKey": self.app_key,
            "appSecret": self.app_secret,
            "tr_id": "TTTC0802U" if is_buy else "TTTC0801U", # TTTC0802U: 매수, TTTC0801U: 매도
            "custtype": "P",
            "hashkey": hashkey
        }
        
        res = requests.post(url, headers=headers, data=json.dumps(body))
        return res.json()

    def order_us_cash(self, is_buy: bool, ticker: str, quantity: int, price: str, exchange: str = "NASD"):
        """
        해외 주식 주문 (매수/매도)
        exchange: NASD (나스닥), NYSE (뉴욕), AMEX (아멕스)
        해외 주식은 주로 지정가(00) 주문임. 시장가 관련 세팅은 환경에 따라 다를 수 있음.
        """
        token = self._get_access_token()
        url = f"{self.url_base}/uapi/overseas-stock/v1/trading/order"
        
        body = {
            "CANO": self.cano,
            "ACNT_PRDT_CD": self.acnt_prdt_cd,
            "OVRS_EXCG_CD": exchange,
            "PDNO": ticker,
            "ORD_QTY": str(quantity),
            "OVRS_ORD_UNPR": str(price),
            "ORD_SVR_DVSN_CD": "0", # 0: 일반
            "ORD_DVSN": "00" # 지정가
        }
        
        hashkey = self._get_hashkey(body)
        
        headers = {
            "Content-Type": "application/json",
            "authorization": f"Bearer {token}",
            "appKey": self.app_key,
            "appSecret": self.app_secret,
            "tr_id": "TTTT1002U" if is_buy else "TTTT1006U", # TTTT1002U: 미국 매수, TTTT1006U: 미국 매도
            "custtype": "P",
            "hashkey": hashkey
        }
        
        res = requests.post(url, headers=headers, data=json.dumps(body))
        return res.json()

    def buy(self, ticker: str, quantity: int, order_type: str = "01", price: str = "0"):
        return self.order_cash(True, ticker, quantity, order_type, price)
        
    def sell(self, ticker: str, quantity: int, order_type: str = "01", price: str = "0"):
        return self.order_cash(False, ticker, quantity, order_type, price)
        
    def buy_us(self, ticker: str, quantity: int, price: str, exchange: str = "NASD"):
        return self.order_us_cash(True, ticker, quantity, price, exchange)
        
    def sell_us(self, ticker: str, quantity: int, price: str, exchange: str = "NASD"):
        return self.order_us_cash(False, ticker, quantity, price, exchange)

    def send_discord_message(self, message: str, channel: str = ""):
        """
        Discord 메시지 전송 (Shared DiscordNotifier 사용)
        
        Args:
            message: 전송할 메시지
            channel: 대상 채널 (auto-detect if empty)
                - "investment": 투자 거래 알림
                - "asset": 자산 보고
                - "daily": 일반 알림
        """
        # 채널 통일: 투자 관련 모든 메시지(자산 현황, 체결 알림, 회의 결과)를 단일 투자 채널로 통합 전송
        if not channel:
            channel = "investment"
        
        try:
            # shared 라이브러리 경로 추가
            _shared_parent = "/Users/Daeho/Projects"
            if _shared_parent not in sys.path:
                sys.path.insert(0, _shared_parent)
            
            from shared.discord_notifier import send_investment_report
            send_investment_report("투자 및 자산 알림", message)
        except ImportError:
            # Fallback: 기존 방식
            webhook_url = os.environ.get("DISCORD_WEBHOOK_URL")
            if webhook_url:
                data = {"content": message}
                requests.post(webhook_url, json=data)

if __name__ == "__main__":
    client = KisClient()
    print("토큰 발급 테스트 시작...")
    token = client._get_access_token()
    print(f"토큰 발급 성공: {token[:20]}...")
    
    print("\n잔고 조회 테스트 시작...")
    balance_info = client.get_balance()
    # 통신 성공 여부 출력
    msg = balance_info.get("msg1", "")
    print(f"조회 결과 메세지: {msg}")
    
    output2 = balance_info.get("output2", [])
    if output2:
        total_assets = output2[0].get("tot_evlu_amt", "0")
        print(f"총 평가 금액: {total_assets} 원")
    else:
        print("조회된 잔고 내역이 없습니다.", balance_info)
    
    client.send_discord_message(f"✅ KIS API 연동 및 잔고 조회 테스트 성공! (총 자산: {total_assets} 원)")
