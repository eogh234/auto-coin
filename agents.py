import os
import time
import sqlite3
from typing import TypedDict, Annotated, List
from langchain_groq import ChatGroq
from langchain_core.messages import BaseMessage, HumanMessage
from langgraph.graph import StateGraph, END
import operator
from dotenv import load_dotenv
from utils import retry_llm
import config

load_dotenv()

# ============================================================
# State 정의 (에이전트들이 공유하는 메모리)
# ============================================================
class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], operator.add]
    current_portfolio: str # 현재 보유 중인 잔고 상태
    market_data: str      # 수집된 시장 데이터 요약 (Raw)
    news_view: str        # 뉴스 애널리스트 요약 리포트 (NEW)
    macro_view: str       # 거시경제학자 의견
    sector_view: str      # 섹터 애널리스트 의견
    quant_view: str       # 퀀트 분석가 의견
    risk_view: str        # 리스크 관리자 의견
    final_decision: str   # 포트폴리오 매니저의 최종 결정 (JSON)

# ============================================================
# ============================================================
# 에이전트별 전용 LLM 설정 (Groq 최신 모델 라인업 분산)
# ============================================================

# 0. 뉴스 애널리스트 (초고속 텍스트 요약) → Groq Compound Mini
llm_news = ChatGroq(
    model=config.MODELS["fast"],
    temperature=0.2,
    max_tokens=1500,
    api_key=os.environ.get("GROQ_API_KEY"),
)

# 1. 거시경제학자 - 깊은 추론 필요 → GPT-OSS 120B
llm_macro = ChatGroq(
    model=config.MODELS["high"],
    temperature=0.2,
    max_tokens=2048,
    api_key=os.environ.get("GROQ_API_KEY"),
)

# 2. 섹터 애널리스트 - 트렌드 분석 → GPT-OSS 20B
llm_sector = ChatGroq(
    model=config.MODELS["mid"],
    temperature=0.3,
    max_tokens=1024,
    api_key=os.environ.get("GROQ_API_KEY"),
)

# 3. 퀀트 분석가 - 수치/추론 특화 → Qwen 3.6 27B
llm_quant = ChatGroq(
    model=config.MODELS["quant"],
    temperature=0.1,
    max_tokens=1024,
    api_key=os.environ.get("GROQ_API_KEY"),
)

# 4. 리스크 관리자 - 보수적 검토 및 헷지 → Qwen 3.6 27B
llm_risk = ChatGroq(
    model=config.MODELS["quant"],
    temperature=0.2,
    max_tokens=1024,
    api_key=os.environ.get("GROQ_API_KEY"),
)

# 5. 포트폴리오 매니저 - JSON 구조화 출력 및 종합 판단 → GPT-OSS 120B
llm_portfolio = ChatGroq(
    model=config.MODELS["high"],
    temperature=0.1,
    max_tokens=2048,
    api_key=os.environ.get("GROQ_API_KEY"),
)

# ============================================================
# 헬퍼 함수
# ============================================================
def load_lessons():
    """자가 학습: 장기 펀더멘털 지혜(DB 요약)와 현재 누적 중인 단기 리뷰(DB 상세)를 모두 로드"""
    lessons_combined = ""
    
    if os.path.exists(config.DB_FILE):
        try:
            conn = sqlite3.connect(config.DB_FILE)
            cursor = conn.cursor()
            
            # 1. 장기 전역 원칙 (Monthly Summaries) 로드
            lessons_combined += "### [장기 불변 투자 원칙 (Long-term Wisdom Accumulation)]\n"
            cursor.execute('SELECT period, summary FROM monthly_summaries ORDER BY id ASC')
            summaries = cursor.fetchall()
            if summaries:
                for row in summaries:
                    lessons_combined += f"#### 기간: {row[0]}\n{row[1]}\n\n"
            else:
                # DB는 있으나 요약본이 아직 없는 경우, 기존에 혹시 있을지 모를 파일 백업 확인 (하위 호환)
                if os.path.exists("long_term_lessons.txt"):
                    with open("long_term_lessons.txt", "r", encoding="utf-8") as f:
                        lessons_combined += f.read() + "\n\n"
                else:
                    lessons_combined += "아직 누적된 장기 원칙이 없습니다.\n\n"
            
            # 2. 이번 달 단기 리뷰 — 최근 5일만 에이전트에게 전달 (토큰 절약 + 최신성 유지)
            # 오래된 리뷰는 monthly_summaries에 이미 압축됨
            lessons_combined += "### [최근 단기 상세 리뷰 (Recent 5 Days)]\n"
            cursor.execute('SELECT date, lesson FROM daily_reviews ORDER BY id DESC LIMIT 5')
            details = cursor.fetchall()
            details = list(reversed(details))  # 날짜 오름차순으로 다시 정렬
            if details:
                for row in details:
                    lessons_combined += f"- {row[0]}: {row[1]}\n"
            else:
                lessons_combined += "이번 달 상세 이력이 아직 없습니다.\n"
                
            conn.close()
        except Exception as e:
             lessons_combined += f"DB 조회 중 오류 발생: {e}\n"
    else:
        lessons_combined += "아직 투자 이력 데이터베이스가 구축되지 않았습니다.\n"
        
    return lessons_combined

