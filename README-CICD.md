# 🚀 Auto-Coin Enhanced CI/CD System

이 프로젝트는 강건한 CI/CD 파이프라인과 자동 모니터링 시스템을 포함합니다.

## 🎯 주요 기능

### 📋 CI/CD 파이프라인

- **자동 테스트**: 코드 품질 검사, 보안 스캔, 백테스트 검증
- **무중단 배포**: PM2 기반 롤링 배포
- **자동 롤백**: 배포 실패 시 이전 버전으로 자동 복구
- **헬스체크**: 배포 후 종합적인 상태 검증

### 🔧 모니터링 & 복구

- **실시간 헬스체크**: 애플리케이션 상태 지속 모니터링
- **자동 에러 복구**: 일반적인 에러 패턴 감지 및 자동 복구
- **다중 알림 시스템**: Discord, Slack, 이메일 등 다양한 채널
- **웹 대시보드**: 실시간 배포 상태 모니터링

## 📁 프로젝트 구조

```
auto-coin/
├── .github/workflows/
│   ├── ci-cd.yml              # 강화된 CI/CD 파이프라인
│   └── ci-cd-old.yml         # 기존 파이프라인 (백업)
├── scripts/
│   ├── health_check.py        # 종합 헬스체크
│   ├── auto_rollback.py       # 자동 롤백 시스템
│   ├── notification_manager.py # 다중 알림 시스템
│   └── error_recovery.py      # 에러 복구 자동화
├── dashboard/
│   └── index.html            # 실시간 모니터링 대시보드
├── modules/                   # 핵심 거래 모듈들
└── main.py                   # 메인 애플리케이션
```

## 🚀 CI/CD 워크플로우

### 1. 테스트 단계 (🧪 Tests & Quality Checks)

- **코드 스타일**: flake8을 이용한 코딩 스타일 검사
- **보안 스캔**: safety를 이용한 의존성 취약점 검사
- **단위 테스트**: pytest 기반 모듈 테스트
- **백테스트**: 실제 거래 로직 검증
- **성능 분석**: 트레이딩 성과 검증

### 2. 배포 단계 (🚀 Deploy to Production)

- **무중단 배포**: 기존 서비스 중단 없이 새 버전 배포
- **설정 보존**: 기존 설정 파일 및 거래 데이터 자동 백업/복원
- **의존성 설치**: requirements.txt 기반 자동 패키지 설치
- **PM2 관리**: 프로세스 매니저를 통한 안정적인 서비스 관리

### 3. 검증 단계 (🔍 Enhanced Health Check)

- **프로세스 상태**: PM2 프로세스 상태 확인
- **로그 분석**: 에러 패턴 자동 감지
- **시스템 리소스**: 메모리, CPU, 디스크 사용량 체크
- **거래 활동**: 실제 거래 기능 정상 작동 확인

### 4. 복구 단계 (🔄 Auto Rollback)

- **실패 감지**: 헬스체크 실패 시 자동 트리거
- **이전 버전 복원**: 백업된 이전 버전으로 자동 롤백
- **상태 검증**: 롤백 후 정상 작동 확인
- **알림 발송**: 복구 과정 및 결과 실시간 알림

## 📊 모니터링 시스템

### 실시간 대시보드

`dashboard/index.html`에서 제공되는 웹 기반 모니터링 도구:

- 📈 **실시간 상태**: 애플리케이션 온라인/오프라인 상태
- ⏱️ **업타임 추적**: 서비스 가동 시간 모니터링
- 💾 **리소스 사용량**: 메모리, CPU 사용률 실시간 표시
- 📊 **거래 현황**: 일일 거래 횟수 및 수익 현황
- 🗂️ **로그 모니터링**: 최근 시스템 로그 실시간 확인
- 🚀 **배포 이력**: 최근 배포 성공/실패 기록

### 자동 복구 시스템

`scripts/error_recovery.py`에서 제공되는 지능형 에러 복구:

- 🔍 **에러 패턴 감지**: 로그 분석을 통한 7가지 에러 유형 식별
- 🔧 **자동 해결**: 각 에러 유형별 맞춤 복구 솔루션 실행
- 🔄 **재시작 관리**: 쿨다운 시간 및 최대 재시작 횟수 제한
- 📢 **복구 알림**: Discord/Slack을 통한 복구 과정 실시간 알림

