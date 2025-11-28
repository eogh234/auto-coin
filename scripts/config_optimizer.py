#!/usr/bin/env python3
"""
🔧 Config Quick Fix Script

현재 설정 문제 즉시 해결:
1. 매도 목표 수익률 2% → 1.5%로 조정
2. 최대 보유 시간 72시간 추가
3. 잔고 임계값 최적화
"""

import yaml
import shutil
from datetime import datetime
import subprocess


def backup_config():
    """설정 파일 백업"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    shutil.copy('config.yaml', f'config_backup_{timestamp}.yaml')
    print(f"✅ 설정 백업: config_backup_{timestamp}.yaml")


def apply_immediate_fixes():
    """즉시 개선사항 적용"""
    print("🔧 설정 최적화 시작...")

    # 백업 먼저
    backup_config()

    # 현재 설정 로드
    with open('config.yaml', 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)

    # 개선사항 적용
    improvements = []

    # 1. 매도 목표 수익률 조정 (2% → 1.5%)
    if config.get('trading', {}).get('profit_target_ratio', 0) == 0.02:
        config['trading']['profit_target_ratio'] = 0.015
        improvements.append("매도 목표 수익률: 2% → 1.5%")

    # 2. 최대 보유 시간 추가
    if 'max_hold_hours' not in config.get('trading', {}):
        config['trading']['max_hold_hours'] = 72
        improvements.append("최대 보유 시간: 72시간 추가")

    # 3. 잔고 임계값 최적화
    current_balance_threshold = config.get(
        'trading', {}).get('balance_threshold', 100000)
    if current_balance_threshold > 60000:
        config['trading']['balance_threshold'] = 50000
        improvements.append(f"잔고 임계값: {current_balance_threshold:,} → 50,000원")

    # 4. 매도 임계값 조정
    current_sell_threshold = config.get(
        'trading', {}).get('sell_threshold', 60)
    if current_sell_threshold > 50:
        config['trading']['sell_threshold'] = 45
        improvements.append(f"매도 임계값: {current_sell_threshold} → 45")

    # 5. 동적 학습 활성화
    if not config.get('learning', {}).get('dynamic_optimization', False):
        if 'learning' not in config:
            config['learning'] = {}
        config['learning']['dynamic_optimization'] = True
        config['learning']['optimization_interval'] = 300  # 5분
        improvements.append("동적 최적화 활성화")

    # 설정 저장
    with open('config.yaml', 'w', encoding='utf-8') as f:
        yaml.dump(config, f, default_flow_style=False,
                  allow_unicode=True, indent=2)

    print("\n✅ 설정 최적화 완료!")
    for i, improvement in enumerate(improvements, 1):
        print(f"   {i}. {improvement}")

    return len(improvements)


def restart_trading_bot():
    """트레이딩 봇 재시작 (PM2)"""
    print("\n🔄 트레이딩 봇 재시작 중...")

    try:
        # PM2 재시작
        result = subprocess.run(['pm2', 'restart', 'auto-trader'],
                                capture_output=True, text=True)

        if result.returncode == 0:
            print("✅ PM2 재시작 성공")
        else:
            print(f"⚠️ PM2 재시작 경고: {result.stderr}")

    except Exception as e:
        print(f"❌ 재시작 오류: {e}")
        print("💡 수동으로 'pm2 restart auto-trader' 실행해주세요.")


def main():
    print("🚀 Auto-Coin 설정 최적화 도구")
    print("=" * 40)

    try:
        # 즉시 개선사항 적용
        improvements_count = apply_immediate_fixes()

        if improvements_count > 0:
            print(f"\n📊 총 {improvements_count}개 개선사항 적용됨")

            # 재시작 확인
            restart_choice = input("\n🤔 트레이딩 봇을 재시작하시겠습니까? (y/N): ").lower()

            if restart_choice in ['y', 'yes']:
                restart_trading_bot()
                print("\n✅ 모든 최적화 완료!")
            else:
                print("\n⚠️ 설정 변경사항 적용을 위해 나중에 재시작해주세요.")
                print("   명령어: pm2 restart auto-trader")
        else:
            print("\n✅ 설정이 이미 최적화되어 있습니다!")

        print("\n📋 다음 단계:")
        print("   1. auto_optimizer.py 실행으로 자동 최적화 시작")
        print("   2. 실시간 모니터링 및 동적 개선")
        print("   3. 수익률 개선 효과 확인")

    except Exception as e:
        print(f"❌ 오류 발생: {e}")


if __name__ == "__main__":
    main()