# ============================================================
# 에이전트 노드 정의
# ============================================================

# 0. 뉴스/지정학 애널리스트 노드
@retry_llm(max_attempts=3)
def news_analyst_node(state: AgentState):
    print("🤖 [뉴스 애널리스트 | Llama-3.3-70B] 글로벌 뉴스 및 지정학 데이터 정제 중...")
    sys_prompt = """당신은 수많은 뉴스 헤드라인과 시장 데이터를 분석하여 핵심만 요약하는 수석 뉴스 애널리스트(Chief News Analyst)입니다.
거시경제(금리, 인플레이션 등), 지정학적 리스크(전쟁, 미중갈등, 선거 등), 시장/가상자산(코인, 증시 자금흐름)의 3가지 카테고리를 중심으로 
가장 중요한 이벤트와 그것이 오늘 투자 시장(주식 및 코인)에 미칠 잠재적 영향을 1페이지 요약 리포트로 작성하세요."""
    prompt = f"{sys_prompt}\n\n[오늘의 로우 데이터(Raw Data)]:\n{state.get('market_data', '데이터 없음')}"
    response = llm_news.invoke([HumanMessage(content=prompt)])
    print(f"  👉 [news_analyst] 요약 완료")
    time.sleep(7)  # 조치 3: Groq TPM Rate Limit 방지 딜레이
    return {"news_view": response.content}

# 1. 거시경제학자 노드 (Llama 3.3 70B)
@retry_llm(max_attempts=3)
def macroeconomist_node(state: AgentState):
    print("🤖 [거시 경제 학자 | Llama-3.3-70B] 글로벌 시황 분석 중...")
    lessons = load_lessons()
    sys_prompt = f"""당신은 월스트리트 최고 수준의 거시경제학자(Macroeconomist)입니다.
뉴스 애널리스트의 요약 리포트와 아래의 '과거 투자 회고록'을 가장 중요하게 종합 분석하십시오.
'단기 리뷰'의 노이즈에만 흔들리지 말고, '장기 펀더멘털 지혜'를 코어(Core)로 삼아 하이브리드 거시적 방향성을 제시하세요.

[과거 투자 회고록 (장기+단기)]
{lessons}

위 지침을 바탕으로 주식, 코인, 무위험자산(현금) 비중을 구체적으로 제안하세요."""
    prompt = f"{sys_prompt}\n\n[뉴스 애널리스트 시황 리포트]:\n{state.get('news_view', '데이터 없음')}"
    response = llm_macro.invoke([HumanMessage(content=prompt)])
    print(f"  👉 [macroeconomist] 분석 완료")
    time.sleep(7)  # 조치 3: Groq TPM Rate Limit 방지 딜레이
    return {"macro_view": response.content}

