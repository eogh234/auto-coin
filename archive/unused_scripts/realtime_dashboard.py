#!/usr/bin/env python3
"""
📊 Auto-Coin Trading Bot 실시간 대시보드

기능:
- 실시간 수익률 모니터링
- 시스템 리소스 사용량
- 거래 활동 추적
- 성능 지표 시각화
"""

import time
import json
import sqlite3
import os
from datetime import datetime, timedelta
from pathlib import Path
import sys

# 프로젝트 루트 경로 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    print("⚠️ psutil이 설치되지 않았습니다. 일부 기능이 제한됩니다.")

try:
    from modules import ConfigManager, LearningSystem
except ImportError:
    sys.path.insert(0, str(project_root / 'modules'))
    from config_manager import ConfigManager
    from learning_system import LearningSystem


class RealtimeDashboard:
    """실시간 대시보드 클래스"""

    def __init__(self):
        self.config = ConfigManager()
        self.learning = LearningSystem(self.config)
        self.running = True

    def clear_screen(self):
        """화면 클리어"""
        os.system('cls' if os.name == 'nt' else 'clear')

    def get_system_status(self):
        """시스템 상태 조회"""
        if not PSUTIL_AVAILABLE:
            return {
                'cpu_percent': 0,
                'memory_percent': 0,
                'disk_percent': 0,
                'process_memory': 0
            }

        try:
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('.')

            # 현재 프로세스 정보
            try:
                process = psutil.Process()
                process_memory = process.memory_info().rss / 1024**2
            except:
                process_memory = 0

            return {
                'cpu_percent': cpu_percent,
                'memory_percent': memory.percent,
                'disk_percent': disk.percent,
                'process_memory': process_memory
            }
        except Exception as e:
            print(f"시스템 상태 조회 오류: {e}")
            return {
                'cpu_percent': 0,
                'memory_percent': 0,
                'disk_percent': 0,
                'process_memory': 0
            }

    def get_trading_stats(self, days=1):
        """거래 통계 조회"""
        try:
            conn = sqlite3.connect(self.learning.db_path)
            cursor = conn.cursor()

            # 최근 거래 조회
            since_date = datetime.now() - timedelta(days=days)
            cursor.execute("""
                SELECT action, success, profit_rate, timestamp 
                FROM trades 
                WHERE timestamp > ?
                ORDER BY timestamp DESC
                LIMIT 20
            """, (since_date.isoformat(),))

            recent_trades = cursor.fetchall()

            # 통계 계산
            total_trades = len(recent_trades)
            if total_trades == 0:
                conn.close()
                return {
                    'total_trades': 0,
                    'success_rate': 0,
                    'avg_profit': 0,
                    'recent_trades': []
                }

            successful_trades = sum(
                1 for trade in recent_trades if trade[1] == 1)
            success_rate = successful_trades / total_trades

            # 수익률 계산
            profit_rates = [trade[2]
                            for trade in recent_trades if trade[2] is not None]
            avg_profit = sum(profit_rates) / \
                len(profit_rates) if profit_rates else 0

            conn.close()

            return {
                'total_trades': total_trades,
                'success_rate': success_rate,
                'avg_profit': avg_profit,
                'recent_trades': recent_trades[:5]  # 최근 5개 거래
            }

        except Exception as e:
            print(f"거래 통계 조회 오류: {e}")
            return {
                'total_trades': 0,
                'success_rate': 0,
                'avg_profit': 0,
                'recent_trades': []
            }

    def get_file_status(self):
        """파일 상태 조회"""
        files_info = {}
        files_to_check = [
            'trade_history.db',
            'auto_trader.log',
            'trading_data.json'
        ]

        for filename in files_to_check:
            if os.path.exists(filename):
                size = os.path.getsize(filename)
                modified = datetime.fromtimestamp(os.path.getmtime(filename))
                files_info[filename] = {
                    'size_mb': size / 1024**2,
                    'last_modified': modified
                }
            else:
                files_info[filename] = {
                    'size_mb': 0,
                    'last_modified': None
                }

        return files_info

    def format_progress_bar(self, percentage, width=20):
        """프로그레스 바 생성"""
        filled = int(width * percentage / 100)
        bar = '█' * filled + '░' * (width - filled)
        return f"[{bar}] {percentage:5.1f}%"

    def display_dashboard(self):
        """대시보드 출력"""
        self.clear_screen()

        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 헤더
        print("=" * 70)
        print(f"📊 Auto-Coin Trading Bot 실시간 대시보드")
        print(f"🕐 {current_time}")
        print("=" * 70)

        # 시스템 상태
        sys_status = self.get_system_status()
        print("\n🖥️  시스템 상태")
        print("-" * 30)
        print(
            f"CPU    : {self.format_progress_bar(sys_status['cpu_percent'])}")
        print(
            f"메모리  : {self.format_progress_bar(sys_status['memory_percent'])}")
        print(f"디스크  : {self.format_progress_bar(sys_status['disk_percent'])}")
        print(f"프로세스: {sys_status['process_memory']:.1f}MB")

        # 거래 통계 (오늘)
        trading_stats = self.get_trading_stats(1)
        print("\n📈 거래 통계 (오늘)")
        print("-" * 30)
        print(f"총 거래  : {trading_stats['total_trades']:3d}회")
        print(f"성공률  : {trading_stats['success_rate']:5.1%}")
        print(f"평균수익: {trading_stats['avg_profit']:+6.2%}")

        # 최근 거래 내역
        if trading_stats['recent_trades']:
            print("\n📋 최근 거래 내역")
            print("-" * 30)
            for trade in trading_stats['recent_trades']:
                action, success, profit_rate, timestamp = trade
                status = "✅" if success == 1 else "❌" if success == 0 else "⏳"
                profit_str = f"{profit_rate:+6.2%}" if profit_rate else "  -   "
                time_str = datetime.fromisoformat(timestamp).strftime("%H:%M")
                print(f"{status} {time_str} {action:4s} {profit_str}")
        else:
            print("\n📋 최근 거래 내역")
            print("-" * 30)
            print("거래 데이터가 없습니다.")

        # 파일 상태
        file_status = self.get_file_status()
        print("\n📁 파일 상태")
        print("-" * 30)
        for filename, info in file_status.items():
            if info['last_modified']:
                age = datetime.now() - info['last_modified']
                age_str = f"{age.total_seconds() / 60:.0f}분 전"
                print(f"{filename}: {info['size_mb']:.1f}MB ({age_str})")
            else:
                print(f"{filename}: 없음")

        # 현재 적응형 매개변수
        print("\n🧠 현재 거래 매개변수")
        print("-" * 30)
        params = self.learning.adaptive_params
        print(f"RSI 매수: {params.get('rsi_buy_threshold', 30):2d}")
        print(f"RSI 매도: {params.get('rsi_sell_threshold', 70):2d}")
        print(f"목표수익: {params.get('min_profit_target', 0.02):5.1%}")
        print(f"손절기준: {params.get('stop_loss_threshold', -0.05):5.1%}")

        print("\n" + "=" * 70)
        print("💡 Press Ctrl+C to exit | Refreshing every 5 seconds...")

    def run(self):
        """대시보드 실행"""
        try:
            while self.running:
                self.display_dashboard()
                time.sleep(5)

        except KeyboardInterrupt:
            print("\n\n👋 대시보드를 종료합니다.")
            self.running = False

        except Exception as e:
            print(f"\n❌ 대시보드 오류: {e}")


if __name__ == "__main__":
    dashboard = RealtimeDashboard()
    dashboard.run()
