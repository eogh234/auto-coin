#!/usr/bin/env python3
"""
배포 후 헬스체크 스크립트
애플리케이션이 정상적으로 작동하는지 확인합니다.
"""

import requests
import json
import time
import sys
import subprocess
import os
from datetime import datetime


class HealthChecker:
    def __init__(self):
        self.pm2_app_name = os.getenv('PM2_APP_NAME', 'auto-trader')
        self.max_retries = 10
        self.retry_interval = 30  # 30초

    def check_pm2_process(self):
        """PM2 프로세스 상태 확인"""
        try:
            result = subprocess.run(
                ['pm2', 'describe', self.pm2_app_name, '--format', 'json'],
                capture_output=True, text=True, check=True
            )

            data = json.loads(result.stdout)
            if data and len(data) > 0:
                status = data[0]['pm2_env']['status']
                uptime = data[0]['pm2_env']['pm_uptime']
                memory = data[0]['monit']['memory']
                cpu = data[0]['monit']['cpu']

                print(f"📊 PM2 상태: {status}")
                print(f"🕐 업타임: {uptime}")
                print(f"💾 메모리: {memory / 1024 / 1024:.1f}MB")
                print(f"🔧 CPU: {cpu}%")

                return status == 'online'
            return False

        except Exception as e:
            print(f"❌ PM2 상태 확인 실패: {e}")
            return False

    def check_log_errors(self):
        """최근 로그에서 심각한 에러 확인"""
        try:
            result = subprocess.run(
                ['pm2', 'logs', self.pm2_app_name, '--lines', '20', '--raw'],
                capture_output=True, text=True
            )

            logs = result.stdout.lower()
            error_keywords = ['error', 'exception',
                              'traceback', 'failed', 'critical']

            errors = []
            for keyword in error_keywords:
                if keyword in logs:
                    errors.append(keyword)

            if errors:
                print(f"⚠️ 로그에서 발견된 에러 키워드: {', '.join(errors)}")
                print("최근 로그:")
                print(result.stdout[-500:])  # 마지막 500자만 출력
                return False

            print("✅ 로그 상태 양호")
            return True

        except Exception as e:
            print(f"❌ 로그 확인 실패: {e}")
            return False

    def check_trading_activity(self):
        """거래 활동 확인 (trading_data.json 파일 존재 및 최신성)"""
        try:
            trading_data_path = "trading_data.json"

            if not os.path.exists(trading_data_path):
                print("⚠️ 거래 데이터 파일이 존재하지 않음")
                return True  # 새로 배포된 경우는 정상

            # 파일 수정 시간 확인
            mod_time = os.path.getmtime(trading_data_path)
            current_time = time.time()

            # 1시간 이내에 수정되었으면 활성 상태로 간주
            if current_time - mod_time < 3600:
                print("✅ 거래 활동 정상 (1시간 이내 데이터 업데이트)")
                return True
            else:
                print("⚠️ 거래 데이터가 오래됨 (1시간 이상)")
                return False

        except Exception as e:
            print(f"❌ 거래 활동 확인 실패: {e}")
            return False

    def check_system_resources(self):
        """시스템 리소스 확인"""
        try:
            # 디스크 사용량 확인
            result = subprocess.run(
                ['df', '-h', '.'], capture_output=True, text=True)
            print("💽 디스크 사용량:")
            print(result.stdout)

            # 메모리 사용량 확인
            result = subprocess.run(
                ['free', '-h'], capture_output=True, text=True)
            print("💾 메모리 사용량:")
            print(result.stdout)

            return True

        except Exception as e:
            print(f"❌ 시스템 리소스 확인 실패: {e}")
            return False

    def comprehensive_health_check(self):
        """종합 헬스체크 수행"""
        print(f"🏥 헬스체크 시작 - {datetime.now().isoformat()}")
        print("="*50)

        checks = [
            ("PM2 프로세스", self.check_pm2_process),
            ("로그 에러 확인", self.check_log_errors),
            ("거래 활동 확인", self.check_trading_activity),
            ("시스템 리소스", self.check_system_resources)
        ]

        passed = 0
        total = len(checks)

        for check_name, check_func in checks:
            print(f"\n🔍 {check_name} 확인 중...")
            try:
                if check_func():
                    passed += 1
                    print(f"✅ {check_name}: 통과")
                else:
                    print(f"❌ {check_name}: 실패")
            except Exception as e:
                print(f"❌ {check_name}: 예외 발생 - {e}")

        print("\n" + "="*50)
        print(f"📊 헬스체크 결과: {passed}/{total} 통과")

        success_rate = passed / total
        if success_rate >= 0.75:  # 75% 이상 통과시 성공
            print("✅ 전체 헬스체크 성공")
            return True
        else:
            print("❌ 전체 헬스체크 실패")
            return False


def main():
    checker = HealthChecker()

    # 여러 번 재시도
    for attempt in range(checker.max_retries):
        print(f"\n🔄 헬스체크 시도 {attempt + 1}/{checker.max_retries}")

        if checker.comprehensive_health_check():
            print("🎉 애플리케이션이 정상적으로 작동합니다!")
            sys.exit(0)

        if attempt < checker.max_retries - 1:
            print(f"⏳ {checker.retry_interval}초 후 재시도...")
            time.sleep(checker.retry_interval)

    print("💥 헬스체크 최종 실패 - 애플리케이션이 정상적으로 작동하지 않습니다")
    sys.exit(1)


if __name__ == "__main__":
    main()
