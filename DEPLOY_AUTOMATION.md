# 🚀 Auto-Coin 자동화 배포 시스템

## 🎯 개요

이 시스템은 Git push부터 GitHub Actions 모니터링, 에러 조치까지 완전 자동화된 배포 파이프라인을 제공합니다.

## 📋 주요 기능

### 🔄 **완전 자동화된 배포**

- Git add → commit → push 자동화
- GitHub Actions 워크플로 실시간 모니터링
- 배포 성공/실패 자동 감지
- Discord 알림 자동 전송

### 🛡️ **스마트 에러 처리**

- CI/CD 실패 시 자동 복구 시도
- 복구 실패 시 자동 롤백
- 실시간 서버 헬스체크
- 상세한 오류 로그 분석

### 📊 **실시간 모니터링**

- GitHub CLI 기반 워크플로 상태 추적
- 작업별 진행 상황 표시
- 서버 리소스 모니터링
- 애플리케이션 상태 확인

## 🚀 사용법

### 1. **간편 배포 (권장)**

```bash
# 커밋 메시지와 함께 배포
./deploy "새로운 기능 추가"

# 또는 변경사항만 배포 (커밋 메시지는 대화형으로 입력)
./deploy
```

### 2. **전체 자동화 배포**

```bash
# 완전 자동화 배포 실행
./deploy-auto.sh
```

### 3. **GitHub Actions 모니터링만**

```bash
# 특정 워크플로 실행 모니터링
python3 scripts/github_monitor.py --run-id 123456789

# 최신 워크플로 모니터링
python3 scripts/github_monitor.py
```

## 📁 시스템 구성

```
auto-coin/
├── deploy                          # 🚀 간편 배포 명령어
├── deploy-auto.sh                  # 🤖 완전 자동화 배포 스크립트
├── scripts/
│   ├── github_monitor.py           # 📊 GitHub Actions 모니터링
│   ├── health_check.py            # 🏥 서버 헬스체크
│   ├── auto_rollback.py           # 🔄 자동 롤백
│   └── error_recovery.py          # 🛠️ 에러 복구
└── .github/workflows/
    └── ci-cd.yml                   # 🏗️ 강화된 CI/CD 파이프라인
```

## 🔧 설정

### 1. **GitHub CLI 설치 및 인증**

```bash
# macOS
brew install gh

# Ubuntu/Debian
curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | sudo dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | sudo tee /etc/apt/sources.list.d/github-cli.list > /dev/null
sudo apt update && sudo apt install gh

# 인증
gh auth login
```

### 2. **GitHub Secrets 설정**

GitHub 레포지토리 → Settings → Secrets and variables → Actions에서 설정:

```bash
DEPLOY_SSH_KEY       # SSH 개인키 (서버 접근용)
SERVER_IP            # 서버 IP 주소
DISCORD_WEBHOOK_URL  # Discord 웹훅 URL (선택사항)
```

### 3. **스크립트 권한 설정**

```bash
chmod +x deploy deploy-auto.sh scripts/*.py
```

## 🎬 배포 플로우

### 📋 **1단계: 로컬 준비**

```
🔍 필수 도구 확인 (GitHub CLI, SSH)
📝 Git 변경사항 처리 (add, commit)
🚀 GitHub에 푸시
```

### 📋 **2단계: CI/CD 파이프라인**

```
🧪 코드 품질 검사 (flake8, tests)
🚀 서버 배포 (SSH, PM2)
🏥 헬스체크 (애플리케이션 상태)
📊 5분간 모니터링
```

### 📋 **3단계: 에러 처리**

```
❌ 실패 시 → 🛠️ 자동 복구 시도
❌ 복구 실패 → 🔄 자동 롤백
✅ 성공 시 → 📢 Discord 알림
```

## 🔧 고급 설정

### **커스텀 타임아웃 설정**

```bash
# 30분 타임아웃으로 모니터링
python3 scripts/github_monitor.py --timeout 1800
```

### **특정 브랜치 배포**

```bash
# develop 브랜치 배포
git checkout develop
./deploy "개발 브랜치 배포"
```

### **수동 롤백**

```bash
# 문제 발생 시 수동 롤백
ssh ubuntu@서버IP
cd /home/ubuntu && ./rollback.sh
```

## 📊 모니터링 대시보드

배포 후 다음 URL에서 실시간 모니터링 가능:

- **애플리케이션 대시보드**: `http://서버IP:3000`
- **PM2 모니터링**: `ssh ubuntu@서버IP 'pm2 monit'`
- **로그 확인**: `ssh ubuntu@서버IP 'pm2 logs auto-trader'`

## 🚨 트러블슈팅

### **SSH 연결 실패**

```bash
# SSH 키 등록 확인
ssh-copy-id -i ~/.ssh/id_ed25519.pub ubuntu@서버IP
```

### **GitHub CLI 인증 실패**

```bash
# 재인증
gh auth logout
gh auth login
```

### **워크플로 찾기 실패**

```bash
# 수동으로 워크플로 ID 확인
gh run list --repo eogh234/auto-coin --limit 5
```

### **Discord 알림 실패**

```bash
# config.yaml에서 webhook_url 확인
grep -A 5 "discord:" config.yaml
```

## 🎉 성공 사례

```
🚀 자동 배포 시스템 실행...

✅ [1/6] 필수 도구 확인 완료
✅ [2/6] Git 변경사항 처리 완료
✅ [3/6] CI/CD 파이프라인 성공
✅ [4/6] 배포 검증 완료
✅ [5/6] 서비스 상태 확인 완료
✅ [6/6] 모니터링 설정 완료

🎉 배포가 성공적으로 완료되었습니다!
🔗 모니터링 대시보드: http://152.70.39.62:3000
📊 서버 로그: ssh ubuntu@152.70.39.62 'pm2 logs auto-trader'
```

이제 단 한 번의 명령어로 안전하고 확실한 배포가 가능합니다! 🚀
