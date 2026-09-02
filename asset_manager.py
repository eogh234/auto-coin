import os
import sys
import time
import datetime
import sqlite3
import argparse
import json
import yfinance as yf
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage

# 프로젝트 경로 설정 및 모듈 임포트
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(BASE_DIR)

import config
from kis_client import KisClient
from upbit_client import UpbitClient

load_dotenv(os.path.join(BASE_DIR, ".env"))

def get_exchange_rate():
    """USD -> KRW 환율 조회"""
    try:
        data = yf.Ticker("KRW=X").history(period="1d")
        if not data.empty:
            return float(data['Close'].iloc[-1])
    except Exception as e:
        print(f"환율 조회 실패: {e}")
    return 1450.0  # Fallback

def init_db(db_path):
    """자산 내역 테이블 초기화"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS wealth_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT UNIQUE,
            total_val REAL,
            kr_val REAL,
            us_val REAL,
            crypto_val REAL,
            cash_val REAL
        );
    """)
    conn.commit()
    conn.close()

def save_wealth_log(db_path, date_str, total_val, kr_val, us_val, crypto_val, cash_val):
    """오늘의 자산 로그 저장/업데이트"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO wealth_history (date, total_val, kr_val, us_val, crypto_val, cash_val)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (date_str, total_val, kr_val, us_val, crypto_val, cash_val))
    conn.commit()
    conn.close()

def get_historical_val(db_path, date_str, days_ago):
    """특정 영업일 전 자산 총평가액 조회"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    target_dt = datetime.datetime.strptime(date_str, "%Y-%m-%d") - datetime.timedelta(days=days_ago)
    target_str = target_dt.strftime("%Y-%m-%d")
    
    cursor.execute("""
        SELECT total_val FROM wealth_history 
        WHERE date <= ? 
        ORDER BY date DESC LIMIT 1
    """, (target_str,))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else None

def fetch_assets(kis, uc, exchange_rate):
    """실시간 API 기반 통합 자산 데이터 수집"""
    kr_val = 0.0
    us_val = 0.0
    crypto_val = 0.0
    cash_val = 0.0
    holdings = []

    # 1. KIS 잔고 조회 (국내주식 + KIS 현금)
    try:
        kr_res = kis.get_balance()
        kr_out2 = kr_res.get('output2', [{}])
        if isinstance(kr_out2, list):
            kr_out2 = kr_out2[0] if kr_out2 else {}
        kr_cash = float(kr_out2.get('dnca_tot_amt', 0))
        kr_stocks = float(kr_out2.get('scts_evlu_amt', 0))
        
        kr_val += kr_stocks
        cash_val += kr_cash

        for item in kr_res.get('output1', []):
            qty = int(item.get('hldg_qty', '0'))
            if qty > 0:
                holdings.append({
                    "name": item.get('prdt_name', ''),
                    "ticker": item.get('pdno', ''),
                    "type": "KR주식",
                    "val": float(item.get('evlu_amt', 0)),
                    "detail": f"{qty}주 | 평단 {float(item.get('pchs_avg_pric', 0)):,.0f}원 | 손익 {float(item.get('evlu_pfls_amt',0)):+,.0f}원 ({float(item.get('evlu_pfls_rt',0)):+.1f}%)"
                })
    except Exception as e:
        print(f"국내 자산 조회 에러: {e}")

    # 2. KIS 미국주식 조회
    try:
        us_res = kis.get_us_balance()
        for item in us_res.get('output1', []):
            qty = float(item.get('ovrs_cblc_qty', item.get('ccld_qty_smic', '0')))
            if qty > 0:
                eval_usd = float(item.get('ovrs_stck_evlu_amt', 0))
                eval_krw = eval_usd * exchange_rate
                us_val += eval_krw
                holdings.append({
                    "name": item.get('ovrs_item_name', ''),
                    "ticker": item.get('ovrs_pdno', ''),
                    "type": "US주식",
                    "val": eval_krw,
                    "detail": f"{qty:.2f}주 | 평단 ${float(item.get('pchs_avg_pric', 0)):.2f} | 손익 ${float(item.get('frcr_evlu_pfls_amt',0)):+.2f} ({float(item.get('evlu_pfls_rt',0)):+.1f}%)"
                })
    except Exception as e:
        print(f"해외 자산 조회 에러: {e}")

    # KIS 가용 외화 예수금 조회 시도
    try:
        import requests as _req
        _token = kis._get_access_token()
        _url = f"{kis.url_base}/uapi/overseas-stock/v1/trading/inquire-psamount"
        _headers = {
            'Content-Type': 'application/json',
            'authorization': f'Bearer {_token}',
            'appKey': kis.app_key, 'appSecret': kis.app_secret,
            'tr_id': 'TTTS3007R', 'custtype': 'P'
        }
        _params = {
            'CANO': kis.cano, 'ACNT_PRDT_CD': kis.acnt_prdt_cd,
            'OVRS_EXCG_CD': 'NASD', 'OVRS_ORD_UNPR': '1.00', 'ITEM_CD': 'AAPL'
        }
        _res = _req.get(_url, headers=_headers, params=_params, timeout=5)
        _out = _res.json().get('output', {})
        # 통합증거금 기준 원화 포함 USD 환산금액이 아닌 순수 외화예수금만 있다면 그것을 합쳐주고, 아니면 중복 합산 방지를 위해 제외
        # 여기서는 KIS 국내 예수금이 이미 kr_cash에 반영되어 있으므로 달러 보유금만 추가 환산
        us_cash_usd = float(_out.get('frcr_dncl_amt_2', 0)) # 외화예수금(D+2)
        if us_cash_usd > 0:
            cash_val += us_cash_usd * exchange_rate
    except:
        pass

    # 3. 업비트 코인 조회
    try:
        for item in uc.get_all_balances():
            currency = item.get('currency', '')
            qty = float(item.get('balance', '0'))
            if qty <= 0:
                continue
            if currency == 'KRW':
                cash_val += qty
            else:
                ticker_up = f"KRW-{currency}"
                cur_price = uc.get_current_price(ticker_up)
                eval_krw = qty * cur_price
                crypto_val += eval_krw
                holdings.append({
                    "name": currency,
                    "ticker": ticker_up,
                    "type": "코인",
                    "val": eval_krw,
                    "detail": f"{qty:.4f}개 | 평단 {float(item.get('avg_buy_price', 0)):,.0f}원 | 손익 {(cur_price - float(item.get('avg_buy_price',0)))*qty:+,.0f}원"
                })
    except Exception as e:
        print(f"가상자산 조회 에러: {e}")

    total_val = kr_val + us_val + crypto_val + cash_val
    return total_val, kr_val, us_val, crypto_val, cash_val, holdings

