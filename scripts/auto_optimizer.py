#!/usr/bin/env python3
"""
🤖 Auto-Optimization Engine for Auto-Coin Trading Bot

동적 자동 최적화 시스템:
- 실시간 성능 모니터링
- 자동 매개변수 조정
- 학습 기반 전략 개선
- 무중단 운영 중 최적화
"""

import sys
import threading
import time
import sqlite3
import json
import logging
import yaml
import psutil
import pyupbit
from datetime import datetime, timedelta
from pathlib import Path
import numpy as np
import os

# 프로젝트 루트 경로 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / 'modules'))
sys.path.insert(0, str(project_root / 'scripts'))

try:
    from modules import ConfigManager, LearningSystem
    from scripts.real_upbit_analyzer import UpbitDataSyncManager
except ImportError:
    # fallback imports
    from config_manager import ConfigManager
    from learning_system import LearningSystem
    from real_upbit_analyzer import UpbitDataSyncManager


class DateTimeEncoder(json.JSONEncoder):
    """DateTime 객체를 JSON으로 serialize하기 위한 encoder"""

    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)


class AutoOptimizationEngine:
    """자동 최적화 엔진"""

    def __init__(self):
        self.config = ConfigManager()
        self.learning = LearningSystem(self.config)

        # 업비트 동기화 매니저 추가 (정확한 데이터용)
        try:
            self.upbit_sync = UpbitDataSyncManager()
            self.use_real_data = True
            print("✅ 실제 업비트 데이터 연결 성공")
        except Exception as e:
            print(f"⚠️ 업비트 데이터 연결 실패, 로컬 데이터 사용: {e}")
            self.use_real_data = False
        self.running = False

        # 다층 최적화 간격 설정
        self.monitoring_interval = 120       # 2분 - 긴급 모니터링
        self.analysis_interval = 1800        # 30분 - 성능 분석
        self.optimization_interval = 7200    # 2시간 - 매개변수 조정
        self.learning_interval = 86400       # 24시간 - 심층 학습

        # 마지막 실행 시간 추적
        self.last_analysis = 0
        self.last_optimization = 0
        self.last_learning = 0

        self.analysis_thread = None

        # 최적화 이력 저장
        self.optimization_history = []
        self.performance_metrics = {
            'signal_efficiency': [],
            'profit_rates': [],
            'holding_times': [],
            'success_rates': []
        }

        # 설정 로그
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - [OPTIMIZER] - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('auto_optimizer.log', encoding='utf-8'),
                logging.StreamHandler()
            ]
        )

        self.logger = logging.getLogger(__name__)

    def start_optimization_engine(self):
        """최적화 엔진 시작"""
        self.running = True
        self.analysis_thread = threading.Thread(target=self._optimization_loop)
        self.analysis_thread.daemon = True
        self.analysis_thread.start()
        self.logger.info("🚀 자동 최적화 엔진 시작")

    def stop_optimization_engine(self):
        """최적화 엔진 중지"""
        self.running = False
        if self.analysis_thread:
            self.analysis_thread.join()
        self.logger.info("⏹️ 자동 최적화 엔진 중지")

    def _optimization_loop(self):
        """다층 최적화 메인 루프"""
        while self.running:
            try:
                current_time = time.time()

                # 🚨 긴급 모니터링 (2분마다)
                self._urgent_monitoring()

                # 📈 성능 분석 (30분마다)
                if current_time - self.last_analysis >= self.analysis_interval:
                    self.logger.info("📈 성능 분석 시작 (30분 주기)")
                    performance = self._analyze_current_performance()
                    self._record_performance_metrics(performance)
                    self.last_analysis = current_time

                # 🔧 매개변수 최적화 (2시간마다)
                if current_time - self.last_optimization >= self.optimization_interval:
                    self.logger.info("🔧 매개변수 최적화 시작 (2시간 주기)")
                    performance = self._analyze_current_performance()
                    improvements = self._identify_improvements(performance)
                    self._apply_automatic_improvements(improvements)
                    self._record_optimization_results(
                        performance, improvements)
                    self.last_optimization = current_time

                # 🧠 심층 학습 (24시간마다)
                if current_time - self.last_learning >= self.learning_interval:
                    self.logger.info("🧠 심층 학습 시작 (24시간 주기)")
                    self._deep_learning_optimization()
                    self.last_learning = current_time

            except Exception as e:
                self.logger.error(f"❌ 최적화 중 오류: {e}")
                import traceback
                self.logger.error(f"상세 오류: {traceback.format_exc()}")

            # 다음 모니터링까지 대기 (2분)
            time.sleep(self.monitoring_interval)

    def _urgent_monitoring(self):
        """🚨 긴급 모니터링 (2분마다)"""
        try:
            # 1. 매도 조건 충족 확인
            performance = self._analyze_current_performance()
            pending_analysis = performance.get('pending_analysis', [])
            sellable_positions = [
                p for p in pending_analysis if p.get('should_sell', False)]

            if sellable_positions:
                self.logger.info(f"🚨 긴급: {len(sellable_positions)}개 매도 조건 충족")
                self._trigger_sell_positions(sellable_positions)

            # 2. 시스템 헬스 체크
            memory_mb = performance.get('memory_usage_mb', 0)
            if memory_mb > 300:  # 300MB 초과 시
                self.logger.warning(f"⚠️ 메모리 사용량 주의: {memory_mb:.1f}MB")
                self._optimize_memory_usage()

        except Exception as e:
            self.logger.error(f"긴급 모니터링 오류: {e}")

    def _deep_learning_optimization(self):
        """🧠 심층 학습 최적화 (24시간마다)"""
        try:
            self.logger.info("🧠 심층 패턴 분석 및 전략 재구성")

            # 24시간 데이터 기반 전략 재평가
            performance_history = self.optimization_history[-24:] if len(
                self.optimization_history) >= 24 else self.optimization_history

            if len(performance_history) >= 5:
                # 성공률 분석
                avg_efficiency = sum(p.get('performance', {}).get('signal_efficiency', {}).get(
                    'efficiency', 0) for p in performance_history) / len(performance_history)

                if avg_efficiency < 0.1:  # 10% 미만
                    self.logger.info("📊 전략 재구성 필요 - 성공률 낮음")
                    self._restructure_strategy()

        except Exception as e:
            self.logger.error(f"심층 학습 오류: {e}")

    def _restructure_strategy(self):
        """전략 재구성"""
        try:
            # RSI 임계값 대폭 조정
            current_params = self.learning.adaptive_params.copy()
            current_params['rsi_buy_threshold'] = 25  # 더 보수적으로
            current_params['min_profit_target'] = 0.01  # 1%로 낮춤

            self.learning.adaptive_params = current_params
            self.logger.info("🔄 전략 재구성 완료: 더 보수적인 매개변수 적용")

        except Exception as e:
            self.logger.error(f"전략 재구성 오류: {e}")

    def _record_performance_metrics(self, performance):
        """성능 메트릭 기록"""
        try:
            signal_eff = performance.get('signal_efficiency', {})
            self.performance_metrics['signal_efficiency'].append(
                signal_eff.get('efficiency', 0))

            # 최근 50개 데이터만 유지
            for key in self.performance_metrics:
                if len(self.performance_metrics[key]) > 50:
                    self.performance_metrics[key] = self.performance_metrics[key][-50:]

        except Exception as e:
            self.logger.error(f"성능 메트릭 기록 오류: {e}")

    def _analyze_current_performance(self):
        """현재 성능 분석 (실제 업비트 데이터 기반)"""
        try:
            # 변수 초기화
            recent_trades = []
            pending_trades = []
            total_unrealized_profit = 0
            pending_analysis = []

            if self.use_real_data:
                # 실제 업비트 데이터 분석
                print("📊 실제 업비트 데이터로 성능 분석 중...")

                # 포트폴리오 현재 상태
                portfolio_data = self.upbit_sync.get_investment_summary()
                current_roi = portfolio_data.get('roi_percentage', 0)

                # 실제 데이터 기반이므로 portfolio_data에서 직접 정보 추출
                print(f"실제 ROI: {current_roi:.2f}%")
                print(
                    f"총 손익: {portfolio_data.get('total_profit_loss', 0):,.0f}원")

            else:
                # 기존 로컬 데이터 분석 (fallback)
                print("📊 로컬 데이터로 성능 분석 중...")
                conn = sqlite3.connect(self.learning.db_path)
                cursor = conn.cursor()

                # 최근 24시간 데이터
                since_time = datetime.now() - timedelta(hours=24)
                cursor.execute("""
                    SELECT * FROM trades 
                    WHERE timestamp > ? 
                    ORDER BY timestamp DESC
                """, (since_time.isoformat(),))

                recent_trades = cursor.fetchall()

                # 미완료 거래 분석
                cursor.execute("SELECT * FROM trades WHERE success IS NULL")
                pending_trades = cursor.fetchall()

                conn.close()

                # 실시간 수익률 계산
                for trade in pending_trades:
                    try:
                        coin = trade[2]
                        buy_price = trade[5]
                        amount = trade[6]
                        buy_time = datetime.fromisoformat(trade[1])

                        current_price = pyupbit.get_current_price(coin)
                        if current_price:
                            profit_rate = (current_price -
                                           buy_price) / buy_price
                            holding_hours = (datetime.now() -
                                             buy_time).total_seconds() / 3600

                            total_unrealized_profit += profit_rate
                            pending_analysis.append({
                                'coin': coin,
                                'profit_rate': profit_rate,
                                'holding_hours': holding_hours,
                                'should_sell': self._should_sell_analysis(profit_rate, holding_hours)
                            })
                    except:
                        continue

            # 로그 분석 (신호 효율성)
            signal_efficiency = self._analyze_signal_efficiency()

            # 시스템 리소스 분석
            process = psutil.Process()
            memory_usage = process.memory_info().rss / 1024**2
            cpu_percent = process.cpu_percent()

            return {
                'recent_trades_count': len(recent_trades),
                'pending_trades_count': len(pending_trades),
                'avg_unrealized_profit': total_unrealized_profit / len(pending_trades) if pending_trades else 0,
                'pending_analysis': pending_analysis,
                'signal_efficiency': signal_efficiency,
                'memory_usage_mb': memory_usage,
                'cpu_percent': cpu_percent,
                'analysis_time': datetime.now().isoformat()
            }

        except Exception as e:
            self.logger.error(f"성능 분석 오류: {e}")
            return {}

    def _analyze_signal_efficiency(self):
        """신호 효율성 분석"""
        try:
            if not os.path.exists('auto_trader.log'):
                return {'efficiency': 0, 'total_signals': 0, 'failed_signals': 0}

            with open('auto_trader.log', 'r', encoding='utf-8') as f:
                lines = f.readlines()

            # 최근 1시간 데이터만 분석
            recent_hour = datetime.now() - timedelta(hours=1)
            recent_lines = [
                l for l in lines if recent_hour.strftime('%Y-%m-%d %H:') in l]

            signal_lines = [l for l in recent_lines if '신호 발생' in l]
            failed_lines = [l for l in recent_lines if '잔고 부족' in l]

            total_signals = len(signal_lines)
            failed_signals = len(failed_lines)
            efficiency = (total_signals - failed_signals) / \
                total_signals if total_signals > 0 else 0

            return {
                'efficiency': efficiency,
                'total_signals': total_signals,
                'failed_signals': failed_signals
            }

        except Exception as e:
            self.logger.error(f"신호 효율성 분석 오류: {e}")
            return {'efficiency': 0, 'total_signals': 0, 'failed_signals': 0}

    def _should_sell_analysis(self, profit_rate, holding_hours):
        """매도 판단 분석"""
        current_target = self.config.get('trading.profit_target_ratio', 0.02)
        max_hold_hours = 72  # 기본 72시간

        # 동적 매도 조건
        conditions = {
            'profit_target_met': profit_rate >= current_target,
            'time_expired': holding_hours >= max_hold_hours,
            'high_profit': profit_rate >= current_target * 2,  # 목표의 2배 수익
            'should_sell': False
        }

        # 매도 권장 로직
        if conditions['high_profit'] or conditions['time_expired']:
            conditions['should_sell'] = True
        elif conditions['profit_target_met'] and holding_hours >= 24:
            conditions['should_sell'] = True

        return conditions

    def _identify_improvements(self, performance):
        """개선점 식별"""
        improvements = []

        if not performance:
            return improvements

        # 1. 미실현 수익 처리
        pending_analysis = performance.get('pending_analysis', [])
        sellable_positions = [p for p in pending_analysis if p['should_sell']]

        if sellable_positions:
            improvements.append({
                'type': 'SELL_POSITIONS',
                'priority': 'HIGH',
                'data': sellable_positions,
                'reason': f"{len(sellable_positions)}개 포지션이 매도 조건 충족"
            })

        # 2. 신호 효율성 개선
        signal_eff = performance.get('signal_efficiency', {})
        if signal_eff.get('efficiency', 0) < 0.1 and signal_eff.get('total_signals', 0) > 10:
            improvements.append({
                'type': 'ADJUST_SIGNAL_PARAMS',
                'priority': 'MEDIUM',
                'data': {
                    'current_efficiency': signal_eff['efficiency'],
                    'failed_ratio': signal_eff['failed_signals'] / signal_eff['total_signals']
                },
                'reason': f"신호 효율성 {signal_eff['efficiency']:.1%} (목표: 10% 이상)"
            })

        # 3. 메모리 사용량 최적화
        if performance.get('memory_usage_mb', 0) > 200:
            improvements.append({
                'type': 'MEMORY_OPTIMIZATION',
                'priority': 'LOW',
                'data': {'memory_mb': performance['memory_usage_mb']},
                'reason': f"메모리 사용량 {performance['memory_usage_mb']:.1f}MB (권장: 200MB 이하)"
            })

        return improvements

    def _apply_automatic_improvements(self, improvements):
        """자동 개선 적용"""
        for improvement in improvements:
            try:
                if improvement['type'] == 'SELL_POSITIONS':
                    self._trigger_sell_positions(improvement['data'])

                elif improvement['type'] == 'ADJUST_SIGNAL_PARAMS':
                    self._adjust_signal_parameters(improvement['data'])

                elif improvement['type'] == 'MEMORY_OPTIMIZATION':
                    self._optimize_memory_usage()

                self.logger.info(
                    f"✅ 개선 적용: {improvement['type']} - {improvement['reason']}")

            except Exception as e:
                self.logger.error(f"❌ 개선 적용 실패 ({improvement['type']}): {e}")

    def _trigger_sell_positions(self, sellable_positions):
        """매도 포지션 트리거"""
        # 실제 매도 로직은 메인 트레이딩 엔진에서 처리하도록 신호 생성
        sell_signals = []

        for position in sellable_positions:
            sell_signals.append({
                'coin': position['coin'],
                'reason': 'auto_optimization',
                'profit_rate': position['profit_rate'],
                'holding_hours': position['holding_hours']
            })

        # 매도 신호 파일 생성 (트레이딩 엔진이 읽어서 처리)
        with open('sell_signals.json', 'w', encoding='utf-8') as f:
            json.dump(sell_signals, f, ensure_ascii=False,
                      indent=2, cls=DateTimeEncoder)

        self.logger.info(f"📤 {len(sell_signals)}개 매도 신호 생성")

    def _adjust_signal_parameters(self, data):
        """신호 매개변수 조정"""
        try:
            # 현재 설정 로드
            current_params = self.learning.adaptive_params.copy()

            # 효율성이 낮으면 임계값을 더 보수적으로 조정
            failed_ratio = data['failed_ratio']

            if failed_ratio > 0.8:  # 80% 이상 실패
                # RSI 임계값을 더 보수적으로
                current_params['rsi_buy_threshold'] = min(
                    35, current_params.get('rsi_buy_threshold', 30) + 2)
                current_params['min_profit_target'] = max(
                    0.015, current_params.get('min_profit_target', 0.02) - 0.002)

                # 학습 시스템에 반영
                self.learning.adaptive_params = current_params

                self.logger.info(
                    f"📊 신호 매개변수 조정: RSI={current_params['rsi_buy_threshold']}, 목표수익={current_params['min_profit_target']:.1%}")

        except Exception as e:
            self.logger.error(f"매개변수 조정 오류: {e}")

    def _optimize_memory_usage(self):
        """메모리 사용량 최적화"""
        try:
            import gc

            # 가비지 컬렉션 강제 실행
            collected = gc.collect()

            # 메모리 상태 확인
            process = psutil.Process()
            memory_after = process.memory_info().rss / 1024**2

            self.logger.info(
                f"🧹 메모리 최적화: {collected}개 객체 정리, 현재 사용량: {memory_after:.1f}MB")

        except Exception as e:
            self.logger.error(f"메모리 최적화 오류: {e}")

    def _record_optimization_results(self, performance, improvements):
        """최적화 결과 기록"""
        result = {
            'timestamp': datetime.now().isoformat(),
            'performance': performance,
            'improvements_applied': len(improvements),
            'improvement_types': [imp['type'] for imp in improvements]
        }

        self.optimization_history.append(result)

        # 이력이 너무 길면 오래된 것 삭제
        if len(self.optimization_history) > 100:
            self.optimization_history = self.optimization_history[-50:]

        # 파일로 저장
        with open('optimization_history.json', 'w', encoding='utf-8') as f:
            json.dump(self.optimization_history, f,
                      ensure_ascii=False, indent=2, cls=DateTimeEncoder)

    def generate_optimization_report(self):
        """최적화 리포트 생성"""
        if not self.optimization_history:
            return "아직 최적화 이력이 없습니다."

        recent_optimizations = self.optimization_history[-10:]

        report = []
        report.append("🤖 자동 최적화 엔진 리포트")
        report.append("=" * 50)
        report.append(f"📊 총 최적화 실행: {len(self.optimization_history)}회")
        report.append(f"⏰ 마지막 실행: {recent_optimizations[-1]['timestamp']}")

        # 개선 유형별 통계
        improvement_counts = {}
        for opt in recent_optimizations:
            for imp_type in opt['improvement_types']:
                improvement_counts[imp_type] = improvement_counts.get(
                    imp_type, 0) + 1

        if improvement_counts:
            report.append("\n📈 최근 개선 유형별 통계:")
            for imp_type, count in improvement_counts.items():
                report.append(f"   {imp_type}: {count}회")

        return "\n".join(report)


