"""
학습 시스템 모듈
"""

import datetime
import time
import logging
import sqlite3
import threading
import json
import psutil
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Union
from .config_manager import ConfigManager


@dataclass
class TradeRecord:
    """거래 기록 데이터 클래스"""
    timestamp: datetime.datetime
    coin: str
    action: str  # BUY, SELL
    signal_type: str
    price: float
    amount: float
    market_state: str
    rsi: float
    bollinger_position: float
    success: Optional[bool] = None
    profit_rate: Optional[float] = None
    hold_duration: Optional[int] = None


class LearningSystem:
    """경량화된 학습 시스템"""

    def __init__(self, config_manager: ConfigManager):
        self.config = config_manager
        self.db_path = "trade_history.db"
        self.learning_lock = threading.Lock()
        self.last_learning_time = 0

        # 적응형 매개변수
        self.adaptive_params = {
            'rsi_buy_threshold': 30,
            'rsi_sell_threshold': 70,
            'bollinger_buy_ratio': 0.2,
            'bollinger_sell_ratio': 0.8,
            'min_profit_target': 0.02,
            'stop_loss_threshold': -0.05,
        }

        self._init_database()
        self._load_adaptive_params()

    def _init_database(self):
        """데이터베이스 초기화"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # 거래 기록 테이블
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    coin TEXT NOT NULL,
                    action TEXT NOT NULL,
                    signal_type TEXT NOT NULL,
                    price REAL NOT NULL,
                    amount REAL NOT NULL,
                    market_state TEXT,
                    rsi REAL,
                    bollinger_position REAL,
                    success INTEGER,
                    profit_rate REAL,
                    hold_duration INTEGER
                )
            ''')

            # 적응형 매개변수 테이블
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS adaptive_params (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    params TEXT NOT NULL
                )
            ''')

            # 인덱스 생성
            cursor.execute(
                'CREATE INDEX IF NOT EXISTS idx_timestamp ON trades(timestamp)')
            cursor.execute(
                'CREATE INDEX IF NOT EXISTS idx_coin ON trades(coin)')

            conn.commit()
            conn.close()
            logging.info("거래 학습 DB 초기화 완료")

        except Exception as e:
            logging.error(f"DB 초기화 실패: {e}")

    def record_trade(self, trade_record: TradeRecord):
        """거래 기록 저장"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                INSERT INTO trades (
                    timestamp, coin, action, signal_type, price, amount,
                    market_state, rsi, bollinger_position, success, 
                    profit_rate, hold_duration
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                trade_record.timestamp.isoformat(),
                trade_record.coin,
                trade_record.action,
                trade_record.signal_type,
                trade_record.price,
                trade_record.amount,
                trade_record.market_state,
                trade_record.rsi,
                trade_record.bollinger_position,
                trade_record.success,
                trade_record.profit_rate,
                trade_record.hold_duration
            ))

            conn.commit()
            conn.close()

        except Exception as e:
            logging.error(f"거래 기록 저장 실패: {e}")

    def update_trade_result(self, coin: str, buy_timestamp: datetime.datetime,
                            success: bool, profit_rate: float, hold_duration: int):
        """매매 결과 업데이트"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                UPDATE trades 
                SET success = ?, profit_rate = ?, hold_duration = ?
                WHERE coin = ? AND action = 'BUY' 
                AND timestamp = ? AND success IS NULL
            ''', (
                1 if success else 0,
                profit_rate,
                hold_duration,
                coin,
                buy_timestamp.isoformat()
            ))

            conn.commit()
            conn.close()

            # 학습 스케줄링
            self._schedule_learning()

        except Exception as e:
            logging.error(f"거래 결과 업데이트 실패: {e}")

    def _schedule_learning(self):
        """자원 고려 학습 스케줄링"""
        current_time = time.time()
        learning_interval = self.config.get(
            'learning.learning_interval_hours', 1) * 3600

        if current_time - self.last_learning_time < learning_interval:
            return

        # 메모리 체크
        memory_threshold = self.config.get('learning.memory_threshold', 0.85)
        memory_usage = psutil.virtual_memory().percent / 100

        if memory_usage > memory_threshold:
            logging.warning(f"메모리 사용량 높음 ({memory_usage:.1%}), 학습 연기")
            return

        # 백그라운드 학습
        threading.Thread(target=self._perform_learning, daemon=True).start()

    def _perform_learning(self):
        """실제 학습 수행"""
        with self.learning_lock:
            try:
                logging.info("적응형 학습 시작...")

                # 성과 분석
                performance = self._analyze_recent_performance()

                # 매개변수 최적화
                new_params = self._optimize_parameters(performance)

                if new_params:
                    self.adaptive_params.update(new_params)
                    self._save_adaptive_params()
                    logging.info(f"매개변수 업데이트: {new_params}")

                self.last_learning_time = time.time()
                logging.info("적응형 학습 완료")

            except Exception as e:
                logging.error(f"학습 수행 오류: {e}")

    def _analyze_recent_performance(self, days: int = 7) -> Dict:
        """최근 성과 분석"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            since_date = datetime.datetime.now() - datetime.timedelta(days=days)

            cursor.execute('''
                SELECT signal_type, success, profit_rate, rsi, bollinger_position,
                       market_state
                FROM trades 
                WHERE timestamp > ? AND success IS NOT NULL
            ''', (since_date.isoformat(),))

            trades = cursor.fetchall()
            conn.close()

            if not trades:
                return {}

            analysis = {
                'total_trades': len(trades),
                'success_rate': sum(1 for t in trades if t[1] == 1) / len(trades),
                'avg_profit': sum(t[2] for t in trades if t[2]) / len(trades),
                'rsi_analysis': [],
                'bollinger_analysis': []
            }

            for trade in trades:
                _, success, profit, rsi, bollinger, market = trade

                if rsi and success is not None:
                    analysis['rsi_analysis'].append({
                        'rsi': rsi, 'success': success, 'profit': profit or 0
                    })

                if bollinger and success is not None:
                    analysis['bollinger_analysis'].append({
                        'bollinger': bollinger, 'success': success, 'profit': profit or 0
                    })

            return analysis

        except Exception as e:
            logging.error(f"성과 분석 실패: {e}")
            return {}

    def _optimize_parameters(self, performance: Dict) -> Dict:
        """매개변수 최적화"""
        min_trades = self.config.get('learning.min_trades_for_learning', 10)

        if not performance or performance.get('total_trades', 0) < min_trades:
            return {}

        optimized = {}

        try:
            # RSI 임계값 최적화
            if performance.get('rsi_analysis'):
                rsi_data = performance['rsi_analysis']
                successful_buys = [d['rsi'] for d in rsi_data
                                   if d['success'] == 1 and d['profit'] > 0]

                if len(successful_buys) >= 5:
                    avg_successful_rsi = sum(
                        successful_buys) / len(successful_buys)
                    current_threshold = self.adaptive_params['rsi_buy_threshold']
                    new_threshold = (current_threshold * 0.8 +
                                     avg_successful_rsi * 0.2)
                    new_threshold = max(20, min(40, new_threshold))
                    optimized['rsi_buy_threshold'] = round(new_threshold, 1)

            # 볼린저밴드 비율 최적화
            if performance.get('bollinger_analysis'):
                bollinger_data = performance['bollinger_analysis']
                successful_positions = [d['bollinger'] for d in bollinger_data
                                        if d['success'] == 1 and d['profit'] > 0]

                if len(successful_positions) >= 5:
                    avg_successful_position = sum(
                        successful_positions) / len(successful_positions)
                    current_ratio = self.adaptive_params['bollinger_buy_ratio']
                    new_ratio = (current_ratio * 0.8 +
                                 avg_successful_position * 0.2)
                    new_ratio = max(0.1, min(0.3, new_ratio))
                    optimized['bollinger_buy_ratio'] = round(new_ratio, 2)

            return optimized

        except Exception as e:
            logging.error(f"매개변수 최적화 실패: {e}")
            return {}

    def _save_adaptive_params(self):
        """적응형 매개변수 저장"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                INSERT INTO adaptive_params (timestamp, params)
                VALUES (?, ?)
            ''', (
                datetime.datetime.now().isoformat(),
                json.dumps(self.adaptive_params, ensure_ascii=False)
            ))

            conn.commit()
            conn.close()

        except Exception as e:
            logging.error(f"매개변수 저장 실패: {e}")

    def _load_adaptive_params(self):
        """최신 적응형 매개변수 로드"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                SELECT params FROM adaptive_params 
                ORDER BY timestamp DESC LIMIT 1
            ''')

            result = cursor.fetchone()
            conn.close()

            if result:
                loaded_params = json.loads(result[0])
                self.adaptive_params.update(loaded_params)
                logging.info("적응형 매개변수 로드 완료")

        except Exception as e:
            logging.error(f"매개변수 로드 실패: {e}")

    def get_adaptive_params(self) -> Dict:
        """현재 적응형 매개변수 반환"""
        return self.adaptive_params.copy()

    def get_performance_report(self, days: int = 7) -> Dict:
        """성과 보고서 생성"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            since_date = datetime.datetime.now() - datetime.timedelta(days=days)

            cursor.execute('''
                SELECT COUNT(*) as total,
                       SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful,
                       AVG(COALESCE(profit_rate, 0)) as avg_profit,
                       MAX(profit_rate) as best_trade,
                       MIN(profit_rate) as worst_trade
                FROM trades 
                WHERE timestamp > ? AND success IS NOT NULL
            ''', (since_date.isoformat(),))

            stats = cursor.fetchone()
            conn.close()

            return {
                'period_days': days,
                'total_trades': stats[0] if stats else 0,
                'success_rate': (stats[1] / stats[0]) if stats and stats[0] > 0 else 0,
                'avg_profit_rate': stats[2] if stats else 0,
                'best_trade': stats[3] if stats else 0,
                'worst_trade': stats[4] if stats else 0,
                'current_params': self.adaptive_params,
                'memory_usage': psutil.virtual_memory().percent
            }

        except Exception as e:
            logging.error(f"성과 보고서 생성 실패: {e}")
            return {}