# 2. 섹터 애널리스트 노드 (Llama 3.3 70B)
@retry_llm(max_attempts=3)
def sector_analyst_node(state: AgentState):
    print("🤖 [섹터 애널리스트 | Llama-3.3-70B] 유망 섹터 발굴 중...")
    sys_prompt = """당신은 날카로운 통찰력을 가진 섹터 애널리스트(Sector Analyst)입니다.
거시경제학자의 뷰를 바탕으로, 현재 시장에서 가장 유망한 1~2개의 테마를 추천하세요.
대상 자산군에는 '주식(AI, 금융, 헬스케어 등)' 뿐만 아니라 '가상자산(Bitcoin, Ethereum 등 코인)'도 포함됩니다. 코인 시장이 유력하다면 가상자산 섹터도 적극 추천하세요.
추천 사유를 명확히 밝혀야 합니다."""
    prompt = f"{sys_prompt}\n\n[거시경제학자 뷰]:\n{state['macro_view']}"
    response = llm_sector.invoke([HumanMessage(content=prompt)])
    print(f"  👉 [sector_analyst] 분석 완료")
    time.sleep(7)  # 조치 3: Groq TPM Rate Limit 방지 딜레이
    return {"sector_view": response.content}

# 3. 퀀트 분석가 노드 (Qwen3-32B)
@retry_llm(max_attempts=3)
def quant_analyst_node(state: AgentState):
    print("🤖 [퀀트 분석가 | Qwen3-32B] 최적의 종목 산출 중...")
    lessons = load_lessons()
    sys_prompt = f"""당신은 펀더멘털(Core)과 모멘텀(Satellite)을 조율하는 하이브리드 퀀트 분석가(Quant Analyst)입니다.
아래의 '과거 투자 회고록'을 주의 깊게 분석하여, 과거에 성공을 가져왔던 종목/섹터 패턴(예: AI/반도체 테마, 거시 환경에 따른 종목 조정 등)은 적극 검토하고, 실패의 원인이 되었던 종목 선정 리스크(테마주 과도한 편입, 바이오/헬스케어의 과도한 변동성 등)는 피해가며 최적의 종목을 선정하십시오.

[과거 투자 회고록 (장기+단기 피드백)]
{lessons}

섹터 애널리스트가 추천한 테마를 반영하되, 장기적으로 우상향하는 '코어 자산'과 단기 뉴스를 타는 '위성 자산'을 구별하여 구체적인 종목(한국/미국/코인 1~4개)을 선정하세요.
현재 우리가 보유 중인 포트폴리오 상태도 함께 고려하여, 펀더멘털이 훼손되지 않은 코어 자산은 비중을 유지(Hold)하고, 단기 시기성이 끝난 자산은 매도(Sell)할지 명확히 판단하세요.
⚠️ [매우 중요 1]: 주식 종목코드(티커)는 한국의 경우 6자리 숫자, 미국의 경우 영문 티커 심볼을 사용하세요. 코인은 KRW- 로 시작하는 업비트 티커를 사용하세요.
⚠️ [매우 중요 1-세부 — 자주 틀리는 코드 주의]:
  - 대웅제약 정확 코드: 069620 (019170은 신풍제약이므로 절대 사용 금지)
  - 삼성바이오로직스 정확 코드: 207940 (008730=율촌화학, 008930=삼성물산, 098370=에코마케팅 — 모두 사용 금지)
  - 069520은 상장된 ETF 코드가 아님 — 사용 금지
  - 주요 정확 코드: 삼성전자 005930, SK하이닉스 000660, KODEX200 069500, 셀트리온 068270
  - 미국: 애플 AAPL, 테슬라 TSLA, S&P500 IVV/VOO/SPY, 나스닥 QQQ
⚠️ [매우 중요 2]: 레버리지, 인버스, 고배당파생 등 '파생 ETF' 상품은 절대 추천 목록에 포함하지 마세요.
⚠️ [매우 중요 3]: 코인(KRW-XXX) 종목은 절대로 주식 추천 목록에 포함하지 마세요. 코인은 별도 분리된 가상자산 계좌에서 운용됩니다.
종목 이름과 정확한 종목코드를 반드시 함께 명시하며, 기술적 판단 근거(수급, 모멘텀 등)를 제시하세요."""
    prompt = f"{sys_prompt}\n\n[현재 포트폴리오 잔고]:\n{state.get('current_portfolio', '없음')}\n\n[섹터 애널리스트 뷰]:\n{state['sector_view']}"
    response = llm_quant.invoke([HumanMessage(content=prompt)])
    print(f"  👉 [quant_analyst] 분석 완료")
    time.sleep(7)  # 조치 3: Groq TPM Rate Limit 방지 딜레이
    return {"quant_view": response.content}

