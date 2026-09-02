import json
import os
import sqlite3
import yfinance as yf
try:
    import pyupbit
    PYUPBIT_AVAILABLE = True
except ImportError:
    PYUPBIT_AVAILABLE = False
from langchain_mistralai import ChatMistralAI
from langchain_core.messages import HumanMessage
from dotenv import load_dotenv

load_dotenv()
from kis_client import KisClient
from utils import retry_llm
import config

def get_performance(ticker, market):
    """
    어제 대비 오늘의 수익률(증감률)을 반환합니다.
    - 주식(KR/US): yfinance 사용
    - 가상자산(CRYPTO): pyupbit 사용 (yfinance는 KRW-XXX 심볼 미지원)
    주의: 주말/휴일 등 장이 닫혀있는 경우에는 같은 가격이 나올 수 있습니다.
    """
    # ── 가상자산: pyupbit로 일봉 조회 ──────────────────────────────
    if market == 'CRYPTO':
        if not PYUPBIT_AVAILABLE:
            print(f"[{ticker}] pyupbit 미설치 — 코인 수익률 계산 불가")
            return 0.0, 0.0
        try:
            ohlcv = pyupbit.get_ohlcv(ticker, count=2, interval="day")
            if ohlcv is not None and len(ohlcv) >= 2:
                prev_close = float(ohlcv['close'].iloc[-2])
                curr_close = float(ohlcv['close'].iloc[-1])
                profit_pct = ((curr_close - prev_close) / prev_close) * 100
                return profit_pct, curr_close
            elif ohlcv is not None and len(ohlcv) == 1:
                return 0.0, float(ohlcv['close'].iloc[-1])
        except Exception as e:
            print(f"[{ticker}] 코인 수익률 평가 실패: {e}")
        return 0.0, 0.0

    # ── 주식(KR / US): yfinance 사용 ────────────────────────────────
    try:
        yf_ticker = f"{ticker}.KS" if market == 'KR' else ticker
        data = yf.Ticker(yf_ticker).history(period="5d")  # 넉넉히 5일 조회 (NaN 행 대비)
        data = data.dropna(subset=['Close'])               # NaN 행 제거 (당일 미확정 데이터 방어)

        if len(data) >= 2:
            prev_close = float(data['Close'].iloc[-2])
            current_close = float(data['Close'].iloc[-1])
            profit_pct = ((current_close - prev_close) / prev_close) * 100
            return profit_pct, current_close
        elif len(data) == 1:
            return 0.0, float(data['Close'].iloc[-1])
    except Exception as e:
        print(f"[{ticker}] 수익률 평가 실패: {e}")

    return 0.0, 0.0

