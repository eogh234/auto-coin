# 🚀 Auto-Coin CI/CD 배포 가이드

이 문서는 GitHub Actions를 통한 자동 배포 파이프라인 설정 방법을 안내합니다.

## 🔑 필수 GitHub Secrets 설정

GitHub 리포지토리 설정에서 다음 Secrets를 추가해야 합니다:

### 1. SSH 키 생성 및 설정

```bash
# 로컬에서 SSH 키 생성
ssh-keygen -t rsa -b 4096 -C "github-actions@auto-coin"

# 공개키를 서버에 등록
cat ~/.ssh/id_rsa.pub | ssh ubuntu@152.70.39.62 'cat >> ~/.ssh/authorized_keys'
```

### 2. GitHub Secrets 등록

GitHub Repository → Settings → Secrets and variables → Actions에서 추가:

- **DEPLOY_SSH_KEY**: 생성한 SSH 개인키 내용 (id_rsa 파일 전체)
- **SERVER_IP**: `152.70.39.62`
- **SLACK_WEBHOOK_URL**: (선택사항) Slack 알림을 위한 웹훅 URL

## 📁 CI/CD 파이프라인 구조

```
.github/workflows/ci-cd.yml
├── 🧪 Test Stage
│   ├── 코드 스타일 검사 (flake8)
│   ├── 보안 취약점 검사 (safety)
│   ├── 백테스트 검증
│   └── 성능 분석 테스트
├── 🚀 Deploy Stage
│   ├── SSH로 서버 접속
│   ├── PM2 프로세스 중지
│   ├── 백업 생성
│   ├── 최신 코드 배포
│   ├── 설정/데이터 파일 복원
│   └── PM2로 재시작
├── 🔍 Health Check
│   ├── 서비스 상태 확인
│   └── 로그 검증
└── 🏷️ Auto Tagging
    ├── 자동 버전 태그 생성
    └── GitHub 릴리즈 생성
```

## 🔄 배포 프로세스

### 자동 배포 트리거:

1. `master` 브랜치에 push
2. Pull Request 생성 (테스트만 실행)
3. 릴리즈 생성

### 배포 단계:

1. **테스트 실행**: 코드 품질 및 기능 검증
2. **서버 배포**: 무중단 배포 (백업 → 배포 → 복원)
3. **상태 검증**: 헬스체크 및 로그 확인
4. **알림 발송**: Slack으로 배포 결과 통지

## 📋 배포 전 체크리스트

- [ ] GitHub Secrets 설정 완료
- [ ] 서버 SSH 키 등록 완료
- [ ] PM2 설정 확인
- [ ] config.yaml 파일 존재 확인
- [ ] 테스트 코드 작성 (선택사항)

## 🛠️ 수동 배포 방법 (백업용)

```bash
# 로컬에서 코드를 서버로 직접 배포
./scripts/deploy.sh

# 또는 서버에서 직접 업데이트
ssh ubuntu@152.70.39.62
cd /home/ubuntu/auto-trader-v2
git pull origin master
pm2 restart auto-trader
```

## 🚨 롤백 방법

배포 실패 시 이전 버전으로 롤백:

```bash
ssh ubuntu@152.70.39.62 << 'EOF'
  pm2 stop auto-trader
  rm -rf auto-trader-v2
  mv auto-trader-v2-backup auto-trader-v2
  cd auto-trader-v2
  pm2 start main.py --name auto-trader --interpreter python3
EOF
```

## 📊 모니터링

### GitHub Actions에서 확인 가능한 정보:

- ✅ 테스트 결과
- 📦 배포 상태
- 🏥 헬스체크 결과
- 📈 성능 메트릭

### 서버에서 직접 모니터링:

```bash
# PM2 상태 확인
pm2 status
pm2 logs auto-trader

# 시스템 리소스 확인
htop
df -h
```

## 🔧 트러블슈팅

### 일반적인 문제와 해결방법:

1. **SSH 연결 실패**

   ```bash
   # SSH 키 권한 확인
   chmod 600 ~/.ssh/id_rsa
   ```

2. **PM2 프로세스 시작 실패**

   ```bash
   # 의존성 재설치
   pip3 install -r requirements.txt --user
   ```

3. **설정 파일 누락**
   ```bash
   # 기본 설정 파일 생성
   python3 main.py --init-config
   ```

## 📞 지원

문제가 발생하면 다음을 확인해주세요:

1. GitHub Actions 로그
2. 서버 PM2 로그: `pm2 logs auto-trader`
3. 시스템 리소스: `htop`, `df -h`

---

_이 CI/CD 파이프라인은 안전하고 신뢰할 수 있는 자동 배포를 위해 설계되었습니다. 문제가 있으면 즉시 이전 버전으로 롤백됩니다._
