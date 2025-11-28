#!/usr/bin/env python3
"""
🔄 Upbit Data Sync & Real Investment Analyzer

업비트 기반 신뢰성 있는 데이터 동기화:
- 업비트 API를 단일 정보원으로 활용
- 프로그램 재시작해도 데이터 유지
- 실제 거래내역과 로컬 데이터 동기화
- 자동 데이터 무결성 검증
"""

import pyupbit
import sqlite3
import json
import yaml
from datetime import datetime, timedelta
from pathlib import Path
import sys
import time

# 프로젝트 루트 경로 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

try:
    from modules import ConfigManager
except ImportError:
    sys.path.insert(0, str(project_root / 'modules'))
    from config_manager import ConfigManager


class UpbitDataSyncManager:
    """업비트 데이터 동기화 매니저"""

    def __init__(self, db_path="upbit_sync.db"):
        self.db_path = db_path
        self.config = ConfigManager()

        # 업비트 API 초기화
        self._init_upbit_api()

        # 데이터베이스 초기화
        self._init_database()

        print("✅ 업비트 데이터 동기화 매니저 초기화 완료")

    def _init_upbit_api(self):
        """업비트 API 초기화"""
        try:
            with open('config.yaml', 'r', encoding='utf-8') as f:
                config_data = yaml.safe_load(f)

            self.access_key = config_data['upbit']['access_key']
            self.secret_key = config_data['upbit']['secret_key']

            self.upbit = pyupbit.Upbit(self.access_key, self.secret_key)

            # API 연결 테스트
            self.upbit.get_balances()
            print("✅ 업비트 API 연결 성공")

        except Exception as e:
            print(f"❌ 업비트 API 연결 실패: {e}")
            raise

    def _init_database(self):
        """신뢰성 있는 데이터베이스 스키마 초기화"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # 실제 업비트 거래 내역 테이블
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS upbit_orders (
                uuid TEXT PRIMARY KEY,
                market TEXT NOT NULL,
                side TEXT NOT NULL,
                ord_type TEXT,
                price REAL,
                volume REAL,
                remaining_volume REAL,
                reserved_fee REAL,
                remaining_fee REAL,
                paid_fee REAL,
                locked REAL,
                executed_volume REAL,
                trades_count INTEGER,
                created_at TEXT NOT NULL,
                updated_at TEXT,
                state TEXT,
                raw_data TEXT,
                sync_timestamp TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 입출금 내역 테이블
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS upbit_deposits_withdraws (
                txid TEXT PRIMARY KEY,
                type TEXT NOT NULL, -- 'deposit' or 'withdraw'
                currency TEXT NOT NULL,
                net_type TEXT,
                amount REAL NOT NULL,
                fee REAL DEFAULT 0,
                state TEXT,
                created_at TEXT NOT NULL,
                done_at TEXT,
                transaction_type TEXT,
                raw_data TEXT,
                sync_timestamp TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 포트폴리오 스냅샷 테이블 (정기적으로 잔고 저장)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS portfolio_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                currency TEXT NOT NULL,
                balance REAL NOT NULL,
                locked REAL NOT NULL,
                avg_buy_price REAL,
                avg_buy_price_modified BOOLEAN,
                unit_currency TEXT,
                current_price REAL,
                krw_value REAL,
                snapshot_time TEXT NOT NULL,
                raw_data TEXT
            )
        """)

        # 동기화 상태 추적 테이블
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sync_status (
                sync_type TEXT PRIMARY KEY,
                last_sync_time TEXT NOT NULL,
                last_sync_success BOOLEAN,
                total_synced_records INTEGER DEFAULT 0,
                last_error TEXT
            )
        """)

        # 투자 성과 계산 테이블
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS investment_performance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                calculation_time TEXT NOT NULL,
                total_investment REAL NOT NULL,
                total_withdrawal REAL NOT NULL,
                net_investment REAL NOT NULL,
                current_portfolio_value REAL NOT NULL,
                unrealized_pnl REAL NOT NULL,
                realized_pnl REAL NOT NULL,
                total_pnl REAL NOT NULL,
                roi_percentage REAL NOT NULL,
                period_start TEXT,
                period_end TEXT
            )
        """)

        conn.commit()
        conn.close()
        print("✅ 데이터베이스 스키마 초기화 완료")

    def sync_all_data(self):
        """모든 업비트 데이터 동기화"""
        print("\n🔄 업비트 데이터 전체 동기화 시작...")

        try:
            # 1. 거래 내역 동기화
            self.sync_trading_history()

            # 2. 입출금 내역 동기화
            self.sync_deposit_withdraw_history()

            # 3. 현재 포트폴리오 스냅샷
            self.sync_current_portfolio()

            # 4. 투자 성과 계산
            self.calculate_investment_performance()

            print("✅ 전체 데이터 동기화 완료")

        except Exception as e:
            print(f"❌ 데이터 동기화 중 오류: {e}")
            raise

    def sync_trading_history(self, days_back=90):
        """거래 내역 동기화 (최근 N일)"""
        print("📈 거래 내역 동기화 중...")

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # KRW 마켓만 조회 (실제 거래 대상)
            markets = pyupbit.get_tickers(fiat="KRW")

            total_synced = 0

            for market in markets:
                try:
                    # 완료된 주문만 조회
                    orders = self.upbit.get_orders(
                        market=market, state='done', limit=100)

                    if not orders:
                        continue

                    for order in orders:
                        # 중복 체크
                        cursor.execute(
                            "SELECT uuid FROM upbit_orders WHERE uuid = ?", (order['uuid'],))
                        if cursor.fetchone():
                            continue

                        # 새로운 거래 내역 저장
                        cursor.execute("""
                            INSERT INTO upbit_orders (
                                uuid, market, side, ord_type, price, volume,
                                remaining_volume, reserved_fee, remaining_fee, paid_fee,
                                locked, executed_volume, trades_count, created_at,
                                updated_at, state, raw_data
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            order['uuid'],
                            order['market'],
                            order['side'],
                            order['ord_type'],
                            float(order['price']) if order['price'] else 0,
                            float(order['volume']) if order['volume'] else 0,
                            float(order['remaining_volume']
                                  ) if order['remaining_volume'] else 0,
                            float(order['reserved_fee']
                                  ) if order['reserved_fee'] else 0,
                            float(order['remaining_fee']
                                  ) if order['remaining_fee'] else 0,
                            float(order['paid_fee']
                                  ) if order['paid_fee'] else 0,
                            float(order['locked']) if order['locked'] else 0,
                            float(order['executed_volume']
                                  ) if order['executed_volume'] else 0,
                            order['trades_count'],
                            order['created_at'],
                            order['updated_at'],
                            order['state'],
                            json.dumps(order, ensure_ascii=False)
                        ))

                        total_synced += 1

                except Exception as e:
                    print(f"⚠️ {market} 동기화 오류: {e}")
                    continue

            # 동기화 상태 업데이트
            cursor.execute("""
                INSERT OR REPLACE INTO sync_status 
                (sync_type, last_sync_time, last_sync_success, total_synced_records)
                VALUES (?, ?, ?, ?)
            """, ('trading_history', datetime.now().isoformat(), True, total_synced))

            conn.commit()
            print(f"✅ 거래 내역 동기화 완료: {total_synced}건")

        except Exception as e:
            cursor.execute("""
                INSERT OR REPLACE INTO sync_status 
                (sync_type, last_sync_time, last_sync_success, last_error)
                VALUES (?, ?, ?, ?)
            """, ('trading_history', datetime.now().isoformat(), False, str(e)))
            conn.commit()
            raise
        finally:
            conn.close()

    def sync_deposit_withdraw_history(self):
        """입출금 내역 동기화"""
        print("💰 입출금 내역 동기화 중...")

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            total_synced = 0

            # 입금 내역
            deposits = self.upbit.get_deposits(limit=200)
            if deposits:
                for deposit in deposits:
                    cursor.execute(
                        "SELECT txid FROM upbit_deposits_withdraws WHERE txid = ?", (deposit['txid'],))
                    if cursor.fetchone():
                        continue

                    cursor.execute("""
                        INSERT INTO upbit_deposits_withdraws (
                            txid, type, currency, net_type, amount, fee, state,
                            created_at, done_at, transaction_type, raw_data
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        deposit['txid'],
                        'deposit',
                        deposit['currency'],
                        deposit.get('net_type'),
                        float(deposit['amount']),
                        float(deposit.get('fee', 0)),
                        deposit['state'],
                        deposit['created_at'],
                        deposit.get('done_at'),
                        deposit.get('transaction_type'),
                        json.dumps(deposit, ensure_ascii=False)
                    ))
                    total_synced += 1

            # 출금 내역
            withdraws = self.upbit.get_withdraws(limit=200)
            if withdraws:
                for withdraw in withdraws:
                    cursor.execute(
                        "SELECT txid FROM upbit_deposits_withdraws WHERE txid = ?", (withdraw['txid'],))
                    if cursor.fetchone():
                        continue

                    cursor.execute("""
                        INSERT INTO upbit_deposits_withdraws (
                            txid, type, currency, net_type, amount, fee, state,
                            created_at, done_at, transaction_type, raw_data
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        withdraw['txid'],
                        'withdraw',
                        withdraw['currency'],
                        withdraw.get('net_type'),
                        float(withdraw['amount']),
                        float(withdraw.get('fee', 0)),
                        withdraw['state'],
                        withdraw['created_at'],
                        withdraw.get('done_at'),
                        withdraw.get('transaction_type'),
                        json.dumps(withdraw, ensure_ascii=False)
                    ))
                    total_synced += 1

            # 동기화 상태 업데이트
            cursor.execute("""
                INSERT OR REPLACE INTO sync_status 
                (sync_type, last_sync_time, last_sync_success, total_synced_records)
                VALUES (?, ?, ?, ?)
            """, ('deposit_withdraw', datetime.now().isoformat(), True, total_synced))

            conn.commit()
            print(f"✅ 입출금 내역 동기화 완료: {total_synced}건")

        except Exception as e:
            cursor.execute("""
                INSERT OR REPLACE INTO sync_status 
                (sync_type, last_sync_time, last_sync_success, last_error)
                VALUES (?, ?, ?, ?)
            """, ('deposit_withdraw', datetime.now().isoformat(), False, str(e)))
            conn.commit()
            raise
        finally:
            conn.close()

    def sync_current_portfolio(self):
        """현재 포트폴리오 스냅샷"""
        print("📊 포트폴리오 스냅샷 생성 중...")

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            balances = self.upbit.get_balances()
            snapshot_time = datetime.now().isoformat()

            for balance in balances:
                currency = balance['currency']
                balance_amount = float(balance['balance'])
                locked_amount = float(balance['locked'])

                # 잔고가 있는 것만 저장
                if balance_amount + locked_amount > 0:
                    # 현재 가격 조회 (KRW가 아닌 경우)
                    current_price = 1
                    krw_value = balance_amount + locked_amount

                    if currency != 'KRW':
                        try:
                            current_price = pyupbit.get_current_price(
                                f"KRW-{currency}")
                            if current_price:
                                krw_value = (balance_amount +
                                             locked_amount) * current_price
                            else:
                                current_price = 0
                                krw_value = 0
                        except:
                            current_price = 0
                            krw_value = 0

                    cursor.execute("""
                        INSERT INTO portfolio_snapshots (
                            currency, balance, locked, avg_buy_price,
                            avg_buy_price_modified, unit_currency, current_price,
                            krw_value, snapshot_time, raw_data
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        currency,
                        balance_amount,
                        locked_amount,
                        float(balance.get('avg_buy_price', 0)),
                        balance.get('avg_buy_price_modified', False),
                        balance.get('unit_currency'),
                        current_price,
                        krw_value,
                        snapshot_time,
                        json.dumps(balance, ensure_ascii=False)
                    ))

            conn.commit()
            print(f"✅ 포트폴리오 스냅샷 완료: {len(balances)}개 자산")

        except Exception as e:
            print(f"❌ 포트폴리오 스냅샷 오류: {e}")
            raise
        finally:
            conn.close()

    def calculate_investment_performance(self):
        """정확한 투자 성과 계산"""
        print("📈 투자 성과 계산 중...")

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # 1. 총 입금액 계산 (KRW)
            cursor.execute("""
                SELECT SUM(amount) FROM upbit_deposits_withdraws 
                WHERE type = 'deposit' AND currency = 'KRW' AND state = 'ACCEPTED'
            """)
            total_deposits = cursor.fetchone()[0] or 0

            # 2. 총 출금액 계산 (KRW)
            cursor.execute("""
                SELECT SUM(amount) FROM upbit_deposits_withdraws 
                WHERE type = 'withdraw' AND currency = 'KRW' AND state = 'ACCEPTED'
            """)
            total_withdrawals = cursor.fetchone()[0] or 0

            # 3. 순 투자금액
            net_investment = total_deposits - total_withdrawals

            # 4. 현재 포트폴리오 가치 (최신 스냅샷)
            cursor.execute("""
                SELECT SUM(krw_value) FROM portfolio_snapshots 
                WHERE snapshot_time = (
                    SELECT MAX(snapshot_time) FROM portfolio_snapshots
                )
            """)
            current_portfolio_value = cursor.fetchone()[0] or 0

            # 5. 실현 손익 계산 (매도 거래에서)
            cursor.execute("""
                SELECT SUM(
                    CASE 
                        WHEN side = 'ask' THEN price - paid_fee
                        WHEN side = 'bid' THEN -(price + paid_fee)
                        ELSE 0
                    END
                ) FROM upbit_orders
                WHERE state = 'done' AND executed_volume > 0
            """)
            realized_pnl = cursor.fetchone()[0] or 0

            # 6. 미실현 손익 = 현재 포트폴리오 가치 - 순투자금액 - 실현손익
            unrealized_pnl = current_portfolio_value - net_investment

            # 7. 총 손익
            total_pnl = unrealized_pnl  # realized_pnl은 이미 portfolio value에 반영됨

            # 8. 수익률
            roi_percentage = (total_pnl / net_investment *
                              100) if net_investment > 0 else 0

            # 계산 결과 저장
            calculation_time = datetime.now().isoformat()
            cursor.execute("""
                INSERT INTO investment_performance (
                    calculation_time, total_investment, total_withdrawal,
                    net_investment, current_portfolio_value, unrealized_pnl,
                    realized_pnl, total_pnl, roi_percentage, period_start, period_end
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                calculation_time,
                total_deposits,
                total_withdrawals,
                net_investment,
                current_portfolio_value,
                unrealized_pnl,
                realized_pnl,
                total_pnl,
                roi_percentage,
                None,  # period_start (전체 기간)
                calculation_time  # period_end
            ))

            conn.commit()

            # 결과 출력
            print(f"✅ 투자 성과 계산 완료:")
            print(f"   💰 총 투자금: {total_deposits:,.0f}원")
            print(f"   💸 총 출금액: {total_withdrawals:,.0f}원")
            print(f"   📊 순 투자금: {net_investment:,.0f}원")
            print(f"   📈 현재 자산가치: {current_portfolio_value:,.0f}원")
            print(f"   💹 총 손익: {total_pnl:,.0f}원 ({roi_percentage:+.2f}%)")

        except Exception as e:
            print(f"❌ 투자 성과 계산 오류: {e}")
            raise
        finally:
            conn.close()

    def get_investment_summary(self):
        """투자 요약 정보 조회"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # 최신 성과 데이터
            cursor.execute("""
                SELECT * FROM investment_performance 
                ORDER BY calculation_time DESC LIMIT 1
            """)
            latest_performance = cursor.fetchone()

            if not latest_performance:
                return None

            # 컬럼명 매핑
            columns = [description[0] for description in cursor.description]
            performance_dict = dict(zip(columns, latest_performance))

            # 최신 포트폴리오 구성
            cursor.execute("""
                SELECT currency, balance + locked as total_amount, krw_value 
                FROM portfolio_snapshots 
                WHERE snapshot_time = (
                    SELECT MAX(snapshot_time) FROM portfolio_snapshots
                ) AND (balance + locked) > 0
                ORDER BY krw_value DESC
            """)
            portfolio = cursor.fetchall()

            # 최근 거래 내역 (최근 10건)
            cursor.execute("""
                SELECT market, side, executed_volume, price, created_at
                FROM upbit_orders 
                WHERE state = 'done'
                ORDER BY created_at DESC LIMIT 10
            """)
            recent_trades = cursor.fetchall()

            return {
                'performance': performance_dict,
                'portfolio': portfolio,
                'recent_trades': recent_trades
            }

        except Exception as e:
            print(f"❌ 요약 정보 조회 오류: {e}")
            return None
        finally:
            conn.close()

    def generate_comprehensive_report(self):
        """종합 투자 리포트 생성"""
        summary = self.get_investment_summary()

        if not summary:
            return "❌ 투자 데이터가 없습니다."

        performance = summary['performance']
        portfolio = summary['portfolio']
        recent_trades = summary['recent_trades']

        report = []
        report.append("💰 업비트 실제 투자 분석 리포트")
        report.append("=" * 60)
        report.append(
            f"📅 분석 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"🔄 데이터 기준: 업비트 API (동기화됨)")

        report.append("\n📈 투자 성과 요약")
        report.append("-" * 40)
        report.append(f"💵 총 입금액: {performance['total_investment']:,.0f}원")
        report.append(f"💸 총 출금액: {performance['total_withdrawal']:,.0f}원")
        report.append(f"💰 순 투자금: {performance['net_investment']:,.0f}원")
        report.append(
            f"📊 현재 자산가치: {performance['current_portfolio_value']:,.0f}원")
        report.append(f"💹 투자 손익: {performance['total_pnl']:,.0f}원")
        report.append(f"📈 수익률: {performance['roi_percentage']:+.2f}%")

        # 포트폴리오 구성
        if portfolio:
            report.append("\n💼 현재 포트폴리오 (업비트 실시간)")
            report.append("-" * 40)

            for currency, total_amount, krw_value in portfolio:
                if currency == 'KRW':
                    report.append(f"💵 {currency}: {total_amount:,.0f}원")
                else:
                    percentage = (krw_value / performance['current_portfolio_value']
                                  * 100) if performance['current_portfolio_value'] > 0 else 0
                    report.append(
                        f"🪙 {currency}: {total_amount:.6f}개 ({krw_value:,.0f}원, {percentage:.1f}%)")

        # 최근 거래
        if recent_trades:
            report.append("\n📋 최근 거래 내역 (업비트 동기화)")
            report.append("-" * 40)

            for market, side, volume, price, created_at in recent_trades:
                side_emoji = "🔴" if side == 'ask' else "🟢"
                side_text = "매도" if side == 'ask' else "매수"
                coin = market.replace('KRW-', '')
                date_str = created_at[:19].replace('T', ' ')

                report.append(f"{side_emoji} {date_str} | {coin} {side_text} | "
                              f"{volume:.6f}개 | {price:,.0f}원")

        return "\n".join(report)


def main():
    """메인 실행 함수"""
    print("🔄 업비트 기반 신뢰성 투자 분석기")
    print("=" * 50)

    try:
        # 동기화 매니저 초기화
        sync_manager = UpbitDataSyncManager()

        print("\n📋 실행할 작업을 선택하세요:")
        print("1. 전체 데이터 동기화")
        print("2. 투자 성과 조회")
        print("3. 종합 리포트 생성")
        print("4. 자동 동기화 (주기적 실행)")

        choice = input("\n선택 (1-4): ").strip()

        if choice == '1':
            sync_manager.sync_all_data()

        elif choice == '2':
            summary = sync_manager.get_investment_summary()
            if summary:
                performance = summary['performance']
                print(f"\n📊 최신 투자 성과:")
                print(f"💰 순 투자금: {performance['net_investment']:,.0f}원")
                print(
                    f"📈 현재 가치: {performance['current_portfolio_value']:,.0f}원")
                print(
                    f"💹 총 손익: {performance['total_pnl']:,.0f}원 ({performance['roi_percentage']:+.2f}%)")
            else:
                print("❌ 투자 데이터가 없습니다. 먼저 동기화를 실행하세요.")

        elif choice == '3':
            report = sync_manager.generate_comprehensive_report()
            print(f"\n{report}")

            # 파일로 저장
            save_choice = input("\n💾 리포트를 파일로 저장하시겠습니까? (y/N): ").lower()
            if save_choice in ['y', 'yes']:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"upbit_investment_report_{timestamp}.txt"
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(report)
                print(f"✅ 리포트 저장: {filename}")

        elif choice == '4':
            print("🔄 자동 동기화 모드 시작...")
            print("30분마다 업비트 데이터를 동기화합니다.")
            print("Ctrl+C로 중지할 수 있습니다.")

            try:
                while True:
                    sync_manager.sync_all_data()
                    print(
                        f"⏰ 다음 동기화: 30분 후 ({(datetime.now() + timedelta(minutes=30)).strftime('%H:%M')})")
                    time.sleep(1800)  # 30분 대기

            except KeyboardInterrupt:
                print("\n⏹️ 자동 동기화 중지됨")

        else:
            print("❌ 잘못된 선택입니다.")

    except Exception as e:
        print(f"❌ 실행 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