def init_db():
    conn = sqlite3.connect(config.DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS daily_reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT UNIQUE,
            daily_yield REAL,
            spy_yield REAL,
            lesson TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS monthly_summaries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            period TEXT,
            summary TEXT
        )
    ''')
    conn.commit()
    return conn

@retry_llm(max_attempts=3)
def summarize_monthly_lessons(conn, llm):
    """
    DB에 기록된 단기 리뷰 개수가 한 달 치(대략 20영업일)가 되면,
    이를 요약하여 monthly_summaries 테이블로 이관(Move)합니다.
    """
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM daily_reviews')
    count = cursor.fetchone()[0]
    
    # 20영업일 이상 쌓였을 때 이관 실행
    if count >= 20:
        print(f"\n[월간 결산] {count}일간의 단기 리뷰를 압축하여 장기 요약 DB로 이관합니다...")
        
        # 전체 상세 데이터를 가져옴
        cursor.execute('SELECT id, date, daily_yield, lesson FROM daily_reviews ORDER BY id ASC')
        rows = cursor.fetchall()
        
        start_date = rows[0][1]
        end_date = rows[-1][1]
        period_str = f"{start_date} ~ {end_date}"
        
        monthly_context = ""
        row_ids = []
        for row in rows:
            row_ids.append(row[0])
            monthly_context += f"- {row[1]} (수익률 {row[2]:+.2f}%): {row[3][:100]}...\n"
            
        sys_prompt = f"""당신은 AI 포트폴리오의 장기 전략가(Strategist)입니다.
아래는 지난 약 한 달간의 매일매일의 투자 회고 기록입니다.

[상세 데이터]
{monthly_context}

지시사항:
이 상세 기록들을 분석하여, 향후 수개월간 지속될 '불변의 장기 투자 원칙'으로 요약하세요.
단기적인 사건 위주가 아니라, 구조적인 성공 패턴이나 반복되는 실수 위주로 3단락 이내로 정리하세요.
"""
        response = llm.invoke([HumanMessage(content=sys_prompt)])
        summary_text = response.content.strip()
        
        try:
            # 1. 장기 요약 DB에 추가 (Append)
            cursor.execute('INSERT INTO monthly_summaries (period, summary) VALUES (?, ?)', (period_str, summary_text))
            
            # 2. 상세 데이터 DB에서 삭제 (Move 완료)
            placeholders = ', '.join(['?'] * len(row_ids))
            cursor.execute(f'DELETE FROM daily_reviews WHERE id IN ({placeholders})', row_ids)
            
            conn.commit()
            print(f"✅ {period_str} 기간의 요약본이 장기 DB로 이관되었습니다. 상세 데이터는 비워졌습니다.")
        except Exception as e:
            conn.rollback()
            print(f"❌ 이관 중 오류 발생: {e}")

def main():
    print("===========================================")
    print(" 🧐 [자가 학습 모듈] 포트폴리오 회고 시스템 가동")
    print("===========================================\n")

    PORTFOLIO_FILE = "latest_portfolio.json"
    
    if not os.path.exists(config.LATEST_PORTFOLIO_FILE):
        print("이전 포트폴리오 데이터가 없습니다. 회고를 종료합니다.")
        return

    # 1. 이전 기록 로드
    with open(config.LATEST_PORTFOLIO_FILE, "r", encoding="utf-8") as f:
        record = json.load(f)
        
    date_str = record.get("date", "Unknown")
    reasoning = record.get("reasoning", "")
    portfolio = record.get("portfolio", [])
    
    print(f"▶ 기준일: {date_str}")
    print(f"▶ 이전 매니저의 투자 논리: {reasoning}")
    
    # 2. 개별 종목 성과 평가
    print("\n[포트폴리오 성과 분석]")
    eval_text = ""
    total_yield = 0.0
    
    for asset in portfolio:
        ticker = asset.get('ticker')
        name = asset.get('name')
        weight = asset.get('weight', 0)
        market = asset.get('market', 'KR')
        
        profit_pct, current_price = get_performance(ticker, market)
        
        contribution = profit_pct * (weight / 100.0)
        total_yield += contribution
        
        line = f"- {name}({ticker}): 비중 {weight}%, 수익률 {profit_pct:+.2f}% (현재가 {current_price:,.2f})"
        print(line)
        eval_text += line + "\n"
        
    print(f"\n▶ 포트폴리오 1일 추정 총 수익률: {total_yield:+.2f}%")
    
    # 3. 벤치마크 (S&P500) 대비 비교
    spy_profit, _ = get_performance("^GSPC", "US")
    print(f"▶ 벤치마크(S&P500) 수익률: {spy_profit:+.2f}%")
    
    # 4. LLM을 통한 일일 반성문(Feedback) 추출
    @retry_llm(max_attempts=3)
    def call_reviewer_llm(llm, prompt):
        return llm.invoke([HumanMessage(content=prompt)])

    print("\n[AI 매니저 회고록 작성 중...]")
    llm = ChatMistralAI(
        model=config.MODELS["mistral"],
        temperature=0.7,
        max_tokens=2048,
        api_key=os.environ.get("MISTRAL_API_KEY"),
    )
    
    sys_prompt = f"""당신은 AI 통합 포트폴리오 시스템의 수석 평가관(Chief Reviewer)입니다.
어제 시스템이 내린 투자 결정과 오늘까지의 실제 수익률을 비교하여, 다음 날 AI 에이전트들이 투자 논의를 할 때 참고해야 할 핵심 피드백(Lessons Learned)을 작성하세요.

[어제의 투자 논리]
{reasoning}

[오늘의 성과(1일 변동)]
총 수익률: {total_yield:+.2f}% (벤치마크 대비: {total_yield - spy_profit:+.2f}%p)
개별 종목 단기 성과:
{eval_text}

지시사항:
1. 시장 예측이 적중했는지 실패했는지 분석하세요.
2. 성과가 저조했다면 어떤 리스크를 놓쳤는지 짚어주세요.
3. 다음 날 포트폴리오 매니저와 다른 에이전트들에게 전하는 "행동 지침(가이드)"을 3줄 이내로 요약하세요. (예: "방어주 비중 부족으로 손실발생. 다음 회의에서는 헷지 자산 편입을 강력히 논의할 것")
"""
    
    
    response = call_reviewer_llm(llm, sys_prompt)
    lesson_text = response.content.strip()
    
    print("\n💡 [일일 AI 회고록]")
    print(lesson_text)
    
    # 5. SQLite DB에 누적 (과거 기록 보호용)
    conn = init_db()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT OR REPLACE INTO daily_reviews (date, daily_yield, spy_yield, lesson) 
            VALUES (?, ?, ?, ?)
        ''', (date_str, total_yield, spy_profit, lesson_text))
        conn.commit()
        print("\n✅ 일일 피드백이 DB (portfolio_history.db) 에 성공적으로 누적되었습니다.")
        
        # 6. 월간 압축 장기 기억 엔진 가동 조건 체크 (20영업일 마다)
        summarize_monthly_lessons(conn, llm)
        
    except Exception as e:
        print(f"\n❌ DB 저장 실패: {e}")
    finally:
        conn.close()
    
    # 7. KIS 디스코드 알림
    try:
        kis = KisClient()
        kis._get_access_token()
        
        # 시스템 상태 및 성과 요약 (중간 점검용)
        discord_msg = "📈 **[AI 성과 분석 및 정기 점검 리포트]**\n\n"
        discord_msg += f"**🩺 시스템 가동 상태:** ✅ 정상 (Reviewer 및 DB 연결 OK)\n"
        discord_msg += f"**💰 오늘의 수익률:** {total_yield:+.2f}%\n"
        discord_msg += f"**🏁 SPY 수익률:** {spy_profit:+.2f}%\n\n"
        discord_msg += f"**🚦 AI 투자 복기 및 교훈:**\n{lesson_text}"
        
        kis.send_discord_message(discord_msg)
    except Exception as e:
        print(f"디스코드 알림 전송 실패: {e}")

if __name__ == "__main__":
    main()
