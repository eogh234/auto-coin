import yfinance as yf
import pandas as pd
import datetime

import feedparser

def get_news_headlines(query, num_articles=3):
    """Google News RSS를 활용해 실시간 뉴스 헤드라인을 가져옵니다."""
    url = f"https://news.google.com/rss/search?q={query}&hl=ko&gl=KR&ceid=KR:ko"
    try:
        feed = feedparser.parse(url)
        headlines = []
        for entry in feed.entries[:num_articles]:
            headlines.append(f"- {entry.title}")
        return "\n".join(headlines)
    except Exception as e:
        return f"뉴스 수집 실패: {e}"


def get_watchlist_data() -> str:
    """
    에이전트가 자주 추천하는 종목들의 실시간 시장 데이터를 조회.
    종목 선정 근거, 가격 수준, 모멘텀을 회의에서 참고할 수 있도록 제공.
    """
    # ── 확장 감시 유니버스 (미국주식 100% & 가상자산 전 범위) ──
    watchlist = {
        "US주식 (Big Tech & AI 반도체)": {
            "NVDA":  "Nvidia",
            "AAPL":  "Apple",
            "MSFT":  "Microsoft",
            "TSLA":  "Tesla",
            "AMZN":  "Amazon",
            "GOOGL": "Alphabet(Google)",
            "META":  "Meta",
            "AMD":   "AMD",
            "AVGO":  "Broadcom",
            "ARM":   "Arm Holdings",
        },
        "US주식 (지수 & 방어/채권 ETF)": {
            "SPY":   "S&P500 ETF",
            "QQQ":   "나스닥100 ETF",
            "SGOV":  "iShares 0-3M 단기채 ETF",
            "TLT":   "iShares 20+년 장기채 ETF",
            "GLD":   "SPDR Gold ETF",
            "COST":  "Costco",
            "BRK-B": "Berkshire Hathaway",
        },
        "가상자산 (yfinance & 업비트 연동)": {
            "BTC-USD": "Bitcoin",
            "ETH-USD": "Ethereum",
            "SOL-USD": "Solana",
            "XRP-USD": "Ripple",
            "DOGE-USD": "Dogecoin",
            "USDT-USD": "Tether",
        },
    }

    sections = []

    for category, tickers in watchlist.items():
        rows = []
        for ticker, name in tickers.items():
            try:
                # KR 주식은 .KS suffix
                yf_ticker = f"{ticker}.KS" if category == "KR주식" else ticker
                info = yf.Ticker(yf_ticker)
                hist = info.history(period="5d")
                if hist.empty:
                    continue

                cur   = hist['Close'].iloc[-1]
                prev  = hist['Close'].iloc[-2] if len(hist) >= 2 else cur
                chg   = (cur - prev) / prev * 100 if prev > 0 else 0
                high  = hist['High'].max()
                low   = hist['Low'].min()

                # 52주 고저 (별도 조회)
                try:
                    hist52 = info.history(period="52wk")
                    wk52_high = hist52['High'].max()
                    wk52_low  = hist52['Low'].min()
                    wk52_str  = f"52주: {wk52_low:.2f}~{wk52_high:.2f}"
                except Exception:
                    wk52_str = ""

                if category == "KR주식":
                    rows.append(
                        f"  {name}({ticker}): {cur:,.0f}원 ({chg:+.2f}%) | {wk52_str}"
                    )
                elif category == "US주식":
                    rows.append(
                        f"  {name}({ticker}): ${cur:.2f} ({chg:+.2f}%) | {wk52_str}"
                    )
                else:  # 코인
                    rows.append(
                        f"  {name}({ticker}): ${cur:,.2f} ({chg:+.2f}%) | {wk52_str}"
                    )
            except Exception:
                pass

        if rows:
            sections.append(f"[{category}]\n" + "\n".join(rows))

    if not sections:
        return "(종목 데이터 수집 실패)"
    return "\n\n".join(sections)


def get_market_data():
    print("📊 시장 및 뉴스 데이터 수집 시작...")
    
    # 1. 야후 파이낸스 글로벌 지수 및 모멘텀 (S&P500, 나스닥, 달러인덱스, 미 국채 10년물)
    tickers_to_fetch = {
        "^GSPC":    "S&P 500",
        "^IXIC":    "NASDAQ",
        "DX-Y.NYB": "달러 인덱스",
        "^TNX":     "미 국채 10년물 금리",
        "^VIX":     "VIX (변동성 지수)",
        "KRW=X":    "원/달러 환율"
    }

    market_summary = []
    
    for ticker, name in tickers_to_fetch.items():
        try:
            data = yf.Ticker(ticker).history(period="5d")
            if not data.empty:
                last_price = data['Close'].iloc[-1]
                prev_price = data['Close'].iloc[-2]
                pct_change = ((last_price - prev_price) / prev_price) * 100
                market_summary.append(
                    f"- {name} ({ticker}): 현재 {last_price:.2f} (전일대비 {pct_change:+.2f}%)"
                )
        except Exception as e:
            print(f"  [-] {ticker} 가격 데이터 수집 실패: {e}")

    # 2. 실시간 주요 뉴스 헤드라인 수집
    macro_query  = "금리+OR+인플레이션+OR+고용+OR+경기+OR+통화+OR+변동성+OR+유동성"
    geo_query    = "전쟁+OR+에너지+OR+공급망+OR+중국+OR+미국"
    market_query = "주식+OR+채권+OR+시장+OR+자금흐름+OR+비트코인+OR+규제"
    macro_news   = get_news_headlines(macro_query, 5)
    geo_news     = get_news_headlines(geo_query, 5)
    market_news  = get_news_headlines(market_query, 5)

    # 3. 추천 가능 주요 종목 실시간 데이터
    print("  📈 주요 종목 실시간 데이터 수집 중...")
    watchlist_data = get_watchlist_data()

    # 4. 결과 텍스트 조합
    today_str = datetime.datetime.now().strftime("%Y-%m-%d")
    
    report  = f"[{today_str} 기준 주요 마켓 지표 및 실시간 뉴스]\n\n"

    report += "[1. 마켓 지표 (글로벌/거시)]\n"
    report += "\n".join(market_summary) + "\n\n"

    report += "[2. 거시경제 뉴스 헤드라인 (Macro)]\n"
    report += macro_news + "\n\n"

    report += "[3. 국제 정세 및 공급망 뉴스 헤드라인 (Geopolitics)]\n"
    report += geo_news + "\n\n"

    report += "[4. 증시 및 가상자산 뉴스 헤드라인 (Markets & Crypto)]\n"
    report += market_news + "\n\n"

    report += "[5. 주요 투자 가능 종목 실시간 현황 (KR/US/코인)]\n"
    report += watchlist_data + "\n\n"

    report += "(참고: 위 지표·뉴스·종목 현황을 바탕으로 오늘의 포트폴리오를 결정하세요.)"
    
    return report

if __name__ == "__main__":
    data = get_market_data()
    print("\n--- 수집 완료 ---\n")
    print(data)

