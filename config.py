import os

# ============================================================
# 경로 설정 (Path Configuration)
# ============================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 데이터 파일
LATEST_PORTFOLIO_FILE = os.path.join(BASE_DIR, "latest_portfolio.json")
DB_FILE = os.path.join(BASE_DIR, "portfolio_history.db")
KIS_TOKEN_FILE = os.path.join(BASE_DIR, ".kis_token.json")

# 로그 파일 (레거시 - shared structured_logger로 대체됨)
EXECUTION_LOG = os.path.join(BASE_DIR, "execution_log.txt")

# ============================================================
# 에이전트 및 모델 설정 (LLM Configuration)
# ============================================================
MODELS = {
    "high": "llama-3.3-70b-versatile",    # 마스터, 매크로, 포트폴리오 매니저
    "mid": "llama-3.3-70b-versatile",     # 섹터, 리스크
    "fast": "llama-3.1-8b-instant",       # 퀀트, 뉴스
    "mistral": "mistral-small-latest"     # 리뷰어
}

# 재시도 설정
MAX_RETRIES = 3
RETRY_MIN_WAIT = 4
RETRY_MAX_WAIT = 10

# ============================================================
# 투자 마켓 및 시간 설정
# ============================================================
KR_MARKET_OPEN = (9, 0)
KR_MARKET_CLOSE = (15, 30)
US_EXECUTION_TIME = "23:20"

# 업비트 매수 성공 판단 최소 금액 (원)
UPBIT_MIN_KRW = 5500
