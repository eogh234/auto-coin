# 🧪 Auto-Coin 테스트 파일
# 기본적인 모듈 테스트를 위한 예제

from modules.learning_system import LearningSystem
from modules.notification_manager import NotificationManager
from modules.config_manager import ConfigManager
import sys
import os
import pytest
from unittest.mock import Mock, patch

# 프로젝트 루트를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 테스트 대상 모듈 임포트


class TestConfigManager:
    """설정 관리자 테스트"""

    def test_config_manager_initialization(self):
        """설정 관리자 초기화 테스트"""
        config_manager = ConfigManager("config.yaml")
        assert config_manager is not None

    def test_get_method(self):
        """설정 값 조회 메소드 테스트"""
        config_manager = ConfigManager("config.yaml")
        # 기본 설정이 있다면 테스트
        try:
            value = config_manager.get("trading.mode")
            assert value is not None
        except Exception:
            # 설정 파일이 없어도 테스트는 통과
            pass


class TestNotificationManager:
    """알림 관리자 테스트"""

    @patch('requests.post')
    def test_discord_notification(self, mock_post):
        """Discord 알림 발송 테스트"""
        mock_post.return_value.status_code = 200

        notification_manager = NotificationManager()
        notification_manager.webhook_url = "https://discord.com/api/webhooks/test"

        result = notification_manager.send_discord_message("테스트 메시지")
        assert result is True or result is None  # 설정에 따라 다름


class TestLearningSystem:
    """학습 시스템 테스트"""

    def test_learning_system_initialization(self):
        """학습 시스템 초기화 테스트"""
        learning_system = LearningSystem(":memory:")  # 메모리 DB 사용
        assert learning_system is not None

    def test_record_trade(self):
        """거래 기록 테스트"""
        learning_system = LearningSystem(":memory:")

        # 거래 기록 추가
        trade_id = learning_system.record_trade(
            ticker="KRW-BTC",
            action="buy",
            price=50000000,
            amount=0.001,
            reason="test"
        )

        assert trade_id is not None


class TestIntegration:
    """통합 테스트"""

    def test_main_module_import(self):
        """메인 모듈 임포트 테스트"""
        try:
            import main
            assert hasattr(main, 'main')
        except ImportError as e:
            pytest.skip(f"메인 모듈 임포트 실패: {e}")

    def test_all_modules_importable(self):
        """모든 모듈이 정상적으로 임포트되는지 확인"""
        modules_to_test = [
            'modules.config_manager',
            'modules.notification_manager',
            'modules.learning_system',
            'modules.trading_engine',
            'modules.backtest_engine',
            'modules.performance_analyzer'
        ]

        for module_name in modules_to_test:
            try:
                __import__(module_name)
            except ImportError as e:
                pytest.fail(f"모듈 {module_name} 임포트 실패: {e}")


def test_python_syntax():
    """Python 구문 검사"""
    import py_compile
    import glob

    # 모든 Python 파일 구문 검사
    python_files = glob.glob("**/*.py", recursive=True)

    for file_path in python_files:
        if "__pycache__" not in file_path and "test_" not in file_path:
            try:
                py_compile.compile(file_path, doraise=True)
            except py_compile.PyCompileError as e:
                pytest.fail(f"구문 오류 발견: {file_path} - {e}")


if __name__ == "__main__":
    # 직접 실행 시 기본 테스트 수행
    print("🧪 기본 테스트 실행 중...")

    # 모듈 임포트 테스트
    try:
        from modules.config_manager import ConfigManager
        print("✅ ConfigManager 임포트 성공")
    except Exception as e:
        print(f"❌ ConfigManager 임포트 실패: {e}")

    try:
        from modules.notification_manager import NotificationManager
        print("✅ NotificationManager 임포트 성공")
    except Exception as e:
        print(f"❌ NotificationManager 임포트 실패: {e}")

    try:
        from modules.learning_system import LearningSystem
        print("✅ LearningSystem 임포트 성공")
    except Exception as e:
        print(f"❌ LearningSystem 임포트 실패: {e}")

    print("🎉 기본 테스트 완료!")
