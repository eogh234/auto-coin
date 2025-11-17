"""
성과 분석기 모듈
"""

from .learning_system import LearningSystem


class PerformanceAnalyzer:
    """성과 분석기"""

    def __init__(self, learning_system: LearningSystem):
        self.learning = learning_system

    def show_performance_report(self, days: int = 7):
        """성과 분석 리포트 출력"""
        print(f"\n📈 성과 분석 리포트 (최근 {days}일)")
        print("=" * 50)

        try:
            report = self.learning.get_performance_report(days)

            if report['total_trades'] == 0:
                print("분석할 거래 데이터가 없습니다.")
                return

            print(f"📊 기본 통계:")
            print(f"  • 총 거래: {report['total_trades']}회")
            print(f"  • 성공률: {report['success_rate']:.1%}")
            print(f"  • 평균 수익률: {report['avg_profit_rate']:+.2%}")
            print(f"  • 최고 거래: {report['best_trade']:+.2%}")
            print(f"  • 최악 거래: {report['worst_trade']:+.2%}")

            print(f"\n🧠 현재 적응형 매개변수:")
            params = report['current_params']
            print(f"  • RSI 매수 임계값: {params.get('rsi_buy_threshold', 30)}")
            print(f"  • RSI 매도 임계값: {params.get('rsi_sell_threshold', 70)}")
            print(
                f"  • 볼린저 매수 비율: {params.get('bollinger_buy_ratio', 0.2):.2f}")
            print(f"  • 목표 수익률: {params.get('min_profit_target', 0.02):.1%}")
            print(
                f"  • 손절 임계값: {params.get('stop_loss_threshold', -0.05):.1%}")

            print(f"\n💾 시스템 상태:")
            print(f"  • 메모리 사용률: {report['memory_usage']:.1f}%")

        except Exception as e:
            print(f"성과 분석 중 오류 발생: {e}")
