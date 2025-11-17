#!/usr/bin/env python3
"""
자동 롤백 스크립트
배포 실패 시 이전 버전으로 자동 롤백합니다.
"""

import subprocess
import os
import json
import time
import sys
from datetime import datetime


class AutoRollback:
    def __init__(self):
        self.pm2_app_name = os.getenv('PM2_APP_NAME', 'auto-trader')
        self.backup_dir = '/home/ubuntu/auto-trader-v2-backup'
        self.current_dir = '/home/ubuntu/auto-trader-v2'

    def check_backup_exists(self):
        """백업 디렉토리가 존재하는지 확인"""
        return os.path.exists(self.backup_dir)

    def stop_current_app(self):
        """현재 애플리케이션 중지"""
        try:
            print("🛑 현재 애플리케이션 중지 중...")
            subprocess.run(['pm2', 'stop', self.pm2_app_name], check=True)
            subprocess.run(['pm2', 'delete', self.pm2_app_name],
                           check=False)  # 프로세스 완전 삭제
            time.sleep(5)
            return True
        except Exception as e:
            print(f"❌ 애플리케이션 중지 실패: {e}")
            return False

    def backup_current_state(self):
        """현재 상태를 failure 백업으로 저장"""
        try:
            failure_backup = f"{self.current_dir}-failure-{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            subprocess.run(
                ['mv', self.current_dir, failure_backup], check=True)
            print(f"💾 실패한 버전을 {failure_backup}로 백업했습니다")
            return True
        except Exception as e:
            print(f"❌ 현재 상태 백업 실패: {e}")
            return False

    def restore_backup(self):
        """백업에서 이전 버전 복원"""
        try:
            print("🔄 이전 버전으로 복원 중...")
            subprocess.run(['cp', '-r', self.backup_dir,
                           self.current_dir], check=True)
            os.chdir(self.current_dir)
            return True
        except Exception as e:
            print(f"❌ 백업 복원 실패: {e}")
            return False

    def start_previous_version(self):
        """이전 버전 애플리케이션 시작"""
        try:
            print("🚀 이전 버전 시작 중...")

            # PM2로 애플리케이션 시작
            subprocess.run([
                'pm2', 'start', 'main.py',
                '--name', self.pm2_app_name,
                '--interpreter', 'python3'
            ], check=True)

            # PM2 설정 저장
            subprocess.run(['pm2', 'save'], check=True)

            time.sleep(10)  # 시작 대기

            # 상태 확인
            result = subprocess.run(
                ['pm2', 'describe', self.pm2_app_name],
                capture_output=True, text=True
            )

            if 'online' in result.stdout:
                print("✅ 이전 버전이 성공적으로 시작되었습니다")
                return True
            else:
                print("❌ 이전 버전 시작 실패")
                return False

        except Exception as e:
            print(f"❌ 이전 버전 시작 실패: {e}")
            return False

    def verify_rollback(self):
        """롤백 성공 여부 확인"""
        try:
            time.sleep(30)  # 안정화 대기

            # PM2 상태 확인
            result = subprocess.run(
                ['pm2', 'describe', self.pm2_app_name, '--format', 'json'],
                capture_output=True, text=True, check=True
            )

            data = json.loads(result.stdout)
            if data and len(data) > 0:
                status = data[0]['pm2_env']['status']
                if status == 'online':
                    print("✅ 롤백 검증 성공")
                    return True

            print("❌ 롤백 검증 실패")
            return False

        except Exception as e:
            print(f"❌ 롤백 검증 중 오류: {e}")
            return False

    def send_rollback_notification(self, success=True):
        """롤백 결과 알림 전송"""
        try:
            status = "성공" if success else "실패"
            message = f"🔄 Auto-Coin 자동 롤백 {status}\n시간: {datetime.now().isoformat()}"

            # Discord 알림 (간단한 curl 명령)
            webhook_url = os.getenv('DISCORD_WEBHOOK_URL')
            if webhook_url:
                payload = {"content": message}
                subprocess.run([
                    'curl', '-X', 'POST', webhook_url,
                    '-H', 'Content-Type: application/json',
                    '-d', json.dumps(payload)
                ], check=False)

        except Exception as e:
            print(f"❌ 알림 전송 실패: {e}")

    def perform_rollback(self):
        """전체 롤백 프로세스 실행"""
        print("🔄 자동 롤백 프로세스 시작")
        print("=" * 50)

        # 1. 백업 존재 여부 확인
        if not self.check_backup_exists():
            print("❌ 백업 디렉토리가 존재하지 않습니다. 롤백할 수 없습니다.")
            self.send_rollback_notification(False)
            return False

        # 2. 현재 애플리케이션 중지
        if not self.stop_current_app():
            print("❌ 현재 애플리케이션 중지 실패")
            self.send_rollback_notification(False)
            return False

        # 3. 현재 상태 백업
        if not self.backup_current_state():
            print("❌ 현재 상태 백업 실패")
            self.send_rollback_notification(False)
            return False

        # 4. 이전 버전 복원
        if not self.restore_backup():
            print("❌ 이전 버전 복원 실패")
            self.send_rollback_notification(False)
            return False

        # 5. 이전 버전 시작
        if not self.start_previous_version():
            print("❌ 이전 버전 시작 실패")
            self.send_rollback_notification(False)
            return False

        # 6. 롤백 검증
        if not self.verify_rollback():
            print("❌ 롤백 검증 실패")
            self.send_rollback_notification(False)
            return False

        print("✅ 자동 롤백이 성공적으로 완료되었습니다!")
        self.send_rollback_notification(True)
        return True


def main():
    rollback = AutoRollback()

    if rollback.perform_rollback():
        print("🎉 롤백 성공!")
        sys.exit(0)
    else:
        print("💥 롤백 실패!")
        sys.exit(1)


if __name__ == "__main__":
    main()
