import os
import logging
from logging.handlers import RotatingFileHandler

# ============================================================
# 경로 설정 (Path Configuration)
# ============================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 데이터 파일
LATEST_PORTFOLIO_FILE = os.path.join(BASE_DIR, "latest_portfolio.json")
DB_FILE = os.path.join(BASE_DIR, "portfolio_history.db")
KIS_TOKEN_FILE = os.path.join(BASE_DIR, ".kis_token.json")

# 로그 파일 설정
EXECUTION_LOG = os.path.join(BASE_DIR, "execution_log.txt")
CRYPTO_LOG = os.path.join(BASE_DIR, "crypto_monitor.log")

def get_rotating_handler(log_filepath: str, max_bytes: int = 10 * 1024 * 1024, backup_count: int = 5) -> RotatingFileHandler:
    """로그 파일 10MB 자동 로테이션 핸들러 반환"""
    handler = RotatingFileHandler(
        log_filepath, maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8"
    )
    formatter = logging.Formatter(
        "%(asctime)s - [%(name)s] - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    handler.setFormatter(formatter)
    return handler

# ============================================================
# 에이전트 및 모델 설정 (LLM Configuration - Groq Rate Limit 분산 배치)
# ============================================================
MODELS = {
    "high": "openai/gpt-oss-120b",        # 마스터, 매크로, 포트폴리오 매니저 (최고 성능 추론)
    "quant": "qwen/qwen3.6-27b",          # 퀀트 분석가, 리스크 관리자 (수치/논리/추론 특화)
    "mid": "openai/gpt-oss-20b",          # 섹터 애널리스트 (트렌드 분석 및 속도 분산)
    "fast": "groq/compound-mini",         # 뉴스 애널리스트 (초고속 요약, RPD 방어)
    "mistral": "mistral-small-latest"     # 수석 리뷰어 (Mistral API 독립 쿼타)
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
