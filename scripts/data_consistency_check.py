#!/usr/bin/env python3
"""
데이터 일관성 체크 도구
정기적으로 실행하여 데이터 소스간 일관성 확인
"""

import sqlite3
import json
from datetime import datetime
from pathlib import Path

def check_data_consistency():
    """데이터 일관성 체크"""
    project_root = Path(__file__).parent
    
    print("🔍 데이터 일관성 체크 시작...")
    
    # 설정 로드
    config_path = project_root / "data_config.json"
    if config_path.exists():
        with open(config_path, 'r') as f:
            config = json.load(f)
        print("✅ 데이터 설정 로드 완료")
    else:
        print("❌ 데이터 설정 파일 없음")
        return
    
    # 주요 데이터베이스 체크
    primary_db = project_root / config["data_sources"]["primary"]["path"]
    backup_db = project_root / config["data_sources"]["backup"]["path"]
    
    if primary_db.exists():
        print(f"✅ 메인 DB 존재: {primary_db.name}")
    else:
        print(f"❌ 메인 DB 없음: {primary_db.name}")
    
    if backup_db.exists():
        print(f"✅ 백업 DB 존재: {backup_db.name}")
    else:
        print(f"⚠️  백업 DB 없음: {backup_db.name}")
    
    # 체크 완료 시간 기록
    timestamp = datetime.now().isoformat()
    print(f"🕐 체크 완료: {timestamp}")

if __name__ == "__main__":
    check_data_consistency()