## 🔔 알림 시스템

### 다중 채널 지원

- **Discord**: 실시간 웹훅 알림
- **Slack**: 팀 협업 채널 연동
- **이메일**: 중요한 상황에 대한 이메일 알림
- **커스텀 웹훅**: 외부 시스템 연동 가능

### 알림 유형

- ✅ **배포 성공**: 새 버전 배포 완료 알림
- ❌ **배포 실패**: 배포 중 문제 발생 알림
- 🔄 **자동 롤백**: 롤백 진행 상황 알림
- 🔧 **에러 복구**: 자동 복구 시도 및 결과 알림
- 📊 **상태 리포트**: 정기적인 시스템 상태 보고

## ⚙️ 설정 가이드

### GitHub Secrets 설정

CI/CD 파이프라인 실행을 위해 다음 secrets 설정 필요:

```
DEPLOY_SSH_KEY        # 서버 접속용 SSH 개인키
SERVER_IP             # 배포 대상 서버 IP 주소
DISCORD_WEBHOOK_URL   # Discord 웹훅 URL (선택사항)
SLACK_WEBHOOK_URL     # Slack 웹훅 URL (선택사항)
EMAIL_USERNAME        # 이메일 계정 (선택사항)
EMAIL_PASSWORD        # 이메일 비밀번호 (선택사항)
```

### 환경 변수 설정

서버에서 실행 시 다음 환경변수 설정:

```bash
export PM2_APP_NAME="auto-trader"
export DISCORD_WEBHOOK_URL="your_discord_webhook"
export SLACK_WEBHOOK_URL="your_slack_webhook"
```

## 🔧 사용법

### 로컬 개발

```bash
# 개발 환경 설정
pip install -r requirements.txt

# 코드 품질 검사
flake8 modules/ main.py --max-line-length=100

# 테스트 실행
python -m pytest tests/ -v

# 백테스트 실행
python main.py --backtest --days 7 --ticker KRW-BTC
```

### 수동 배포 스크립트 실행

```bash
# 헬스체크 실행
python scripts/health_check.py

# 에러 복구 체크
python scripts/error_recovery.py --check

# 롤백 실행 (긴급시)
python scripts/auto_rollback.py

# 알림 테스트
python scripts/notification_manager.py success "테스트 메시지"
```

### 지속적인 모니터링 실행

```bash
# 백그라운드에서 에러 모니터링 실행
nohup python scripts/error_recovery.py > recovery.log 2>&1 &
```

## 📈 개선 사항

### 완료된 기능

- ✅ 강화된 CI/CD 파이프라인 구축
- ✅ 자동 롤백 시스템 구현
- ✅ 종합 헬스체크 시스템
- ✅ 다중 채널 알림 시스템
- ✅ 실시간 모니터링 대시보드
- ✅ 에러 복구 자동화
- ✅ 코드 품질 검사 통합

### 향후 개발 예정

- 🔄 Blue-Green 배포 전략
- 📊 Canary 배포 지원
- 🔍 APM (Application Performance Monitoring) 통합
- 📈 메트릭 수집 및 분석 대시보드
- 🔐 보안 스캔 강화

## 🆘 트러블슈팅

### 배포 실패 시

1. GitHub Actions 로그 확인
2. 서버 SSH 연결 상태 확인
3. 디스크 공간 및 권한 확인
4. PM2 프로세스 상태 확인

### 에러 복구 시스템이 작동하지 않을 때

1. 환경변수 설정 확인
2. PM2 애플리케이션 이름 확인
3. 스크립트 실행 권한 확인
4. 로그 파일(`error_recovery.log`) 확인

### 알림이 오지 않을 때

1. 웹훅 URL 유효성 확인
2. 네트워크 연결 상태 확인
3. Discord/Slack 채널 설정 확인

## 📄 라이선스

MIT License

---

**Auto-Coin Enhanced CI/CD System**은 안정적이고 강건한 암호화폐 자동매매 시스템 운영을 위한 완전 자동화된 DevOps 솔루션입니다.
