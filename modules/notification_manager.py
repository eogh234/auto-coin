"""
알림 시스템 모듈
"""

import time
import datetime
import logging
import requests
import psutil
from .config_manager import ConfigManager


class NotificationManager:
    """통합 알림 관리자"""

    def __init__(self, config_manager: ConfigManager):
        self.config = config_manager
        self.webhook_url = self.config.get('discord.webhook_url', '')
        self.notification_cooldown = {}
        self.last_status_report = 0

    def send_discord(self, title: str, description: str, color: int = 0x00ff00):
        """Discord 알림 전송"""
        if not self.webhook_url:
            return False

        # 알림 쿨다운 체크
        now = time.time()
        key = f"{title}:{description[:50]}"
        cooldown_time = self.config.get('discord.notification_cooldown', 300)

        if key in self.notification_cooldown:
            if now - self.notification_cooldown[key] < cooldown_time:
                return False

        try:
            embed = {
                "title": title,
                "description": description,
                "color": color,
                "timestamp": datetime.datetime.now().isoformat()
            }

            payload = {"embeds": [embed]}
            response = requests.post(
                self.webhook_url, json=payload, timeout=10)

            if response.status_code in [200, 204]:
                self.notification_cooldown[key] = now
                logging.info(f"Discord 알림 전송: {title}")
                return True

        except Exception as e:
            logging.error(f"Discord 알림 오류: {e}")

        return False

    def send_status_report(self, bot_status: str, additional_info: str = ""):
        """정기 상태 보고"""
        now = time.time()
        interval = self.config.get('discord.status_report_interval', 1800)

        if now - self.last_status_report >= interval:
            memory_usage = psutil.virtual_memory().percent

            status_msg = f"""📊 **자동매매 봇 상태**
🔄 상태: {bot_status}
💾 메모리: {memory_usage:.1f}%
⏰ 시간: {datetime.datetime.now().strftime('%H:%M:%S')}"""

            if additional_info:
                status_msg += f"\n{additional_info}"

            self.send_discord("봇 상태 리포트", status_msg.strip(), 0x0099ff)
            self.last_status_report = now