def load_latest_portfolio_decision():
    """오늘 아침 에이전트들이 제안한 포트폴리오(latest_portfolio.json) 정보 로드"""
    if os.path.exists(config.LATEST_PORTFOLIO_FILE):
        try:
            with open(config.LATEST_PORTFOLIO_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"latest_portfolio.json 로드 실패: {e}")
    return None

def generate_ai_advice(total_val, kr_val, us_val, crypto_val, cash_val, holdings, returns, target_decision):
    """자산운용가 AI의 분석 리포트 및 리스크 조언 피드백 생성"""
    groq_key = os.environ.get("GROQ_API_KEY")
    if not groq_key:
        return "⚠️ GROQ_API_KEY 누락으로 AI 조언 생성이 비활성화되었습니다."

    llm = ChatGroq(
        model=config.MODELS["high"],
        temperature=0.3,
        max_tokens=1500,
        api_key=groq_key
    )

    holdings_str = ""
    for h in holdings:
        weight = (h['val'] / total_val * 100) if total_val > 0 else 0
        holdings_str += f"- [{h['type']}] {h['name']} ({h['ticker']}): 비중 {weight:.1f}%, 평가금액 {h['val']:,.0f}원 ({h['detail']})\n"

    target_str = "없음"
    if target_decision:
        target_str = json.dumps(target_decision, ensure_ascii=False, indent=2)

    sys_prompt = """당신은 사용자의 통합 자산 관리자(Chief Wealth Manager)이자 금융 비서입니다.
사용자는 스크립트에 의한 자동 투자뿐만 아니라, 스스로 개별 판단하여 매매하는 '수동 투자'를 병행하고 있어 계좌에는 다양한 주식과 코인이 복합적으로 들어있습니다.
오늘의 실시간 자산 현황, 역사적 투자 성과(1D, 7D, 30D 수익률), 그리고 오늘 아침 투자 에이전트들의 회의 제안서(latest_portfolio)를 세밀하게 분석하십시오.

현재 자산의 쏠림(리스크), 현금 수준, 자동투자 에이전트 제안 대비 수동 포트폴리오의 괴리 또는 위험 요소를 비판적으로 평가하고, 사용자에게 매우 친근하면서도 날카로운 자산 운용 리스크 관리 피드백을 작성해 주세요. (한국어로 작성하며, 너무 길지 않고 가독성 높은 리스트 형태로 작성하세요.)"""

    prompt = f"""[통합 자산 현황]
- 총 자산: {total_val:,.0f}원
- 국내주식 평가금: {kr_val:,.0f}원
- 해외주식 평가금: {us_val:,.0f}원
- 가상자산 평가금: {crypto_val:,.0f}원
- 원화/달러 통합 예수금: {cash_val:,.0f}원

[개별 자산 상세]
{holdings_str}

[성과 지표]
- 전일 대비: {returns.get('1D', 0.0):+.2f}%
- 1주일 대비: {returns.get('7D', 0.0):+.2f}%
- 1개월 대비: {returns.get('30D', 0.0):+.2f}%

[오늘 아침 자동투자 에이전트 합의안 (latest_portfolio.json)]
{target_str}
"""

    try:
        response = llm.invoke([HumanMessage(content=sys_prompt + "\n\n" + prompt)])
        return response.content
    except Exception as e:
        return f"AI 조언 작성 중 오류 발생: {e}"

