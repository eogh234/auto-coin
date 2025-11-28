#!/usr/bin/env python3
"""
GitHub Actions 상태 모니터링 도우미
실시간으로 워크플로 상태를 추적하고 알림을 전송
"""

import requests
import json
import time
import os
import sys
from datetime import datetime
import argparse


class GitHubActionsMonitor:
    def __init__(self, repo, token=None):
        self.repo = repo
        self.token = token or os.getenv('GITHUB_TOKEN')
        self.base_url = "https://api.github.com"
        self.headers = {
            'Accept': 'application/vnd.github.v3+json',
            'User-Agent': 'Auto-Coin-Monitor/1.0'
        }

        if self.token:
            self.headers['Authorization'] = f'token {self.token}'

    def get_latest_run(self, branch='master'):
        """최신 워크플로 실행 정보 가져오기"""
        url = f"{self.base_url}/repos/{self.repo}/actions/runs"
        params = {
            'branch': branch,
            'per_page': 1
        }

        try:
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()

            data = response.json()
            if data['workflow_runs']:
                return data['workflow_runs'][0]

        except requests.RequestException as e:
            print(f"API 요청 실패: {e}")
            return None

    def get_run_details(self, run_id):
        """특정 워크플로 실행의 상세 정보"""
        url = f"{self.base_url}/repos/{self.repo}/actions/runs/{run_id}"

        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json()

        except requests.RequestException as e:
            print(f"워크플로 상세 정보 조회 실패: {e}")
            return None

    def get_run_jobs(self, run_id):
        """워크플로 실행의 작업 목록"""
        url = f"{self.base_url}/repos/{self.repo}/actions/runs/{run_id}/jobs"

        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json()['jobs']

        except requests.RequestException as e:
            print(f"작업 목록 조회 실패: {e}")
            return []

    def monitor_workflow(self, run_id=None, timeout=1800):
        """워크플로 실시간 모니터링"""
        if not run_id:
            # 최신 실행 찾기
            latest = self.get_latest_run()
            if not latest:
                print("❌ 실행 중인 워크플로를 찾을 수 없습니다.")
                return False
            run_id = latest['id']

        print(f"🔍 워크플로 모니터링 시작: #{run_id}")
        print(f"🔗 https://github.com/{self.repo}/actions/runs/{run_id}")

        start_time = time.time()

        while time.time() - start_time < timeout:
            run_details = self.get_run_details(run_id)
            if not run_details:
                time.sleep(10)
                continue

            status = run_details['status']
            conclusion = run_details.get('conclusion')

            # 진행 상황 표시
            jobs = self.get_run_jobs(run_id)
            completed_jobs = len(
                [j for j in jobs if j['status'] == 'completed'])
            total_jobs = len(jobs)

            current_time = datetime.now().strftime("%H:%M:%S")
            elapsed = int(time.time() - start_time)

            print(
                f"[{current_time}] 📊 상태: {status} | 작업: {completed_jobs}/{total_jobs} | 경과: {elapsed}초")

            if status == 'completed':
                if conclusion == 'success':
                    print("✅ 워크플로 성공!")
                    self.send_notification(
                        "success", "🎉 CI/CD 파이프라인 성공", run_details)
                    return True
                else:
                    print(f"❌ 워크플로 실패: {conclusion}")
                    self.show_failure_details(run_id)
                    self.send_notification(
                        "error", f"❌ CI/CD 파이프라인 실패: {conclusion}", run_details)
                    return False

            # 실행 중인 작업 표시
            running_jobs = [j for j in jobs if j['status'] == 'in_progress']
            if running_jobs:
                job_names = ", ".join([j['name'] for j in running_jobs])
                print(f"🔄 실행 중: {job_names}")

            time.sleep(15)

        print("⏰ 타임아웃: 워크플로 모니터링 종료")
        return False

    def show_failure_details(self, run_id):
        """실패 상세 정보 표시"""
        jobs = self.get_run_jobs(run_id)
        failed_jobs = [j for j in jobs if j['conclusion'] == 'failure']

        if failed_jobs:
            print("\n📋 실패한 작업들:")
            for job in failed_jobs:
                print(f"  ❌ {job['name']}")

                # 실패한 단계 표시
                if 'steps' in job:
                    failed_steps = [s for s in job['steps']
                                    if s.get('conclusion') == 'failure']
                    for step in failed_steps:
                        print(f"     └─ 💥 {step['name']}")

    def send_notification(self, status, message, run_details=None):
        """Discord 알림 전송"""
        try:
            # config.yaml에서 웹훅 URL 읽기
            webhook_url = None
            try:
                with open('config.yaml', 'r', encoding='utf-8') as f:
                    import yaml
                    config = yaml.safe_load(f)
                    webhook_url = config.get('discord', {}).get('webhook_url')
            except Exception:
                pass

            if not webhook_url:
                return

            # 색상 설정
            colors = {
                'success': 0x00ff00,  # 초록색
                'warning': 0xffaa00,  # 주황색
                'error': 0xff0000     # 빨간색
            }

            embed = {
                'title': '🚀 GitHub Actions 알림',
                'description': message,
                'color': colors.get(status, 0x0099ff),
                'timestamp': datetime.utcnow().isoformat(),
                'fields': []
            }

            if run_details:
                embed['fields'] = [
                    {'name': '🔗 실행 ID',
                        'value': f"#{run_details['id']}", 'inline': True},
                    {'name': '🌿 브랜치', 'value': run_details.get(
                        'head_branch', 'N/A'), 'inline': True},
                    {'name': '👤 실행자', 'value': run_details.get(
                        'actor', {}).get('login', 'N/A'), 'inline': True}
                ]

            payload = {'embeds': [embed]}

            response = requests.post(webhook_url, json=payload, timeout=10)
            if response.status_code in [200, 204]:
                print("📢 Discord 알림 전송 완료")

        except Exception as e:
            print(f"알림 전송 실패: {e}")


def main():
    parser = argparse.ArgumentParser(description='GitHub Actions 워크플로 모니터링')
    parser.add_argument('--repo', default='eogh234/auto-coin',
                        help='레포지토리 (owner/repo)')
    parser.add_argument('--run-id', type=int, help='모니터링할 워크플로 실행 ID')
    parser.add_argument('--timeout', type=int, default=1800, help='타임아웃 시간(초)')
    parser.add_argument('--token', help='GitHub 토큰')

    args = parser.parse_args()

    monitor = GitHubActionsMonitor(args.repo, args.token)
    success = monitor.monitor_workflow(args.run_id, args.timeout)

    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
