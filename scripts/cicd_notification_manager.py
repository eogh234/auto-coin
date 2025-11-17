#!/usr/bin/env python3
"""
CI/CD 전용 알림 시스템
다양한 채널(Discord, 이메일, 웹훅)로 배포 상태를 알림
"""

import requests
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from datetime import datetime
import sys


class NotificationManager:
    def __init__(self):
        self.discord_webhook = os.getenv('DISCORD_WEBHOOK_URL')
        self.slack_webhook = os.getenv('SLACK_WEBHOOK_URL')
        self.email_smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
        self.email_smtp_port = int(os.getenv('SMTP_PORT', '587'))
        self.email_username = os.getenv('EMAIL_USERNAME')
        self.email_password = os.getenv('EMAIL_PASSWORD')
        self.email_recipients = os.getenv('EMAIL_RECIPIENTS', '').split(',')
        self.custom_webhook = os.getenv('CUSTOM_WEBHOOK_URL')

    def send_discord_notification(self, title, message, color=None):
        """Discord 알림 전송"""
        if not self.discord_webhook:
            return False

        try:
            colors = {
                'success': 0x00ff00,
                'warning': 0xffff00,
                'error': 0xff0000,
                'info': 0x0099ff
            }

            embed = {
                "title": title,
                "description": message,
                "color": color or colors.get('info'),
                "timestamp": datetime.utcnow().isoformat(),
                "footer": {
                    "text": "Auto-Coin CI/CD"
                }
            }

            payload = {"embeds": [embed]}

            response = requests.post(self.discord_webhook, json=payload)
            response.raise_for_status()
            print("✅ Discord 알림 전송 성공")
            return True

        except Exception as e:
            print(f"❌ Discord 알림 전송 실패: {e}")
            return False

    def send_slack_notification(self, title, message, color='good'):
        """Slack 알림 전송"""
        if not self.slack_webhook:
            return False

        try:
            payload = {
                "attachments": [
                    {
                        "color": color,
                        "title": title,
                        "text": message,
                        "footer": "Auto-Coin CI/CD",
                        "ts": int(datetime.utcnow().timestamp())
                    }
                ]
            }

            response = requests.post(self.slack_webhook, json=payload)
            response.raise_for_status()
            print("✅ Slack 알림 전송 성공")
            return True

        except Exception as e:
            print(f"❌ Slack 알림 전송 실패: {e}")
            return False

    def send_email_notification(self, subject, message):
        """이메일 알림 전송"""
        if not all([self.email_username, self.email_password, self.email_recipients[0]]):
            return False

        try:
            msg = MIMEMultipart()
            msg['From'] = self.email_username
            msg['To'] = ', '.join(self.email_recipients)
            msg['Subject'] = subject

            msg.attach(MIMEText(message, 'plain'))

            with smtplib.SMTP(self.email_smtp_server, self.email_smtp_port) as server:
                server.starttls()
                server.login(self.email_username, self.email_password)
                server.sendmail(self.email_username,
                                self.email_recipients, msg.as_string())

            print("✅ 이메일 알림 전송 성공")
            return True

        except Exception as e:
            print(f"❌ 이메일 알림 전송 실패: {e}")
            return False

    def send_custom_webhook(self, title, message, status):
        """커스텀 웹훅 알림 전송"""
        if not self.custom_webhook:
            return False

        try:
            payload = {
                "title": title,
                "message": message,
                "status": status,
                "timestamp": datetime.utcnow().isoformat(),
                "source": "auto-coin-cicd"
            }

            response = requests.post(self.custom_webhook, json=payload)
            response.raise_for_status()
            print("✅ 커스텀 웹훅 알림 전송 성공")
            return True

        except Exception as e:
            print(f"❌ 커스텀 웹훅 알림 전송 실패: {e}")
            return False

    def send_deployment_notification(self, status, details):
        """배포 관련 종합 알림 전송"""
        status_emoji = {
            'success': '✅',
            'warning': '⚠️',
            'error': '❌',
            'info': 'ℹ️'
        }

        emoji = status_emoji.get(status, 'ℹ️')
        title = f"{emoji} Auto-Coin 배포 {status.upper()}"

        message = f"""
배포 상태: {status}
시간: {datetime.now().isoformat()}
커밋: {os.getenv('GITHUB_SHA', 'Unknown')}
브랜치: {os.getenv('GITHUB_REF', 'Unknown')}
작성자: {os.getenv('GITHUB_ACTOR', 'Unknown')}

상세 정보:
{details}
        """.strip()

        success_count = 0

        # Discord 알림
        discord_colors = {
            'success': 0x00ff00,
            'warning': 0xffff00,
            'error': 0xff0000,
            'info': 0x0099ff
        }
        if self.send_discord_notification(title, message, discord_colors.get(status)):
            success_count += 1

        # Slack 알림
        slack_colors = {
            'success': 'good',
            'warning': 'warning',
            'error': 'danger',
            'info': 'good'
        }
        if self.send_slack_notification(title, message, slack_colors.get(status)):
            success_count += 1

        # 이메일 알림 (중요한 상태에만)
        if status in ['error', 'success']:
            if self.send_email_notification(title, message):
                success_count += 1

        # 커스텀 웹훅
        if self.send_custom_webhook(title, message, status):
            success_count += 1

        print(f"📢 {success_count}개 채널로 알림 전송 완료")
        return success_count > 0


def main():
    if len(sys.argv) < 3:
        print("사용법: python notification_manager.py <status> <details>")
        print("status: success, warning, error, info")
        sys.exit(1)

    status = sys.argv[1]
    details = " ".join(sys.argv[2:])

    notifier = NotificationManager()

    if notifier.send_deployment_notification(status, details):
        print("🎉 알림 전송 성공!")
        sys.exit(0)
    else:
        print("💥 알림 전송 실패!")
        sys.exit(1)


if __name__ == "__main__":
    main()
