import time
import logging
from functools import wraps
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import httpx

logger = logging.getLogger(__name__)

def retry_llm(max_attempts=3):
    """
    LLM API 호출을 위한 재시도 데코레이터.
    429(Rate Limit), 500, 502, 503, 504 에러 시 지수 백오프로 재시도함.
    """
    def decorator(func):
        @wraps(func)
        @retry(
            stop=stop_after_attempt(max_attempts),
            wait=wait_exponential(multiplier=1, min=4, max=10),
            retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.RequestError, Exception)),
            before_sleep=lambda retry_state: logger.warning(
                f"⚠️ API 호출 실패 ({retry_state.attempt_number}/{max_attempts}). {retry_state.outcome.exception()} - 재시도 중..."
            )
        )
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        return wrapper
    return decorator
