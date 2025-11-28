#!/usr/bin/env python3
"""
에러 복구 자동화 스크립트
일반적인 에러 패턴을 감지하고 자동으로 복구를 시도합니다.
"""

import subprocess
import os
import time
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('error_recovery.log'),
        logging.StreamHandler()
    ]
)


class ErrorRecoveryManager:
    def __init__(self):
        self.pm2_app_name = os.getenv('PM2_APP_NAME', 'auto-trader')
        self.max_restart_attempts = 3
        self.restart_cooldown = 300  # 5분
        self.last_restart_time = None
        self.restart_count = 0

        # 알려진 에러 패턴과 해결책
        self.error_patterns = {
            'connection_error': {
                'keywords': ['connection', 'timeout', 'network', 'unreachable'],
                'solution': self.fix_connection_issues
            },
            'memory_error': {
                'keywords': ['memory', 'out of memory', 'malloc', 'allocation'],
                'solution': self.fix_memory_issues
            },
            'disk_space': {
                'keywords': ['no space', 'disk full', 'filesystem full'],
                'solution': self.fix_disk_space_issues
            },
            'permission_error': {
                'keywords': ['permission denied', 'access denied', 'forbidden'],
                'solution': self.fix_permission_issues
            },
            'module_error': {
                'keywords': ['module not found', 'import error', 'no module named'],
                'solution': self.fix_module_issues
            },
            'api_error': {
                'keywords': ['api error', '401', '403', '500', '502', '503'],
                'solution': self.fix_api_issues
            },
            'database_error': {
                'keywords': ['database', 'sqlite', 'connection closed', 'locked'],
                'solution': self.fix_database_issues
            }
        }

    def get_app_logs(self, lines: int = 50) -> str:
        """PM2 애플리케이션 로그 가져오기"""
        try:
            result = subprocess.run(
                ['pm2', 'logs', self.pm2_app_name,
                    '--lines', str(lines), '--raw'],
                capture_output=True, text=True, check=True
            )
            return result.stdout
        except Exception as e:
            logging.error(f"로그 가져오기 실패: {e}")
            return ""

    def get_app_status(self) -> Dict:
        """PM2 애플리케이션 상태 확인"""
        try:
            result = subprocess.run(
                ['pm2', 'describe', self.pm2_app_name, '--format', 'json'],
                capture_output=True, text=True, check=True
            )

            data = json.loads(result.stdout)
            if data and len(data) > 0:
                return {
                    'status': data[0]['pm2_env']['status'],
                    'uptime': data[0]['pm2_env']['pm_uptime'],
                    'restarts': data[0]['pm2_env']['restart_time'],
                    'memory': data[0]['monit']['memory'],
                    'cpu': data[0]['monit']['cpu']
                }
            return {'status': 'unknown'}
        except Exception as e:
            logging.error(f"상태 확인 실패: {e}")
            return {'status': 'error'}

    def detect_error_pattern(self, logs: str) -> Optional[str]:
        """로그에서 에러 패턴 감지"""
        logs_lower = logs.lower()

        for pattern_name, pattern_info in self.error_patterns.items():
            for keyword in pattern_info['keywords']:
                if keyword in logs_lower:
                    logging.info(f"에러 패턴 감지: {pattern_name} (키워드: {keyword})")
                    return pattern_name

        return None

    def can_restart(self) -> bool:
        """재시작 가능 여부 확인"""
        now = datetime.now()

        # 쿨다운 시간 확인
        if self.last_restart_time:
            time_diff = now - self.last_restart_time
            if time_diff.total_seconds() < self.restart_cooldown:
                logging.warning(
                    f"재시작 쿨다운 중 ({self.restart_cooldown - int(time_diff.total_seconds())}초 남음)")
                return False

        # 최대 재시작 횟수 확인
        if self.restart_count >= self.max_restart_attempts:
            logging.error("최대 재시작 횟수 초과")
            return False

        return True

    def restart_application(self) -> bool:
        """애플리케이션 재시작"""
        if not self.can_restart():
            return False

        try:
            logging.info("애플리케이션 재시작 시도...")

            # PM2로 재시작
            subprocess.run(['pm2', 'restart', self.pm2_app_name], check=True)

            # 재시작 정보 업데이트
            self.last_restart_time = datetime.now()
            self.restart_count += 1

            # 시작 대기
            time.sleep(10)

            # 상태 확인
            status = self.get_app_status()
            if status.get('status') == 'online':
                logging.info("애플리케이션 재시작 성공")
                return True
            else:
                logging.error("애플리케이션 재시작 실패")
                return False

        except Exception as e:
            logging.error(f"재시작 중 오류: {e}")
            return False

    def fix_connection_issues(self) -> bool:
        """네트워크 연결 문제 해결"""
        logging.info("연결 문제 해결 시도...")

        # DNS 플러시
        try:
            subprocess.run(['sudo', 'systemctl', 'restart', 'systemd-resolved'],
                           check=False, capture_output=True)
        except:
            pass

        # 단순 재시작으로 해결 시도
        return self.restart_application()

    def fix_memory_issues(self) -> bool:
        """메모리 문제 해결"""
        logging.info("메모리 문제 해결 시도...")

        # 시스템 캐시 정리
        try:
            subprocess.run(['sync'], check=False)
            subprocess.run(['sudo', 'sh', '-c', 'echo 3 > /proc/sys/vm/drop_caches'],
                           check=False, capture_output=True)
        except:
            pass

        # 애플리케이션 재시작
        return self.restart_application()

    def fix_disk_space_issues(self) -> bool:
        """디스크 공간 문제 해결"""
        logging.info("디스크 공간 정리 시도...")

        # 로그 파일 정리
        try:
            # PM2 로그 정리
            subprocess.run(['pm2', 'flush'], check=False)

            # 시스템 로그 정리
            subprocess.run(['sudo', 'journalctl', '--vacuum-time=7d'],
                           check=False, capture_output=True)

            # 임시 파일 정리
            subprocess.run(['sudo', 'apt-get', 'autoremove', '-y'],
                           check=False, capture_output=True)
            subprocess.run(['sudo', 'apt-get', 'autoclean'],
                           check=False, capture_output=True)

        except Exception as e:
            logging.error(f"디스크 정리 중 오류: {e}")

        return self.restart_application()

    def fix_permission_issues(self) -> bool:
        """권한 문제 해결"""
        logging.info("권한 문제 해결 시도...")

        # 애플리케이션 디렉토리 권한 수정
        try:
            app_dir = "/home/ubuntu/auto-trader-v2"
            subprocess.run(['sudo', 'chown', '-R', 'ubuntu:ubuntu', app_dir],
                           check=False, capture_output=True)
            subprocess.run(['chmod', '-R', '755', app_dir],
                           check=False, capture_output=True)
        except Exception as e:
            logging.error(f"권한 수정 중 오류: {e}")

        return self.restart_application()

    def fix_module_issues(self) -> bool:
        """모듈 문제 해결"""
        logging.info("모듈 문제 해결 시도...")

        # 의존성 재설치
        try:
            os.chdir("/home/ubuntu/auto-trader-v2")
            subprocess.run(['pip3', 'install', '-r', 'requirements.txt', '--user'],
                           check=False, capture_output=True)
        except Exception as e:
            logging.error(f"모듈 설치 중 오류: {e}")

        return self.restart_application()

    def fix_api_issues(self) -> bool:
        """API 문제 해결"""
        logging.info("API 문제 해결 시도...")

        # API 연결 테스트 및 대기 시간 추가
        time.sleep(30)  # API 복구 대기

        return self.restart_application()

    def fix_database_issues(self) -> bool:
        """데이터베이스 문제 해결"""
        logging.info("데이터베이스 문제 해결 시도...")

        # SQLite 락 해제
        try:
            db_path = "/home/ubuntu/auto-trader-v2/trade_history.db"
            if os.path.exists(f"{db_path}-wal"):
                os.remove(f"{db_path}-wal")
            if os.path.exists(f"{db_path}-shm"):
                os.remove(f"{db_path}-shm")
        except Exception as e:
            logging.error(f"데이터베이스 정리 중 오류: {e}")

        return self.restart_application()

    def send_recovery_notification(self, error_type: str, success: bool):
        """복구 시도 결과 알림"""
        try:
            webhook_url = os.getenv('DISCORD_WEBHOOK_URL')
            if not webhook_url:
                return

            status = "성공" if success else "실패"
            color = 0x00ff00 if success else 0xff0000

            payload = {
                "embeds": [{
                    "title": f"🔧 자동 복구 {status}",
                    "description": f"에러 유형: {error_type}\n복구 결과: {status}",
                    "color": color,
                    "timestamp": datetime.utcnow().isoformat()
                }]
            }

            subprocess.run([
                'curl', '-X', 'POST', webhook_url,
                '-H', 'Content-Type: application/json',
                '-d', json.dumps(payload)
            ], check=False, capture_output=True)

        except Exception as e:
            logging.error(f"알림 전송 실패: {e}")

    def monitor_and_recover(self):
        """지속적인 모니터링 및 복구"""
        logging.info("에러 복구 모니터링 시작")

        while True:
            try:
                # 애플리케이션 상태 확인
                status = self.get_app_status()

                if status.get('status') not in ['online', 'launching']:
                    logging.warning(f"애플리케이션 비정상 상태: {status.get('status')}")

                    # 로그 확인
                    logs = self.get_app_logs(100)
                    error_pattern = self.detect_error_pattern(logs)

                    if error_pattern:
                        logging.info(f"에러 패턴 감지: {error_pattern}")

                        # 해당 에러에 대한 복구 시도
                        solution_func = self.error_patterns[error_pattern]['solution']
                        success = solution_func()

                        # 복구 결과 알림
                        self.send_recovery_notification(error_pattern, success)

                        if success:
                            self.restart_count = 0  # 성공시 카운터 리셋

                    else:
                        # 일반적인 재시작 시도
                        success = self.restart_application()
                        self.send_recovery_notification("unknown", success)

                # 30초 대기 후 재검사
                time.sleep(30)

            except KeyboardInterrupt:
                logging.info("모니터링 종료")
                break
            except Exception as e:
                logging.error(f"모니터링 중 오류: {e}")
                time.sleep(60)


def main():
    recovery_manager = ErrorRecoveryManager()

    # 원샷 실행 모드 (인자가 있는 경우)
    if len(os.sys.argv) > 1:
        if os.sys.argv[1] == "--check":
            status = recovery_manager.get_app_status()
            logs = recovery_manager.get_app_logs(50)
            error_pattern = recovery_manager.detect_error_pattern(logs)

            print(f"상태: {status.get('status')}")
            if error_pattern:
                print(f"감지된 에러: {error_pattern}")

                # 복구 시도
                solution_func = recovery_manager.error_patterns[error_pattern]['solution']
                success = solution_func()
                print(f"복구 시도: {'성공' if success else '실패'}")
            else:
                print("에러 패턴 없음")

            return

    # 지속적인 모니터링 모드
    recovery_manager.monitor_and_recover()


if __name__ == "__main__":
    main()
