#!/usr/bin/env python3
"""
🔄 Trading Bot Data Sync Integration

트레이딩 봇과 업비트 데이터 동기화 통합:
- 봇 시작 시 자동 데이터 동기화
- 주기적 실제 데이터 검증
- 로컬 DB와 업비트 API 일관성 유지
"""

import sys
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path

# 프로젝트 루트 경로 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from scripts.real_upbit_analyzer import UpbitDataSyncManager
    from modules import ConfigManager, LearningSystem
except ImportError:
    sys.path.insert(0, str(project_root / 'modules'))
    sys.path.insert(0, str(project_root / 'scripts'))
    from real_upbit_analyzer import UpbitDataSyncManager
    from config_manager import ConfigManager
    from learning_system import LearningSystem


class DataSyncIntegration:
    """데이터 동기화 통합 매니저"""
    
    def __init__(self, trading_bot_instance=None):
        self.trading_bot = trading_bot_instance
        self.sync_manager = UpbitDataSyncManager()
        self.config = ConfigManager()
        
        # 동기화 설정
        self.auto_sync_interval = 1800  # 30분마다
        self.validation_interval = 3600  # 1시간마다
        
        # 동기화 스레드
        self.sync_thread = None
        self.running = False
        
        print("✅ 데이터 동기화 통합 매니저 초기화 완료")
    
    def initialize_on_startup(self):
        """봇 시작 시 초기 동기화"""
        print("\n🚀 트레이딩 봇 시작 시 데이터 동기화...")
        
        try:
            # 1. 업비트 데이터 전체 동기화
            print("📥 업비트 실제 데이터 동기화 중...")
            self.sync_manager.sync_all_data()
            
            # 2. 로컬 DB 검증
            self._validate_local_data()
            
            # 3. 불일치 데이터 수정
            self._reconcile_data_inconsistencies()
            
            print("✅ 시작 시 데이터 동기화 완료")
            
        except Exception as e:
            print(f"❌ 시작 시 동기화 실패: {e}")
            # 동기화 실패해도 봇은 계속 실행
    
    def start_background_sync(self):
        """백그라운드 자동 동기화 시작"""
        if self.running:
            return
        
        self.running = True
        self.sync_thread = threading.Thread(target=self._background_sync_loop)
        self.sync_thread.daemon = True
        self.sync_thread.start()
        
        print("🔄 백그라운드 데이터 동기화 시작")
    
    def stop_background_sync(self):
        """백그라운드 동기화 중지"""
        self.running = False
        if self.sync_thread:
            self.sync_thread.join()
        
        print("⏹️ 백그라운드 데이터 동기화 중지")
    
    def _background_sync_loop(self):
        """백그라운드 동기화 루프"""
        last_sync = 0
        last_validation = 0
        
        while self.running:
            try:
                current_time = time.time()
                
                # 정기 동기화 (30분마다)
                if current_time - last_sync >= self.auto_sync_interval:
                    print("🔄 정기 업비트 데이터 동기화...")
                    self.sync_manager.sync_all_data()
                    last_sync = current_time
                
                # 데이터 검증 (1시간마다)
                if current_time - last_validation >= self.validation_interval:
                    print("🔍 데이터 무결성 검증...")
                    self._validate_local_data()
                    last_validation = current_time
                
                time.sleep(60)  # 1분마다 체크
                
            except Exception as e:
                print(f"❌ 백그라운드 동기화 오류: {e}")
                time.sleep(300)  # 5분 후 재시도
    
    def _validate_local_data(self):
        """로컬 데이터 검증"""
        try:
            # 업비트 API에서 최신 잔고 조회
            api_balances = self.sync_manager.upbit.get_balances()
            
            # 로컬 DB에서 최신 포트폴리오 조회
            summary = self.sync_manager.get_investment_summary()
            
            if not summary:
                print("⚠️ 로컬 데이터 없음 - 전체 동기화 필요")
                return False
            
            local_portfolio = {item[0]: item[1] for item in summary['portfolio']}
            
            # 잔고 비교
            discrepancies = []
            
            for api_balance in api_balances:
                currency = api_balance['currency']
                api_amount = float(api_balance['balance']) + float(api_balance['locked'])
                local_amount = local_portfolio.get(currency, 0)
                
                if abs(api_amount - local_amount) > 0.000001:  # 소수점 오차 고려
                    discrepancies.append({
                        'currency': currency,
                        'api_amount': api_amount,
                        'local_amount': local_amount,
                        'difference': api_amount - local_amount
                    })
            
            if discrepancies:
                print(f"⚠️ 데이터 불일치 발견: {len(discrepancies)}건")
                for disc in discrepancies:
                    print(f"   {disc['currency']}: API={disc['api_amount']:.6f}, Local={disc['local_amount']:.6f}")
                return False
            else:
                print("✅ 데이터 무결성 검증 통과")
                return True
                
        except Exception as e:
            print(f"❌ 데이터 검증 오류: {e}")
            return False
    
    def _reconcile_data_inconsistencies(self):
        """데이터 불일치 해결"""
        try:
            print("🔧 데이터 불일치 해결 중...")
            
            # 업비트를 신뢰할 수 있는 소스로 간주하고 전체 재동기화
            self.sync_manager.sync_current_portfolio()
            self.sync_manager.calculate_investment_performance()
            
            print("✅ 데이터 불일치 해결 완료")
            
        except Exception as e:
            print(f"❌ 데이터 불일치 해결 실패: {e}")
    
    def get_reliable_balance(self, currency='KRW'):
        """신뢰할 수 있는 잔고 조회 (업비트 API 우선)"""
        try:
            # 업비트 API에서 직접 조회
            balances = self.sync_manager.upbit.get_balances()
            
            for balance in balances:
                if balance['currency'] == currency:
                    total_amount = float(balance['balance']) + float(balance['locked'])
                    return total_amount
            
            return 0
            
        except Exception as e:
            print(f"❌ 신뢰 잔고 조회 오류: {e}")
            # API 실패 시 로컬 DB에서 조회
            summary = self.sync_manager.get_investment_summary()
            if summary and summary['portfolio']:
                for curr, amount, krw_value in summary['portfolio']:
                    if curr == currency:
                        return amount if currency == 'KRW' else amount
            return 0
    
    def get_real_investment_performance(self):
        """실제 투자 성과 조회"""
        try:
            # 최신 동기화 먼저 실행
            self.sync_manager.sync_current_portfolio()
            self.sync_manager.calculate_investment_performance()
            
            # 성과 데이터 조회
            summary = self.sync_manager.get_investment_summary()
            
            if summary:
                return summary['performance']
            else:
                return None
                
        except Exception as e:
            print(f"❌ 실제 성과 조회 오류: {e}")
            return None
    
    def log_trade_execution(self, trade_data):
        """거래 실행 시 로그 (향후 검증용)"""
        try:
            # 거래 실행 즉시 업비트에서 최신 데이터 동기화
            time.sleep(1)  # 1초 후 동기화 (API 반영 시간)
            
            self.sync_manager.sync_current_portfolio()
            
            print(f"✅ 거래 후 포트폴리오 동기화 완료: {trade_data.get('market', 'Unknown')}")
            
        except Exception as e:
            print(f"❌ 거래 후 동기화 오류: {e}")
    
    def generate_sync_status_report(self):
        """동기화 상태 리포트"""
        try:
            report = []
            report.append("🔄 데이터 동기화 상태 리포트")
            report.append("=" * 40)
            report.append(f"📅 리포트 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            
            # 동기화 상태 조회
            import sqlite3
            conn = sqlite3.connect(self.sync_manager.db_path)
            cursor = conn.cursor()
            
            cursor.execute("SELECT * FROM sync_status")
            sync_statuses = cursor.fetchall()
            
            if sync_statuses:
                report.append("\n📊 동기화 이력:")
                for status in sync_statuses:
                    sync_type, last_sync, success, records, error = status
                    status_emoji = "✅" if success else "❌"
                    report.append(f"   {status_emoji} {sync_type}: {last_sync[:19]} ({records}건)")
                    if error:
                        report.append(f"      오류: {error}")
            
            # 데이터 무결성 체크
            validation_result = self._validate_local_data()
            validation_emoji = "✅" if validation_result else "⚠️"
            report.append(f"\n{validation_emoji} 데이터 무결성: {'정상' if validation_result else '불일치 감지'}")
            
            # 최신 투자 성과
            performance = self.get_real_investment_performance()
            if performance:
                report.append(f"\n💰 최신 투자 성과:")
                report.append(f"   📈 수익률: {performance['roi_percentage']:+.2f}%")
                report.append(f"   💹 손익: {performance['total_pnl']:,.0f}원")
            
            conn.close()
            return "\n".join(report)
            
        except Exception as e:
            return f"❌ 상태 리포트 생성 오류: {e}"


def integrate_with_trading_bot(trading_bot_instance):
    """트레이딩 봇과 통합"""
    print("🔗 트레이딩 봇과 데이터 동기화 통합 중...")
    
    # 데이터 동기화 통합 인스턴스 생성
    sync_integration = DataSyncIntegration(trading_bot_instance)
    
    # 시작 시 초기화
    sync_integration.initialize_on_startup()
    
    # 백그라운드 동기화 시작
    sync_integration.start_background_sync()
    
    return sync_integration


if __name__ == "__main__":
    # 독립 실행용 테스트
    print("🧪 데이터 동기화 통합 테스트")
    
    sync_integration = DataSyncIntegration()
    sync_integration.initialize_on_startup()
    
    # 상태 리포트 출력
    report = sync_integration.generate_sync_status_report()
    print(f"\n{report}")
    
    # 실제 성과 조회
    performance = sync_integration.get_real_investment_performance()
    if performance:
        print(f"\n💰 실제 투자 성과:")
        print(f"📈 수익률: {performance['roi_percentage']:+.2f}%")
        print(f"💹 총 손익: {performance['total_pnl']:,.0f}원")
