"""
market_guard.py — 24H 코인 감시 & 장중 주식 -7% 비상 폭락 리스크 가드 데몬

1. 🪙 24H 가상자산 감시: ±5% 이상 급등락 발생 시 긴급 회의 소집
2. 🏦 장중 주식 -7% 비상 리스크 가드: 
   - 한국 장 (09:00~15:30), 미국 장 (22:30~05:00 / 23:30~06:00)
   - 보유 주식 종목이 -7% 이상 급락 시 디스코드 긴급 경보 발송 및 비상 회의 소집
"""
import os
import sys
import time
import datetime
import logging
import subprocess
import yfinance as yf
from dotenv import load_dotenv

import config
from upbit_client import UpbitClient
from kis_client import KisClient

load_dotenv()

# 로거 설정
logger = logging.getLogger("market_guard")
logger.setLevel(logging.INFO)
if not logger.handlers:
    logger.addHandler(config.get_rotating_handler(config.CRYPTO_LOG, max_bytes=10 * 1024 * 1024, backup_count=5))
    console = logging.StreamHandler()
    console.setFormatter(logging.Formatter("%(asctime)s - [%(name)s] - %(levelname)s - %(message)s"))
    logger.addHandler(console)

BASE_WATCHLIST_CRYPTO = [
    "KRW-BTC", "KRW-ETH", "KRW-SOL", "KRW-XRP", "KRW-DOGE", "KRW-USDT"
]

def get_active_cryptos(uc: UpbitClient) -> list[str]:
    active = set(BASE_WATCHLIST_CRYPTO)
    try:
        for bal in uc.get_all_balances():
            cur = bal.get("currency", "")
            qty = float(bal.get("balance", 0))
            if cur != "KRW" and qty > 0:
                active.add(f"KRW-{cur}")
    except Exception as e:
        logger.error(f"[코인감시] 보유 코인 조회 실패: {e}")
    return sorted(active)

def get_active_stocks(kis: KisClient) -> list[dict]:
    """현재 보유 중인 한/미 주식 종목 목록 조회"""
    stocks = []
    try:
        kr_res = kis.get_balance()
        for item in kr_res.get('output1', []):
            qty = int(item.get('hldg_qty', '0'))
            if qty > 0:
                stocks.append({
                    'ticker': item.get('pdno', ''),
                    'name': item.get('prdt_name', ''),
                    'market': 'KR'
                })
    except Exception as e:
        logger.error(f"[주식감시] 국내 주식 잔고 조회 실패: {e}")

    try:
        us_res = kis.get_us_balance()
        for item in us_res.get('output1', []):
            qty = float(item.get('ovrs_cblc_qty', item.get('ccld_qty_smic', '0')))
            if qty > 0:
                stocks.append({
                    'ticker': item.get('ovrs_pdno', ''),
                    'name': item.get('ovrs_item_name', ''),
                    'market': 'US'
                })
    except Exception as e:
        logger.error(f"[주식감시] 미국 주식 잔고 조회 실패: {e}")
    return stocks

def is_kr_market_open() -> bool:
    now = datetime.datetime.now()
    if now.weekday() >= 5: return False
    return 9 <= now.hour < 15 or (now.hour == 15 and now.minute <= 30)

def is_us_market_open() -> bool:
    now = datetime.datetime.now()
    if now.weekday() >= 5: return False
    # 서머타임 22:30~05:00, 동절기 23:30~06:00
    return now.hour >= 22 or now.hour < 6

def trigger_emergency_scrum(reason_msg: str, kis: KisClient):
    """비상 리스크 스크럼 소집"""
    logger.warning(f"🚨 [비상 소집] {reason_msg}")
    kis.send_discord_message(f"🚨 **[비상 리스크 스크럼 소집]**\n{reason_msg}\n 즉시 AI 긴급 회의를 구동합니다.")
    
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    python_bin = os.path.join(BASE_DIR, "venv/bin/python")
    if not os.path.exists(python_bin):
        python_bin = sys.executable
    
    try:
        subprocess.run([python_bin, os.path.join(BASE_DIR, "orchestrator.py"), "--mode", "EMERGENCY", "--reason", reason_msg], cwd=BASE_DIR)
        logger.info("✅ 비상 리밸런싱 회의 완수.")
    except Exception as e:
        logger.error(f"❌ 비상 회의 실행 실패: {e}")

def main_loop():
    uc = UpbitClient()
    kis = KisClient()

    logger.info("🛡️ [마켓 가드 데몬 가동] 24H 코인 감시 & 장중 주식 -7% 비상 리스크 가드 준비 완료")
    
    crypto_baselines = {}
    last_crypto_refresh = 0
    
    while True:
        try:
            now = time.time()
            
            # 1. 코인 감시 목록 갱신 (1시간마다)
            if now - last_crypto_refresh > 3600:
                cryptos = get_active_cryptos(uc)
                for c in cryptos:
                    try:
                        p = uc.get_current_price(c)
                        if p: crypto_baselines[c] = p
                    except: pass
                last_crypto_refresh = now
                logger.info(f"🪙 [코인 감시] {len(cryptos)}개 종목 감시 중")

            # 2. 🪙 가상자산 ±5% 변동성 감시
            cryptos = get_active_cryptos(uc)
            for c in cryptos:
                base_p = crypto_baselines.get(c)
                if not base_p:
                    p = uc.get_current_price(c)
                    if p: crypto_baselines[c] = p
                    continue
                cur_p = uc.get_current_price(c)
                if not cur_p: continue
                pct = ((cur_p - base_p) / base_p) * 100.0
                if abs(pct) >= 5.0:
                    direction = "📈 급등" if pct > 0 else "📉 급락"
                    msg = f"코인 {c} {direction} ({pct:+.2f}%)\n기준가 {base_p:,.0f}원 ➡️ 현재가 {cur_p:,.0f}원"
                    trigger_emergency_scrum(msg, kis)
                    # 기준가 갱신 후 1시간 대기
                    crypto_baselines[c] = cur_p
                    time.sleep(3600)
                    break

            # 3. 🏦 장중 주식 -7% 비상 리스크 감시
            if is_kr_market_open() or is_us_market_open():
                stocks = get_active_stocks(kis)
                for s in stocks:
                    ticker = s['ticker']
                    name = s['name']
                    mkt = s['market']
                    try:
                        if mkt == 'KR':
                            item_info = kis.get_balance().get('output1', [])
                            for it in item_info:
                                if it.get('pdno') == ticker:
                                    pfls_rt = float(it.get('evlu_pfls_rt', 0))
                                    if pfls_rt <= -7.0:
                                        msg = f"주식 {name}({ticker}) 장중 손실률 {pfls_rt:+.2f}% 경고 (-7% 돌파)"
                                        trigger_emergency_scrum(msg, kis)
                                        time.sleep(3600)
                                        break
                    except Exception as st_e:
                        logger.error(f"주식 감시 예외 ({name}): {st_e}")

            time.sleep(300) # 5분 간격 점검

        except Exception as e:
            logger.error(f"마켓 가드 데몬 루프 오류: {e}")
            time.sleep(60)

if __name__ == "__main__":
    main_loop()
