import os
import time
import subprocess
import datetime
import logging
import config
from upbit_client import UpbitClient
from kis_client import KisClient

# ── 로거 및 10MB 자동 로테이션 핸들러 설정 ──
logger = logging.getLogger("crypto_monitor")
logger.setLevel(logging.INFO)
if not logger.handlers:
    logger.addHandler(config.get_rotating_handler(config.CRYPTO_LOG, max_bytes=10 * 1024 * 1024, backup_count=5))
    console = logging.StreamHandler()
    console.setFormatter(logging.Formatter("%(asctime)s - [%(name)s] - %(levelname)s - %(message)s"))
    logger.addHandler(console)

# ── 감시 기본 종목 (에이전트가 자주 추천하는 주요 코인) ──
BASE_WATCHLIST = [
    "KRW-BTC",   # 비트코인
    "KRW-ETH",   # 이더리움
    "KRW-SOL",   # 솔라나
    "KRW-XRP",   # 리플
    "KRW-DOGE",  # 도지코인
    "KRW-ADA",   # 카르다노
    "KRW-AVAX",  # 아발란체
    "KRW-USDT",  # 테더 (현재 보유 중)
    "KRW-USDC",  # USD 코인
]


def get_active_tickers(uc: UpbitClient) -> list[str]:
    """BASE_WATCHLIST + 현재 업비트에 보유 중인 코인을 합쳐 반환."""
    active = set(BASE_WATCHLIST)
    try:
        for bal in uc.get_all_balances():
            cur = bal.get("currency", "")
            qty = float(bal.get("balance", 0))
            if cur != "KRW" and qty > 0:
                active.add(f"KRW-{cur}")
    except Exception as e:
        logger.error(f"[감시목록] 보유 코인 조회 실패: {e}")
    return sorted(active)


def monitor_crypto(threshold_pct: float = 5.0, check_interval_sec: int = 300):
    uc  = UpbitClient()
    kis = KisClient()

    # 감시 대상 초기화
    tickers = get_active_tickers(uc)
    logger.info(f"👀 [가상자산 24H 감시 모듈 가동]")
    logger.info(f"   감시 주기: {check_interval_sec}초 | 임계치: ±{threshold_pct}%")
    logger.info(f"   감시 종목({len(tickers)}개): {', '.join(tickers)}\n")

    # 기준가 초기 설정
    baseline_prices: dict[str, float] = {}
    for t in tickers:
        try:
            p = uc.get_current_price(t)
            if p and p > 0:
                baseline_prices[t] = p
        except Exception:
            pass

    last_reset_time   = time.time()
    last_refresh_time = time.time()  # 감시 목록 갱신 주기 (1시간)

    while True:
        try:
            now = time.time()

            # 1시간마다 감시 종목 목록 갱신
            if now - last_refresh_time > 3600:
                tickers = get_active_tickers(uc)
                last_refresh_time = now
                logger.info(f"[감시목록 갱신] 총 {len(tickers)}개 종목 감시 중")

            # 24시간마다 기준가 재설정
            if now - last_reset_time > 86400:
                logger.info("[24H 갱신] 감시 기준가를 현재가로 재설정합니다.")
                for t in tickers:
                    try:
                        p = uc.get_current_price(t)
                        if p and p > 0:
                            baseline_prices[t] = p
                    except Exception:
                        pass
                last_reset_time = now

            triggered = False
            for t in tickers:
                try:
                    base_price = baseline_prices.get(t)
                    if not base_price or base_price <= 0:
                        p = uc.get_current_price(t)
                        if p:
                            baseline_prices[t] = p
                        continue

                    cur_price = uc.get_current_price(t)
                    if not cur_price or cur_price <= 0:
                        continue

                    pct_change = ((cur_price - base_price) / base_price) * 100.0

                    if abs(pct_change) >= threshold_pct:
                        direction = "📈 급등" if pct_change > 0 else "📉 급락"
                        ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        msg = (
                            f"🚨 **[가상자산 변동성 경보]** {t} {direction} {pct_change:+.2f}%\n"
                            f"기준가 {base_price:,.0f}원 → 현재 {cur_price:,.0f}원\n"
                            f"   즉시 AI 긴급 회의를 소집합니다."
                        )
                        logger.warning(f"[{ts}] {msg}")
                        kis.send_discord_message(msg)

                        # 긴급 회의 소집
                        logger.info(">> orchestrator.py 긴급 실행 중...")
                        BASE_DIR = os.path.dirname(os.path.abspath(__file__))
                        subprocess.run(
                            [os.path.join(BASE_DIR, "venv/bin/python"), os.path.join(BASE_DIR, "orchestrator.py")],
                            cwd=BASE_DIR
                        )

                        # 기준가 리셋 후 1시간 휴식
                        for t2 in tickers:
                            try:
                                p = uc.get_current_price(t2)
                                if p:
                                    baseline_prices[t2] = p
                            except Exception:
                                pass

                        logger.info("긴급 리밸런싱 완료. 1시간 동안 감시를 일시 중지합니다...")
                        time.sleep(3600)
                        triggered = True
                        break

                except Exception as e:
                    logger.error(f"  [{t}] 가격 조회 오류: {e}")

            if not triggered:
                time.sleep(check_interval_sec)

        except Exception as e:
            logger.error(f"감시 모듈 오류: {e}")
            time.sleep(60)


if __name__ == "__main__":
    monitor_crypto()
