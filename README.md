# Auto Coin Trading Bot

## 📋 프로젝트 개요

업비트 API를 활용한 자동화된 암호화폐 트레이딩 봇

## 🏗️ 핵심 구조

### 메인 시스템

- `main.py` - 메인 트레이딩 엔진
- `config.yaml` - 설정 관리

### 모듈 (modules/)

- `config_manager.py` - 설정 관리자
- `trading_engine.py` - 거래 엔진
- `learning_system.py` - 학습 시스템
- `notification_manager.py` - 알림 관리자

### 스크립트 (scripts/)

- `real_upbit_analyzer.py` - 실제 업비트 데이터 동기화
- `auto_optimizer.py` - 자동 최적화 엔진
- `data_sync_integration.py` - 데이터 통합 관리

## 🚀 배포 및 실행

### 로컬 실행

```bash
python main.py
```

### 서버 배포

```bash
./deploy-auto.sh
```

### PM2 관리

```bash
pm2 list
pm2 logs auto-trader
pm2 logs auto-optimizer
```

## 📊 데이터 관리

- `upbit_sync.db` - 실제 업비트 거래 데이터 (메인)
- `trade_history.db` - 로컬 백업 데이터

## 주요 기능

1. 실시간 암호화폐 거래
2. 자동 최적화 시스템
3. 실제 업비트 데이터 동기화
4. 성능 모니터링 및 분석

## ⚙️ 환경 설정

1. Python 가상환경 설정
2. 의존성 설치: `pip install -r requirements.txt`
3. config.yaml 설정
4. 업비트 API 키 등록
