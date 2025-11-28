#!/usr/bin/env python3
"""
🔍 Auto-Coin Trading Bot 성능 모니터링 도구

기능:
- 메모리 사용량 분석
- CPU 사용률 체크
- 거래 성과 분석
- 코드 최적화 제안
"""

import psutil
import sqlite3
import json
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

# 프로젝트 루트 경로 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from modules import ConfigManager, LearningSystem
except ImportError:
    # 상대 경로로 시도
    sys.path.insert(0, str(project_root / 'modules'))
    from config_manager import ConfigManager
    from learning_system import LearningSystem


class PerformanceMonitor:
    """성능 모니터링 클래스"""

    def __init__(self):
        self.config = ConfigManager()
        self.learning = LearningSystem(self.config)

    def check_system_resources(self):
        """시스템 리소스 사용량 체크"""
        print("🖥️  시스템 리소스 사용량")
        print("=" * 40)

        # CPU 사용률
        cpu_percent = psutil.cpu_percent(interval=1)
        print(f"CPU 사용률: {cpu_percent:.1f}%")

        # 메모리 사용량
        memory = psutil.virtual_memory()
        print(
            f"메모리 사용률: {memory.percent:.1f}% ({memory.used // 1024**2}MB / {memory.total // 1024**2}MB)")

        # 디스크 사용량
        disk = psutil.disk_usage('.')
        print(
            f"디스크 사용률: {disk.percent:.1f}% ({disk.used // 1024**3}GB / {disk.total // 1024**3}GB)")

        # 현재 프로세스 상세 정보
        process = psutil.Process()
        print(f"\n📊 현재 프로세스 정보:")
        print(f"메모리 사용량: {process.memory_info().rss / 1024**2:.1f}MB")
        print(
            f"CPU 시간: {process.cpu_times().user + process.cpu_times().system:.2f}초")

    def analyze_trading_performance(self, days=7):
        """거래 성과 분석"""
        print(f"\n📈 거래 성과 분석 (최근 {days}일)")
        print("=" * 40)

        try:
            # 데이터베이스에서 거래 기록 조회
            conn = sqlite3.connect(self.learning.db_path)
            cursor = conn.cursor()

            # 최근 거래 조회
            since_date = datetime.now() - timedelta(days=days)
            cursor.execute("""
                SELECT * FROM trades 
                WHERE timestamp > ? 
                ORDER BY timestamp DESC
            """, (since_date.isoformat(),))

            trades = cursor.fetchall()
            conn.close()

            if not trades:
                print("❌ 분석할 거래 데이터가 없습니다.")
                return

            # 거래 통계 계산
            total_trades = len(trades)
            successful_trades = sum(1 for trade in trades if len(
                trade) > 10 and trade[10] == 1)
            success_rate = successful_trades / total_trades if total_trades > 0 else 0

            # 수익률 계산 (profit_rate 컬럼이 있는 경우)
            profit_rates = [trade[11] for trade in trades if len(
                trade) > 11 and trade[11] is not None]
            avg_profit = sum(profit_rates) / \
                len(profit_rates) if profit_rates else 0

            print(f"총 거래 수: {total_trades}")
            print(f"성공 거래: {successful_trades}")
            print(f"성공률: {success_rate:.1%}")
            print(f"평균 수익률: {avg_profit:+.2%}")

            if profit_rates:
                print(f"최고 수익률: {max(profit_rates):+.2%}")
                print(f"최저 수익률: {min(profit_rates):+.2%}")

        except Exception as e:
            print(f"❌ 거래 성과 분석 실패: {e}")

    def check_file_sizes(self):
        """파일 크기 및 로그 분석"""
        print(f"\n📁 파일 시스템 분석")
        print("=" * 40)

        # 주요 데이터 파일들 크기 체크
        files_to_check = [
            'trade_history.db',
            'auto_trader.log',
            'trading_data.json',
            'config.yaml'
        ]

        for filename in files_to_check:
            if os.path.exists(filename):
                size = os.path.getsize(filename)
                size_mb = size / 1024**2
                print(f"{filename}: {size_mb:.2f}MB")
            else:
                print(f"{filename}: 파일 없음")

    def analyze_memory_usage(self):
        """메모리 사용 패턴 분석"""
        print(f"\n🧠 메모리 사용 패턴 분석")
        print("=" * 40)

        # 현재 프로세스의 메모리 맵
        process = psutil.Process()
        memory_info = process.memory_full_info()

        print(f"RSS (실제 사용 메모리): {memory_info.rss / 1024**2:.1f}MB")
        print(f"VMS (가상 메모리): {memory_info.vms / 1024**2:.1f}MB")

        # macOS에서는 일부 속성이 다를 수 있음
        try:
            print(f"USS (고유 메모리): {memory_info.uss / 1024**2:.1f}MB")
            print(f"PSS (비례 공유 메모리): {memory_info.pss / 1024**2:.1f}MB")
        except AttributeError:
            pass

        try:
            print(f"공유 메모리: {memory_info.shared / 1024**2:.1f}MB")
            print(f"텍스트 (코드) 메모리: {memory_info.text / 1024**2:.1f}MB")
            print(f"데이터 메모리: {memory_info.data / 1024**2:.1f}MB")
        except AttributeError:
            print("일부 메모리 정보는 현재 플랫폼에서 사용할 수 없습니다.")

    def suggest_optimizations(self):
        """최적화 제안"""
        print(f"\n💡 최적화 제안사항")
        print("=" * 40)

        suggestions = []

        # 메모리 사용량 체크
        memory = psutil.virtual_memory()
        if memory.percent > 80:
            suggestions.append("⚠️  메모리 사용률이 높습니다. 불필요한 데이터 캐싱을 줄여보세요.")

        # CPU 사용량 체크
        cpu_percent = psutil.cpu_percent(interval=1)
        if cpu_percent > 70:
            suggestions.append("⚠️  CPU 사용률이 높습니다. 연산 최적화가 필요합니다.")

        # 데이터베이스 파일 크기 체크
        if os.path.exists('trade_history.db'):
            db_size = os.path.getsize('trade_history.db') / 1024**2
            if db_size > 100:
                suggestions.append(
                    "📦 데이터베이스가 100MB를 초과했습니다. 오래된 기록 정리를 고려하세요.")

        # 로그 파일 크기 체크
        if os.path.exists('auto_trader.log'):
            log_size = os.path.getsize('auto_trader.log') / 1024**2
            if log_size > 50:
                suggestions.append("📝 로그 파일이 50MB를 초과했습니다. 로그 로테이션을 설정하세요.")

        # 현재 프로세스 메모리 사용량 체크
        process = psutil.Process()
        process_memory = process.memory_info().rss / 1024**2
        if process_memory > 500:
            suggestions.append("🔍 프로세스 메모리 사용량이 500MB를 초과했습니다. 메모리 누수를 점검하세요.")

        # 제안사항 출력
        if suggestions:
            for suggestion in suggestions:
                print(suggestion)
        else:
            print("✅ 현재 시스템 상태가 양호합니다!")

        # 일반적인 최적화 팁
        print(f"\n🚀 일반적인 최적화 팁:")
        print("- 불필요한 데이터 캐싱 최소화")
        print("- API 호출 빈도 조절")
        print("- 데이터베이스 정기 정리")
        print("- 로그 레벨 최적화")
        print("- 메모리 효율적인 자료구조 사용")

    def run_full_analysis(self):
        """전체 성능 분석 실행"""
        print("🔍 Auto-Coin Trading Bot 성능 분석")
        print("=" * 50)
        print(f"분석 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        self.check_system_resources()
        self.analyze_trading_performance()
        self.check_file_sizes()
        self.analyze_memory_usage()
        self.suggest_optimizations()

        print(f"\n✅ 성능 분석 완료!")


if __name__ == "__main__":
    monitor = PerformanceMonitor()
    monitor.run_full_analysis()
