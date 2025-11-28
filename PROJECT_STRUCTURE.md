# 프로젝트 구조 요약

## 현재 활성 파일들

### 핵심 시스템

- **main.py** - 메인 트레이딩 봇 엔진
- **config.yaml** - 전체 설정 관리

### 모듈 (modules/)

- **config_manager.py** - 설정 관리자
- **trading_engine.py** - 거래 엔진
- **learning_system.py** - 머신러닝 시스템
- **notification_manager.py** - 알림 관리자

### 스크립트 (scripts/)

- **real_upbit_analyzer.py** - 실제 업비트 데이터 동기화 (실제 API 데이터)
- **auto_optimizer.py** - 자동 최적화 엔진 (실제 데이터 기반 최적화)
- **data_sync_integration.py** - 데이터 통합 관리

### 데이터

- **upbit_sync.db** - 메인 데이터소스 (실제 업비트 거래 데이터)
- **trade_history.db** - 백업 데이터소스 (로컬 거래 로그)
- **data_config.json** - 데이터 소스 설정

### 배포/관리

- **deploy-auto.sh** - 자동 배포 스크립트
- **requirements.txt** - 의존성 패키지 목록

## 정리된 파일들 (archive/)

### 미사용 스크립트 (archive/unused_scripts/)

- performance_monitor.py
- realtime_dashboard.py
- cicd_notification_manager.py
- config_optimizer.py
- optimization_action_plan.py

### 분석 도구 (archive/analysis_tools/)

- optimization_report.py
- current_status_report.py
- investment_analysis.py
- test_data_integration.py
- analyze_structure.py

### 개발 도구 (archive/development_tools/)

- github_monitor.py
- health_check.py
- error_recovery.py
- auto_rollback.py

### 미사용 모듈 (archive/unused_modules/)

- backtest_engine.py
- performance_analyzer.py

## 데이터 흐름

```
실제 업비트 API
    ↓
real_upbit_analyzer.py (30분마다 동기화)
    ↓
upbit_sync.db (메인 데이터)
    ↓
auto_optimizer.py (실제 데이터 기반 최적화)
    ↓
main.py (최적화된 매개변수로 트레이딩)
```

## 서버 실행 상태

- **PM2 auto-trader**: main.py 실행 중
- **PM2 auto-optimizer**: auto_optimizer.py 실행 중
- 실제 업비트 API와 동기화된 정확한 데이터 기반 운영

## 정리 효과

1. **파일 수 감소**: 27개 → 11개 핵심 파일
2. **명확한 역할 분담**: 각 파일의 목적이 명확해짐
3. **데이터 일관성**: 실제 업비트 데이터를 단일 소스로 활용
4. **유지보수성 향상**: 핵심 기능에 집중된 구조
5. **의존성 단순화**: 복잡한 교차 의존성 제거
