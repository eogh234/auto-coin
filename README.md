# 🚀 Auto-Coin Trading Bot - 모듈화 버전

Upbit API를 활용한 암호화폐 자동매매 시스템입니다. 모듈화된 구조로 설계되어 유지보수와 확장성을 고려했습니다.

## ✨ 주요 기능

### 🎯 핵심 기능

- **실시간 자동매매**: RSI, 볼린저밴드 기반 전략
- **AI 학습 시스템**: 거래 결과를 학습하여 매개변수 자동 최적화
- **Discord 알림**: 거래 결과 및 상태를 실시간 알림
- **백테스팅**: 과거 데이터로 전략 검증
- **성과 분석**: 상세한 거래 통계 및 수익률 분석

### 🏗️ 모듈화 구조

```
auto-coin/
├── main.py                 # 메인 실행 파일
├── modules/                # 모듈 디렉토리
│   ├── __init__.py
│   ├── config_manager.py   # 설정 관리
│   ├── notification_manager.py  # 알림 시스템
│   ├── learning_system.py  # AI 학습 시스템
│   ├── trading_engine.py   # 거래 엔진
│   ├── backtest_engine.py  # 백테스트 엔진
│   └── performance_analyzer.py  # 성과 분석기
├── config.yaml            # 설정 파일
├── requirements.txt       # 의존성
├── run.sh                # 통합 실행 스크립트
└── README.md             # 문서
```

### 🧠 AI 학습 시스템

- **적응형 매개변수**: 거래 성과에 따른 자동 파라미터 조정
- **SQLite 데이터베이스**: 경량화된 거래 이력 저장
- **백그라운드 학습**: 메모리 효율적인 비동기 학습
- **성과 기반 최적화**: RSI, 볼린저밴드 임계값 자동 조정

### 🛡️ 안전장치

- **일일 거래 한도**: 과도한 거래 방지
- **최소 잔고 관리**: 잔고 부족 시 거래 중단
- **메모리 모니터링**: 시스템 자원 상태 실시간 확인
- **오류 복구**: 네트워크/API 오류 시 자동 재시도

## 🔧 설치 및 설정

### 1. 환경 준비

```bash
# 의존성 설치
pip install -r requirements.txt
```

### 2. 설정 파일 구성 (`config.yaml`)

```yaml
upbit:
  access_key: "YOUR_ACCESS_KEY"
  secret_key: "YOUR_SECRET_KEY"

discord:
  webhook_url: "YOUR_WEBHOOK_URL"
  notification_cooldown: 300
  status_report_interval: 1800

trading:
  max_daily_trades: 50
  investment_ratio: 0.1
  min_krw_balance: 50000

learning:
  learning_interval_hours: 1
  memory_threshold: 0.85
  min_trades_for_learning: 10
```

## 🚀 실행 방법

### 통합 실행 스크립트 (권장)

```bash
# 실거래 모드
./run.sh live

# 테스트 모드
./run.sh test

# 백테스팅 (30일)
./run.sh backtest

# 성과 분석 (7일)
./run.sh analyze

# 서버 배포
./run.sh deploy
```

### 직접 실행

```bash
# 실거래 모드
python main.py

# 테스트 모드
python main.py --test

# 백테스팅
python main.py --backtest --ticker KRW-BTC --days 30

# 성과 분석
python main.py --analyze --days 7
```

## 📊 모듈별 기능

### ConfigManager

- YAML 기반 설정 관리
- 기본 설정 자동 생성
- 점 표기법으로 설정값 접근

### NotificationManager

- Discord 웹훅 알림
- 쿨다운 기능
- 정기 상태 보고

### LearningSystem

- SQLite 기반 거래 이력 관리
- 적응형 매개변수 최적화
- 백그라운드 학습

### TradingEngine

- 실시간 거래 실행
- 다중 코인 지원
- 신호 생성 및 포지션 관리

### BacktestEngine

- 과거 데이터 기반 전략 검증
- RSI 기반 백테스팅
- 상세 성과 분석

### PerformanceAnalyzer

- 거래 성과 통계
- 매개변수 현황
- 시스템 상태 모니터링

## 🔧 개발자 가이드

### 새로운 모듈 추가

1. `modules/` 디렉토리에 새 파일 생성
2. `modules/__init__.py`에 import 추가
3. `main.py`에서 새 모듈 활용

### 사용자 정의 전략 추가

```python
# modules/trading_engine.py의 generate_signal 메서드 수정
def generate_signal(self, ticker: str) -> str:
    # 기존 로직
    # ...

    # 새로운 전략 추가
    if your_custom_condition:
        return "CUSTOM_BUY"
```

# 특정 코인 백테스팅

python backtest_advanced.py --ticker KRW-ETH --plot

```

## 🚨 주의사항

### 보안

- API 키 보안 주의
- config.yaml 파일 외부 노출 금지
- 서버 접근 권한 관리

### 투자 위험

- 모든 투자 손실 책임은 사용자에게 있음
- 실거래 전 충분한 테스트 필요
- 감당 가능한 자금으로만 거래

### 시스템 요구사항

- 안정적인 인터넷 연결
- 24시간 운영 가능한 서버 환경
- Python 3.8 이상

## ⚠️ 면책 조항

이 소프트웨어는 교육 목적으로 제공되며, 실제 투자 시 발생하는 모든 손실에 대해 개발자는 책임지지 않습니다. 투자는 본인의 판단과 책임하에 진행하시기 바랍니다.
```