def main():
    parser = argparse.ArgumentParser(description="Asset Manager Agent - Financial Secretary")
    parser.add_argument("--reason", type=str, default="정기 보고", help="보고서 출력 타이틀 사유 (예: 정기 보고 #1 - 아침, 긴급 변동성 보고, 리밸런싱 완료 보고)")
    parser.add_argument("--alert", action="store_true", help="🚨 긴급 경보로 Discord에 강조 전송할지 여부")
    args = parser.parse_args()

    print("💼 [자산운용가] 자산 평가 프로세스 시작...")
    
    # 1. DB 초기화
    init_db(config.DB_FILE)

    # 2. 클라이언트 인스턴스화
    kis = KisClient()
    uc = UpbitClient()
    kis._get_access_token()

    # 3. 환율 및 실시간 자산 정보 수집
    exchange_rate = get_exchange_rate()
    total_val, kr_val, us_val, crypto_val, cash_val, holdings = fetch_assets(kis, uc, exchange_rate)
    
    # 4. 오늘의 날짜에 기록 저장
    today_str = datetime.datetime.now().strftime("%Y-%m-%d")
    save_wealth_log(config.DB_FILE, today_str, total_val, kr_val, us_val, crypto_val, cash_val)

    # 5. 기간별 성과 분석 계산 (1D, 7D, 30D)
    returns = {}
    periods = {"1D": 1, "7D": 7, "30D": 30}
    for label, days in periods.items():
        hist_val = get_historical_val(config.DB_FILE, today_str, days)
        if hist_val and hist_val > 0:
            returns[label] = ((total_val / hist_val) - 1.0) * 100.0
        else:
            returns[label] = 0.0  # 기록이 부족하면 0.0%

    # 6. 오늘 아침 자동투자 에이전트 합의 포트폴리오
    target_decision = load_latest_portfolio_decision()

    # 7. AI 자산운용가의 맞춤 피드백/조언 생성
    ai_advice = generate_ai_advice(total_val, kr_val, us_val, crypto_val, cash_val, holdings, returns, target_decision)

    # 8. Discord 메세지 포맷팅 및 전송
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    
    alert_header = "🚨 **[긴급 자산 리포트]**" if args.alert else f"💼 **[{args.reason}]**"
    
    # 등락금액 계산용 전일자산 조회
    hist_1d = get_historical_val(config.DB_FILE, today_str, 1)
    daily_diff_str = ""
    if hist_1d:
        diff_val = total_val - hist_1d
        daily_diff_str = f" ({diff_val:+,.0f}원 | {returns['1D']:+.2f}%)"
    else:
        daily_diff_str = f" ({returns['1D']:+.2f}%)"

    discord_msg = f"""{alert_header} (기준시각: {now_str} | 환율: {exchange_rate:,.1f}원/$)

📊 **[통합 자산 현황 요약]**
* **총 자산 평가액:** **{total_val:,.0f}원**{daily_diff_str}
* 🇰🇷 국내 주식: {kr_val:,.0f}원 ({(kr_val/total_val*100) if total_val > 0 else 0:.1f}%)
* 🇺🇸 해외 주식: {us_val:,.0f}원 ({(us_val/total_val*100) if total_val > 0 else 0:.1f}%)
* 🪙 가상 자산: {crypto_val:,.0f}원 ({(crypto_val/total_val*100) if total_val > 0 else 0:.1f}%)
* 💵 가용 현금: {cash_val:,.0f}원 ({(cash_val/total_val*100) if total_val > 0 else 0:.1f}%)

📈 **[기간별 누적 수익률]**
* **일간 (1D):** {returns['1D']:+.2f}%
* **주간 (7D):** {returns['7D']:+.2f}%
* **월간 (30D):** {returns['30D']:+.2f}%

🧠 **[자산운용가의 맞춤 조언 및 분석]**
{ai_advice}
"""

    # 전송
    kis.send_discord_message(discord_msg)
    print("💼 [자산운용가] Discord로 자산 리포트 및 피드백 전송 완료!")

if __name__ == "__main__":
    main()