# 4. 리스크 관리자 노드 (Qwen 3.6 27B)
@retry_llm(max_attempts=3)
def risk_manager_node(state: AgentState):
    print("🤖 [리스크 관리자 | Qwen-3.6-27B] 포트폴리오 위험성 검토 중...")
    sys_prompt = """당신은 보수적인 리스크 관리자(Risk Manager)입니다.
앞선 3명의 의견을 모두 종합하여, 선정된 종목과 비중이 무리한 쏠림 투자는 아닌지, 
현재 시장의 변동성(VIX 등)을 고려할 때 헷지(Hedge) 수단 및 방어 자산(채권/골드/현금성 자산 비중 최소 15% 이상) 편입이 필요한지 비판적으로 검토하세요.
위험을 줄이기 위한 수정 의견을 명시하세요."""
    prompt = f"{sys_prompt}\n\n[거시뷰]:\n{state['macro_view']}\n\n[섹터뷰]:\n{state['sector_view']}\n\n[퀀트뷰]:\n{state['quant_view']}"
    response = llm_risk.invoke([HumanMessage(content=prompt)])
    print(f"  👉 [risk_manager] 검토 완료")
    time.sleep(7)  # 조치 3: Groq TPM Rate Limit 방지 딜레이
    return {"risk_view": response.content}

# 5. 포트폴리오 매니저 노드 (GPT-OSS 120B — JSON 출력)
@retry_llm(max_attempts=3)
def portfolio_manager_node(state: AgentState):
    print("🤖 [포트폴리오 매니저 | GPT-OSS 120B] 최종 목표 비중(%) 산출 중...")
    sys_prompt = """당신은 하이브리드 펀드 총괄 포트폴리오 매니저(Portfolio Manager)입니다.
모든 에이전트의(거시, 섹터, 퀀트, 리스크) 의견 및 현재 보유 중인 포트폴리오 잔고를 취합하여 최종 목표 종목(주식/코인)과 비중(%)을 결정하세요.
단, 데일리 트레이더처럼 매일 100% 종목을 전부 갈아치우는 행위를 엄격히 지양하십시오. 보유 중인 우량/코어 자산의 펀더멘털이 유효하다면 비중을 기존과 동일하게 '유지(Hold)'하여 트레이딩 비용을 아끼고, 과열/소외된 '단기 변동성' 테마 자산에만 선별적으로 전량 매도/비중 축소/매수를 부여하는 '무거운 엉덩이(장기 투자 중심)'를 기본 골격으로 삼으세요.
⚠️ [금지 사항 1]: 파생 ETF(레버리지, 인버스, 배당 등 증거금 제한이 있는 파생결합 ETF)는 무조건 배제하세요.
⚠️ [금지 사항 2]: 티커(종목코드)는 지어내지 마세요. (주식: 6자리 숫자, 코인: 업비트 형식 KRW-XXX).
⚠️ [금지 사항 3]: 현재 잔고에 있으나 가격 조회가 불가능한 종목(이화공영 001840, 골든센츄리 900280 등)은 거래정지 종목이므로 절대 목표 포트폴리오에 포함하지 마세요.
⚠️ [금지 사항 4 — 매우 중요]: 한국/미국 종목 코드를 절대 혼동하지 마세요.
  - 대웅제약 정확 코드: 069620 (019170은 신풍제약 — 대웅제약에 절대 사용 금지)
  - 삼성바이오로직스 정확 코드: 207940 (008730=율촌화학, 008930=삼성물산 — 사용 금지)
  - KODEX 200: 069500 / 삼성전자: 005930 / SK하이닉스: 000660 / 셀트리온: 068270
  - 069520은 상장 ETF 코드가 아님 — 사용 금지
⚠️ [균형 원칙]: 글로벌 분산을 위해 한국 주식만 편중하지 말고, 미국 주식(AAPL/MSFT/TSLA/SPY/QQQ 등)도 적극 검토하세요. 미국 주식은 execute_us.py가 야간에 자동 실행하므로 추천해도 됩니다.
⚠️ [방어/헷지 원칙 — 필수]: 하락장 방어 및 리스크 관리를 위해 현금, 채권형 자산/ETF(SPY, TLT, SGOV, KODEX 200 등) 또는 안전 헷지 자산의 비중을 포트폴리오 내 최소 15% 이상 배정하십시오.
⚠️ [배분 원칙]: 주식 계좌와 코인 계좌는 분리된 별도의 자산입니다. 주식 포트폴리오 weight 총합 = 반드시 100, 코인 포트폴리오 weight 총합 = 100 또는 0.

결과는 반드시 매매 시스템이 파싱할 수 있도록 아래 JSON 형식으로만 출력하세요. 설명은 필요 없습니다.
결과 포맷:
{
    "reasoning": "최종 결정에 대한 핵심 요약",
    "stock_portfolio": [
        {
            "ticker": "005930", 
            "name": "삼성전자", 
            "weight": 50,
            "market": "KR" 
        },
        {
            "ticker": "AAPL", 
            "name": "애플", 
            "weight": 50,
            "market": "NASD" # 달러 환전 없이 통합증거금으로 주문되므로, 한국주식과 합쳐 총합 100%. 시장구분: NASD, NYSE, AMEX, KR 중 택1.
        }
    ],
    "crypto_portfolio": [
        {
            "ticker": "KRW-BTC", 
            "name": "비트코인", 
            "weight": 50,
            "market": "CRYPTO" 
        },
        {
            "ticker": "KRW-ETH", 
            "name": "이더리움", 
            "weight": 50,
            "market": "CRYPTO" 
        }
    ]
}"""
    prompt = f"{sys_prompt}\n\n[현재 포트폴리오 잔고]:\n{state.get('current_portfolio', '없음')}\n\n[거시뷰]:\n{state['macro_view']}\n\n[섹터뷰]:\n{state['sector_view']}\n\n[퀀트뷰]:\n{state['quant_view']}\n\n[리스크뷰]:\n{state['risk_view']}"
    response = llm_portfolio.invoke([HumanMessage(content=prompt)])
    print(f"  👉 [portfolio_manager] 최종 결정 완료")
    time.sleep(10)  # Groq TPM Rate Limit 방지 딜레이
    return {"final_decision": response.content}