def main():
    """메인 실행 함수"""
    print("🤖 Auto-Optimization Engine 시작")

    optimizer = AutoOptimizationEngine()

    try:
        # 즉시 1회 분석 실행
        print("🔍 초기 성능 분석 중...")
        performance = optimizer._analyze_current_performance()
        improvements = optimizer._identify_improvements(performance)

        if improvements:
            print(f"📋 {len(improvements)}개 개선사항 발견:")
            for i, imp in enumerate(improvements, 1):
                print(f"   {i}. {imp['type']}: {imp['reason']}")

            # 개선사항 적용
            optimizer._apply_automatic_improvements(improvements)
            print("✅ 개선사항 적용 완료")
        else:
            print("✅ 현재 상태 양호 - 개선사항 없음")

        # 연속 모니터링 시작
        optimizer.start_optimization_engine()

        print("🔄 다층 자동 최적화 시스템 가동 중...")
        print("📋 최적화 간격:")
        print("   🚨 긴급 모니터링: 2분마다")
        print("   📈 성능 분석: 30분마다")
        print("   🔧 매개변수 최적화: 2시간마다")
        print("   🧠 심층 학습: 24시간마다")
        print("Ctrl+C로 중지할 수 있습니다.")

        # 메인 루프
        status_counter = 0
        while True:
            time.sleep(60)  # 1분마다 상태 출력
            status_counter += 1

            if status_counter % 5 == 0:  # 5분마다 상태 출력
                current_time = datetime.now()
                print(
                    f"⏰ {current_time.strftime('%H:%M:%S')} - 다층 최적화 시스템 실행 중...")

                # 다음 최적화까지 남은 시간 표시
                next_analysis = (optimizer.last_analysis +
                                 optimizer.analysis_interval - time.time()) // 60
                next_optimization = (
                    optimizer.last_optimization + optimizer.optimization_interval - time.time()) // 60

                if next_analysis > 0:
                    print(f"   📈 다음 성능 분석: {int(next_analysis)}분 후")
                if next_optimization > 0:
                    print(f"   🔧 다음 매개변수 최적화: {int(next_optimization)}분 후")

    except KeyboardInterrupt:
        print("\n⏹️ 사용자에 의한 중지")
        optimizer.stop_optimization_engine()

        # 최종 리포트 출력
        print("\n" + optimizer.generate_optimization_report())

    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        optimizer.stop_optimization_engine()


if __name__ == "__main__":
    main()
