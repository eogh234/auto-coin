"""
설정 관리 모듈
"""

import yaml
import logging


class ConfigManager:
    """설정 관리 클래스 - 모든 설정을 중앙에서 관리"""

    def __init__(self, config_path: str = "config.yaml"):
        self.config_path = config_path
        self.config = {}
        self.load_config()

    def load_config(self):
        """설정 파일 로드"""
        try:
            with open(self.config_path, 'r', encoding='UTF-8') as f:
                self.config = yaml.safe_load(f)
            logging.info(f"설정 로드 완료: {self.config_path}")
        except Exception as e:
            logging.error(f"설정 로드 실패: {e}")
            self._create_default_config()

    def _create_default_config(self):
        """기본 설정 파일 생성"""
        default_config = {
            'upbit': {
                'access_key': '',
                'secret_key': ''
            },
            'discord': {
                'webhook_url': '',
                'notification_cooldown': 300,
                'status_report_interval': 1800,
                'daily_report_time': '09:00'
            },
            'trading': {
                'max_daily_trades': 50,
                'max_hourly_trades': 5,
                'daily_loss_limit': 0.05,
                'investment_ratio': 0.1,
                'min_krw_balance': 50000
            },
            'learning': {
                'learning_interval_hours': 1,
                'memory_threshold': 0.85,
                'archive_days': 30,
                'min_trades_for_learning': 10
            }
        }

        with open(self.config_path, 'w', encoding='UTF-8') as f:
            yaml.dump(default_config, f, allow_unicode=True, indent=2)

        self.config = default_config
        logging.info(f"기본 설정 파일 생성: {self.config_path}")

    def get(self, key_path: str, default=None):
        """점 표기법으로 설정값 가져오기"""
        keys = key_path.split('.')
        value = self.config

        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default

        return value