# ============================================================
# 그래프(워크플로우) 구성
# ============================================================
workflow = StateGraph(AgentState)

workflow.add_node("news_analyst", news_analyst_node)
workflow.add_node("macroeconomist", macroeconomist_node)
workflow.add_node("sector_analyst", sector_analyst_node)
workflow.add_node("quant_analyst", quant_analyst_node)
workflow.add_node("risk_manager", risk_manager_node)
workflow.add_node("portfolio_manager", portfolio_manager_node)

workflow.set_entry_point("news_analyst")
workflow.add_edge("news_analyst", "macroeconomist")
workflow.add_edge("macroeconomist", "sector_analyst")
workflow.add_edge("sector_analyst", "quant_analyst")
workflow.add_edge("quant_analyst", "risk_manager")
workflow.add_edge("risk_manager", "portfolio_manager")
workflow.add_edge("portfolio_manager", END)

app = workflow.compile()

if __name__ == "__main__":
    print("🏃‍♂️ 다중 에이전트 투자 회의를 시작합니다...\n")
    dummy_market_data = "현재 시장 요약: 1) 연준이 금리 인하를 시사했으나 인플레이션 지표가 혼조세. 2) 엔비디아 실적 호조로 AI 섹터 자금 유입 지속. 3) 중동 지정학적 리스크 잔존."
    initial_state = AgentState(
        messages=[],
        current_portfolio="가상 테스트용 데이터: 100% 현금",
        market_data=dummy_market_data,
        news_view="", macro_view="", sector_view="", quant_view="", risk_view="", final_decision=""
    )
    for output in app.stream(initial_state):
        for key, value in output.items():
            print(f"✅ [{key}] 노드 완료.")
    print("\n================ [최종 결정 내역] ================\n")
    print(value.get("final_decision", value))
