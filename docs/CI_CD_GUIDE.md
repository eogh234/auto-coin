# 🚀 Auto-Coin CI/CD Pipeline Guide

## 📋 Overview

우리의 CI/CD 파이프라인은 **테스트 실패 시 자동 롤백**과 **포괄적인 검증**을 제공합니다.

## 🔄 Pipeline Stages

### 1. 🧪 Test & Validate

- **Configuration 검증**: YAML 형식 및 필수 필드 확인
- **Security 스캔**: Bandit으로 보안 취약점 검사
- **Unit Tests**: 전체 테스트 스위트 실행
- **Import 검증**: 핵심 모듈 임포트 확인
- **Code Coverage**: 코드 커버리지 측정

### 2. 🚀 Deploy (테스트 통과 시에만)

- **Backup 생성**: 현재 버전 자동 백업
- **서비스 중단**: PM2 프로세스 graceful stop
- **코드 업데이트**: Git pull 및 의존성 설치
- **검증**: 배포된 코드 유효성 확인
- **서비스 재시작**: PM2 프로세스 restart

### 3. 🔄 Emergency Rollback (배포 실패 시)

- **자동 트리거**: 배포 실패 시 즉시 실행
- **백업 복원**: 최신 백업으로 자동 복구
- **서비스 복구**: PM2 프로세스 재시작

## ❌ 테스트 실패 시 대응책

### 🔍 실패 유형별 대응

#### 1. **Configuration 에러**

```yaml
❌ Config validation failed: Missing upbit section
```

**해결책:**

- `config.yaml`에서 필수 섹션 확인
- YAML 문법 검증
- 필수 필드 추가

#### 2. **Unit Test 실패**

```bash
❌ AssertionError: Failed to import TradingEngine
```

**해결책:**

- 로컬에서 테스트 실행: `python -m pytest tests/ -v`
- 실패한 테스트 로그 확인
- 코드 수정 후 재푸시

#### 3. **Import 에러**

```python
❌ ImportError: cannot import name 'AutoOptimizer'
```

**해결책:**

- 모듈 구조 확인
- `__init__.py` 파일 검증
- 의존성 업데이트

### 📊 Artifact 활용

실패 시 다음 아티팩트가 생성됩니다:

- `test-failures.txt`: 상세 테스트 실패 로그
- `bandit-report.json`: 보안 스캔 결과

### 🛠️ 로컬 디버깅

```bash
# 전체 테스트 실행
python -m pytest tests/ -v --tb=long

# 특정 테스트 실행
python -m pytest tests/test_config.py -v

# 커버리지 포함 테스트
python -m pytest tests/ --cov=modules --cov=scripts --cov-report=html

# 보안 스캔
bandit -r . -f json -o bandit-report.json
```

## 🚨 Emergency Procedures

### 🔄 수동 롤백

```bash
ssh ubuntu@서버IP
cd /home/ubuntu/auto-coin
pm2 stop auto-trader auto-optimizer

# 백업 목록 확인
ls -la /home/ubuntu/backups/

# 특정 백업으로 복원
cp -r /home/ubuntu/backups/auto-coin-YYYYMMDD-HHMMSS/* .
pm2 restart auto-trader auto-optimizer
```

### 🔧 서비스 상태 확인

```bash
# PM2 상태 확인
pm2 status

# 로그 확인
pm2 logs auto-trader --lines 50
pm2 logs auto-optimizer --lines 50

# 프로세스 재시작
pm2 restart all
```

## 📈 Best Practices

### ✅ 성공적인 배포를 위한 체크리스트

- [ ] 로컬에서 모든 테스트 통과
- [ ] Config 파일 유효성 검증
- [ ] 새로운 의존성이 있다면 `requirements.txt` 업데이트
- [ ] 중요 변경사항은 PR로 코드 리뷰

### 🔄 정기 점검 사항

- [ ] 주간 백업 정리 (오래된 백업 삭제)
- [ ] PM2 프로세스 상태 모니터링
- [ ] 보안 스캔 결과 검토
- [ ] 코드 커버리지 개선

## 📞 문제 해결

### 자주 발생하는 문제들

1. **SSH 연결 실패**

   - GitHub Secrets의 SSH_PRIVATE_KEY, HOST, USERNAME 확인

2. **PM2 프로세스 시작 실패**

   - ecosystem.config.js 파일 확인
   - 포트 충돌 확인

3. **의존성 설치 실패**

   - requirements.txt 업데이트
   - Python 버전 호환성 확인

4. **Git 업데이트 실패**
   - 서버의 Git 상태 확인
   - 수동으로 git reset --hard origin/master

---

💡 **Tip**: 문제가 지속될 경우 GitHub Actions 로그와 서버 로그를 함께 확인하세요!
