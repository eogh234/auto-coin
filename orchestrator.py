import os
import sys
import json
import datetime
import logging
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage

# 공통 로깅 모듈 (최상단에서 초기화)
sys.path.insert(0, "/Users/Daeho/Projects")
from shared.structured_logger import setup_logger
setup_logger("multi-agent-investor")

# Import project config and modules
import config
from agents import app as agent_workflow
from agents import AgentState
from data_pipeline import get_market_data
from kis_client import KisClient
from upbit_client import UpbitClient
from executor import execute_portfolio, execute_crypto, get_current_portfolio_str
from utils import retry_llm
import reviewer  # 조치 2: 일일 성과 리뷰 & DB 저장 자동화

load_dotenv()

logger = logging.getLogger(__name__)

# 마스터 에이전트용 LLM (고성능 모델 사용)
llm_master = ChatGroq(
    model=config.MODELS["high"],
    temperature=0.1,
    max_tokens=2048,
    api_key=os.environ.get("GROQ_API_KEY"),
)

class ProjectOrchestrator:
    """
    프로젝트의 최종 책임자 역할을 수행하는 마스터 에이전트.
    시스템 감시, 전략 승인, 비상 정지 및 조율을 담당합니다.
    """
    def __init__(self):
        self.kis = KisClient()
        self.uc = UpbitClient()
        self.kis._get_access_token()
        
    def check_system_health(self):
        """시스템 구성 요소의 상태를 점검합니다."""
        logger.info("시스템 헬스 체크 시작...")
        
        # 1. 파일 점검
        if not os.path.exists(config.KIS_TOKEN_FILE):
             logger.warning("KIS 토큰 파일이 없습니다. 새로 발급이 필요할 수 있습니다.")
             
        # 2. LLM API 연결 점검 (Pre-flight Check)
        try:
            logger.info("LLM API 연결 점검 중 (Pre-flight Check)...")
            llm_master.invoke([HumanMessage(content="ping")])
            logger.info("✅ LLM API 연결 정상")
        except Exception as e:
            logger.error(f"❌ LLM API 연결 실패: {e}")
            return False
            
        return True

    @retry_llm(max_attempts=config.MAX_RETRIES)
    def master_review(self, final_state: dict, portfolio_decision: dict):
        """
        포트폴리오 매니저의 결정을 프로젝트 원칙에 따라 최종 검토합니다. (Veto 권한)
        """
        logger.info("마스터 에이전트 최종 검토 중...")
        
        principles = """
        [Antigravity 프로젝트 투자 원칙]
        1. 무거운 엉덩이: 펀더멘털이 유효한 우량주는 잦은 매매를 지양하고 Hold한다.
        2. 글로벌 분산: 한국, 미국, 가상자산의 균형을 유지한다. 무리한 집중 투자를 경고한다.
        3. 리스크 우선: 리스크 관리자의 경고가 무시되지 않았는지 확인한다.
        4. 데이터 기반: 모든 결정의 reasoning이 논리적이고 데이터에 기반해야 한다.
        """
        
        review_prompt = f"""당신은 이 투자 프로젝트의 최종 책임자이자 마스터 오케스트레이터입니다.
아래의 투자 원칙과 에이전트들의 분석 결과를 바탕으로, 포트폴리오 매니저가 내린 최종 결정을 승인할지 결정하세요.

{principles}

[분석 하이라이트]
- 거시뷰: {final_state.get('macro_view', '없음')}
- 리스크뷰: {final_state.get('risk_view', '없음')}

[최종 결정안]
{json.dumps(portfolio_decision, ensure_ascii=False, indent=2)}

지시사항:
결정이 원칙에 부합한다면 'APPROVED'로 시작하고, 반려해야 한다면 'REJECTED'로 시작하세요. 
최종 출력 마지막 줄에 반드시 'STATUS: APPROVED' 또는 'STATUS: REJECTED'를 포함하세요."""

        response = llm_master.invoke([HumanMessage(content=review_prompt)])
        return response.content

    def run_daily_cycle(self):
        """전체 인베스트먼트 라이프사이클을 실행합니다."""
        print("\n" + "="*50)
        print(" 🚀 Antigravity Orchestrator 가동 시작")
        print("="*50)

        try:
            if not self.check_system_health():
                self.kis.send_discord_message("🚨 **[오케스트레이터 알림]** 시스템 불완전 상태. 중단합니다.")
                return

            # 1. 데이터 수집
            logger.info("시장 데이터 및 잔고 정보 수집 중...")
            market_data = get_market_data()
            current_portfolio_summary = get_current_portfolio_str(self.kis, self.uc)
            print(f"✅ 데이터 수집 완료. 현재 잔고 파악 완료.\n")
            
            # 2. 멀티 에이전트 토론 실행
            logger.info("멀티 에이전트 그래프 토론 실행...")
            initial_state = AgentState(
                messages=[],
                current_portfolio=current_portfolio_summary,
                market_data=market_data,
                news_view="", macro_view="", sector_view="", quant_view="", risk_view="", final_decision=""
            )
            
            final_state = {}
            for output in agent_workflow.stream(initial_state):
                for key, value in output.items():
                    print(f"  👉 [{key.split('_')[0].upper()}] 분석 완료")
                    final_state = value
            
            # 3. 결정안 파싱
            decision_raw = final_state.get('final_decision', '{}')
            if "```json" in decision_raw:
                decision_raw = decision_raw.split("```json\n")[1].split("\n```")[0]
            elif "```" in decision_raw:
                decision_raw = decision_raw.replace("```", "")
            decision_json = json.loads(decision_raw)

            # 4. 마스터 에이전트 최종 검토
            master_report = self.master_review(final_state, decision_json)
            is_approved = "STATUS: APPROVED" in master_report.upper()
            
            # 5. 실행 및 저장
            portfolio_record = {
                "date": datetime.datetime.now().strftime("%Y-%m-%d"),
                "reasoning": decision_json.get("reasoning", ""),
                "portfolio": decision_json.get("stock_portfolio", []) + decision_json.get("crypto_portfolio", []),
                "master_status": "APPROVED" if is_approved else "REJECTED"
            }
            
            with open(config.LATEST_PORTFOLIO_FILE, "w", encoding="utf-8") as f:
                json.dump(portfolio_record, f, ensure_ascii=False, indent=4)
            logger.info(f"결과 저장 완료: {config.LATEST_PORTFOLIO_FILE}")

            if is_approved:
                print("\n✅ 마스터 승인 완료. 주문 실행 중...")
                # 한국 주식 / 코인 실행
                kr_portfolio = [a for a in decision_json.get("stock_portfolio", []) if a.get('market') == 'KR']
                if kr_portfolio:
                    execute_portfolio(self.kis, kr_portfolio)
                
                crypto_portfolio = decision_json.get("crypto_portfolio", [])
                if crypto_portfolio:
                    execute_crypto(crypto_portfolio)
                
                self.send_final_report(final_state, decision_json, master_report, "APPROVED")
                try:
                    import subprocess
                    subprocess.run(
                        ["python", "asset_manager.py", "--reason", "국내 자산 리밸런싱 완료 보고"],
                        cwd=config.BASE_DIR,
                        capture_output=True,
                        text=True
                    )
                except Exception as w_e:
                    logger.error(f"자산운용가 완료 보고 실행 실패: {w_e}")
            else:
                print("\n🛑 마스터 반려됨. 매매 보류.")
                self.send_final_report(final_state, decision_json, master_report, "REJECTED")
                try:
                    import subprocess
                    subprocess.run(
                        ["python", "asset_manager.py", "--reason", "국내 자산 매매 보류 현황 보고"],
                        cwd=config.BASE_DIR,
                        capture_output=True,
                        text=True
                    )
                except Exception as w_e:
                    logger.error(f"자산운용가 현황 보고 실행 실패: {w_e}")

        except Exception as e:
            msg = f"오케스트레이터 루프 오류: {e}"
            logger.error(msg)
            self.kis.send_discord_message(f"🚨 **[오케스트레이터 치명적 에러]**\n{e}")

        # ── 조치 2: 매 사이클 마지막 — 전날 포트폴리오 성과 리뷰 & DB 저장 ──
        try:
            logger.info("📊 포트폴리오 리뷰 & 성과 DB 저장 시작 (reviewer.main)...")
            reviewer.main()
            logger.info("✅ 리뷰 & DB 저장 완료")
        except Exception as e:
            logger.warning(f"⚠️ reviewer.main() 실행 중 오류 (메인 사이클 유지): {e}")

    def send_final_report(self, state, decision, master_report, status):
        """최종 리포트 발송"""
        header = "🛡️ **[데일리 투자 오케스트레이션 - 승인]**" if status == "APPROVED" else "⚠️ **[데일리 투자 오케스트레이션 - 반려]**"
        
        discord_msg = f"{header}\n\n"
        discord_msg += f"**👨‍✈️ 마스터 한줄평:**\n{master_report.split('STATUS:')[0].strip()}\n\n"
        discord_msg += f"**📝 요약:** {decision.get('reasoning', '정보 없음')}\n"
        
        if status == "APPROVED":
            discord_msg += "\n**📊 최종 포트폴리오**\n"
            for asset in decision.get('stock_portfolio', []) + decision.get('crypto_portfolio', []):
                discord_msg += f"- {asset['name']}: {asset['weight']}%\n"
        
        self.kis.send_discord_message(discord_msg)

if __name__ == "__main__":
    ProjectOrchestrator().run_daily_cycle()
