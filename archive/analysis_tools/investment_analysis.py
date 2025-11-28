#!/usr/bin/env python3
"""
📈 Auto-Coin Trading Bot 투자손익 종합 분석 보고서

실제 거래 데이터와 시스템 로그를 기반으로 한 상세 분석
"""

import sys
import sqlite3
import json
import re
from datetime import datetime, timedelta
from pathlib import Path

# 프로젝트 루트 경로 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from modules import ConfigManager, LearningSystem
except ImportError:
    sys.path.insert(0, str(project_root / 'modules'))
    from config_manager import ConfigManager
    from learning_system import LearningSystem


class InvestmentAnalysisReport:
    """투자손익 종합 분석 클래스"""

    def __init__(self):
        self.config = ConfigManager()
        self.learning = LearningSystem(self.config)
        self.analysis_time = datetime.now()

    def analyze_log_data(self):
        """로그 데이터 분석"""
        log_file = "auto_trader.log"

        if not Path(log_file).exists():
            return {
                'total_signals': 0,
                'failed_trades': 0,
                'signal_types': {},
                'recent_activity': []
            }

        with open(log_file, 'r', encoding='utf-8') as f:
            log_content = f.read()

        # 신호 발생 패턴 분석
        signal_pattern = r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}),\d+ - INFO - 신호 발생: (KRW-\w+) -> (\w+)'
        signals = re.findall(signal_pattern, log_content)

        # 잔고 부족 패턴 분석
        balance_pattern = r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}),\d+ - WARNING - 최소 잔고 부족: ([\d,]+) < ([\d,]+)'
        balance_failures = re.findall(balance_pattern, log_content)

        # 신호 유형별 분석
        signal_types = {}
        for timestamp, ticker, signal_type in signals:
            if signal_type not in signal_types:
                signal_types[signal_type] = []
            signal_types[signal_type].append((timestamp, ticker))

        return {
            'total_signals': len(signals),
            'failed_trades': len(balance_failures),
            'signal_types': signal_types,
            'recent_signals': signals[-10:] if signals else [],
            'balance_info': balance_failures[-1] if balance_failures else None
        }

    def analyze_database_records(self):
        """데이터베이스 거래 기록 분석"""
        try:
            conn = sqlite3.connect(self.learning.db_path)
            cursor = conn.cursor()

            # 총 거래 수
            cursor.execute("SELECT COUNT(*) FROM trades")
            total_trades = cursor.fetchone()[0]

            # 완료된 거래 분석
            cursor.execute("""
                SELECT action, success, profit_rate, hold_duration, timestamp 
                FROM trades 
                WHERE success IS NOT NULL
                ORDER BY timestamp DESC
            """)
            completed_trades = cursor.fetchall()

            # 성공률 계산
            if completed_trades:
                success_count = sum(
                    1 for trade in completed_trades if trade[1] == 1)
                success_rate = success_count / len(completed_trades)

                # 수익률 분석
                profits = [trade[2]
                           for trade in completed_trades if trade[2] is not None]
                profit_stats = {
                    'avg_profit': sum(profits) / len(profits) if profits else 0,
                    'max_profit': max(profits) if profits else 0,
                    'min_profit': min(profits) if profits else 0,
                    'total_return': sum(profits) if profits else 0
                }

                # 보유 기간 분석
                durations = [trade[3]
                             for trade in completed_trades if trade[3] is not None]
                duration_stats = {
                    'avg_duration': sum(durations) / len(durations) if durations else 0,
                    'max_duration': max(durations) if durations else 0,
                    'min_duration': min(durations) if durations else 0
                }
            else:
                success_rate = 0
                profit_stats = {'avg_profit': 0, 'max_profit': 0,
                                'min_profit': 0, 'total_return': 0}
                duration_stats = {'avg_duration': 0,
                                  'max_duration': 0, 'min_duration': 0}

            conn.close()

            return {
                'total_trades': total_trades,
                'completed_trades': len(completed_trades),
                'success_rate': success_rate,
                'profit_stats': profit_stats,
                'duration_stats': duration_stats,
                'recent_trades': completed_trades[:5]
            }

        except Exception as e:
            print(f"데이터베이스 분석 오류: {e}")
            return {
                'total_trades': 0,
                'completed_trades': 0,
                'success_rate': 0,
                'profit_stats': {'avg_profit': 0, 'max_profit': 0, 'min_profit': 0, 'total_return': 0},
                'duration_stats': {'avg_duration': 0, 'max_duration': 0, 'min_duration': 0},
                'recent_trades': []
            }

    def analyze_trading_patterns(self, log_analysis):
        """거래 패턴 분석"""
        patterns = {
            'most_active_coins': {},
            'signal_distribution': {},
            'time_patterns': {
                'hourly': {str(i): 0 for i in range(24)},
                'daily': {}
            }
        }

        # 신호 유형별 분포
        for signal_type, signals in log_analysis['signal_types'].items():
            patterns['signal_distribution'][signal_type] = len(signals)

            # 코인별 활동
            for timestamp, ticker in signals:
                if ticker not in patterns['most_active_coins']:
                    patterns['most_active_coins'][ticker] = 0
                patterns['most_active_coins'][ticker] += 1

                # 시간대별 패턴
                try:
                    hour = datetime.strptime(
                        timestamp, "%Y-%m-%d %H:%M:%S").hour
                    patterns['time_patterns']['hourly'][str(hour)] += 1
                except:
                    pass

        return patterns

    def generate_improvement_recommendations(self, log_analysis, db_analysis, patterns):
        """개선 권장사항 생성"""
        recommendations = []

        # 잔고 관련 권장사항
        if log_analysis['failed_trades'] > 0:
            fail_rate = log_analysis['failed_trades'] / \
                log_analysis['total_signals'] * 100
            recommendations.append({
                'priority': 'HIGH',
                'category': '자금 관리',
                'issue': f"잔고 부족으로 {log_analysis['failed_trades']}회 거래 실패 ({fail_rate:.1f}%)",
                'solution': '최소 10만원 이상 입금하여 거래 기회 확보',
                'expected_impact': '거래 기회 100% 활용, 잠재 수익 실현'
            })

        # 거래 활동 권장사항
        if db_analysis['completed_trades'] == 0:
            recommendations.append({
                'priority': 'HIGH',
                'category': '거래 실행',
                'issue': '실제 거래가 전혀 실행되지 않음',
                'solution': '테스트 모드 해제 및 충분한 초기 자금 확보',
                'expected_impact': '실제 수익 창출 기회 확보'
            })

        # 신호 효율성 권장사항
        if log_analysis['total_signals'] > 50:
            recommendations.append({
                'priority': 'MEDIUM',
                'category': '알고리즘 최적화',
                'issue': f'{log_analysis["total_signals"]}개 신호 발생했으나 실행 없음',
                'solution': '신호 필터링 강화 및 매개변수 조정',
                'expected_impact': '거래 신호 정확도 향상'
            })

        # 시간대 최적화
        hourly_activity = patterns['time_patterns']['hourly']
        peak_hour = max(hourly_activity.items(), key=lambda x: x[1])
        if int(peak_hour[1]) > 0:
            recommendations.append({
                'priority': 'LOW',
                'category': '시간 최적화',
                'issue': f'{peak_hour[0]}시에 가장 많은 신호 발생',
                'solution': '활동 시간대 집중 모니터링 및 알고리즘 조정',
                'expected_impact': '시간대별 최적화로 수익률 개선'
            })

        return recommendations

    def generate_report(self):
        """종합 분석 보고서 생성"""
        print("=" * 80)
        print("📈 Auto-Coin Trading Bot 투자손익 종합 분석 보고서")
        print("=" * 80)
        print(f"📅 분석 기간: {self.analysis_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print()

        # 로그 데이터 분석
        log_analysis = self.analyze_log_data()

        # 데이터베이스 분석
        db_analysis = self.analyze_database_records()

        # 거래 패턴 분석
        patterns = self.analyze_trading_patterns(log_analysis)

        # 1. 전체 거래 현황
        print("📊 1. 전체 거래 현황")
        print("-" * 50)
        print(f"💡 총 거래 신호 발생: {log_analysis['total_signals']}회")
        print(f"❌ 잔고 부족 실패: {log_analysis['failed_trades']}회")
        print(f"✅ 실제 완료 거래: {db_analysis['completed_trades']}회")

        if log_analysis['total_signals'] > 0:
            execution_rate = (
                log_analysis['total_signals'] - log_analysis['failed_trades']) / log_analysis['total_signals'] * 100
            print(f"📈 거래 실행률: {execution_rate:.1f}%")

        print()

        # 2. 수익성 분석
        print("💰 2. 수익성 분석")
        print("-" * 50)

        if db_analysis['completed_trades'] > 0:
            print(f"🎯 거래 성공률: {db_analysis['success_rate']:.1%}")
            print(
                f"📊 평균 수익률: {db_analysis['profit_stats']['avg_profit']:+.2%}")
            print(
                f"🔝 최고 수익률: {db_analysis['profit_stats']['max_profit']:+.2%}")
            print(
                f"🔻 최저 수익률: {db_analysis['profit_stats']['min_profit']:+.2%}")
            print(
                f"💵 총 누적 수익률: {db_analysis['profit_stats']['total_return']:+.2%}")

            print(f"\n⏱️ 거래 보유 기간 분석:")
            print(f"평균: {db_analysis['duration_stats']['avg_duration']:.0f}분")
            print(f"최장: {db_analysis['duration_stats']['max_duration']:.0f}분")
            print(f"최단: {db_analysis['duration_stats']['min_duration']:.0f}분")
        else:
            print("❌ 완료된 거래가 없어 수익성 분석 불가")
            print("💡 현재 상태: 신호 발생하나 실제 거래 미실행")

        print()

        # 3. 거래 패턴 분석
        print("🔍 3. 거래 패턴 분석")
        print("-" * 50)

        if patterns['signal_distribution']:
            print("📈 신호 유형별 분포:")
            for signal_type, count in sorted(patterns['signal_distribution'].items(), key=lambda x: x[1], reverse=True):
                print(f"  {signal_type}: {count}회")

        if patterns['most_active_coins']:
            print(f"\n🏆 가장 활발한 코인 TOP 5:")
            top_coins = sorted(patterns['most_active_coins'].items(
            ), key=lambda x: x[1], reverse=True)[:5]
            for ticker, count in top_coins:
                print(f"  {ticker}: {count}회")

        # 시간대별 활동
        hourly_activity = patterns['time_patterns']['hourly']
        peak_hours = sorted([(int(k), v) for k, v in hourly_activity.items(
        ) if v > 0], key=lambda x: x[1], reverse=True)[:3]
        if peak_hours:
            print(f"\n🕐 활동 시간대 TOP 3:")
            for hour, count in peak_hours:
                print(f"  {hour:02d}시: {count}회")

        print()

        # 4. 문제점 및 개선사항
        print("⚠️ 4. 현재 문제점 및 개선 권장사항")
        print("-" * 50)

        recommendations = self.generate_improvement_recommendations(
            log_analysis, db_analysis, patterns)

        for i, rec in enumerate(recommendations, 1):
            priority_emoji = {"HIGH": "🔴", "MEDIUM": "🟡", "LOW": "🟢"}
            print(
                f"{priority_emoji[rec['priority']]} {i}. {rec['category']} ({rec['priority']})")
            print(f"   문제: {rec['issue']}")
            print(f"   해결: {rec['solution']}")
            print(f"   효과: {rec['expected_impact']}")
            print()

        # 5. 즉시 실행 계획
        print("🎯 5. 즉시 실행해야 할 조치사항")
        print("-" * 50)

        if log_analysis['balance_info']:
            current_balance = int(
                log_analysis['balance_info'][1].replace(',', ''))
            min_balance = int(log_analysis['balance_info'][2].replace(',', ''))
            needed_amount = min_balance - current_balance

            print(f"💰 즉시 조치: {needed_amount:,}원 이상 추가 입금 필요")
            print(f"   현재 잔고: {current_balance:,}원")
            print(f"   최소 요구: {min_balance:,}원")
            print(f"   권장 입금: {needed_amount + 50000:,}원 (여유자금 포함)")

        print(f"\n🔧 시스템 최적화:")
        print(f"   1. 신호 임계값 조정으로 거래 빈도 최적화")
        print(f"   2. 리스크 관리 강화")
        print(f"   3. 다중 시간대 분석 도입")

        print()
        print("=" * 80)
        print("📝 분석 완료! 위 권장사항을 단계적으로 적용하세요.")
        print("=" * 80)


if __name__ == "__main__":
    analyzer = InvestmentAnalysisReport()
    analyzer.generate_report()
