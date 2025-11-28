#!/usr/bin/env python3
"""
프로젝트 구조 분석 및 정리 계획
현재 사용 중인 파일과 미사용 파일을 구분하고 최적화 방안 제시
"""

import os
import ast
import sqlite3
from pathlib import Path
from datetime import datetime


class ProjectAnalyzer:
    def __init__(self, project_root):
        self.project_root = Path(project_root)
        self.active_files = set()
        self.unused_files = set()
        self.dependencies = {}

    def analyze_imports(self, file_path):
        """Python 파일의 import 분석"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                tree = ast.parse(f.read())

            imports = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports.append(node.module)

            return imports
        except:
            return []

    def scan_project(self):
        """프로젝트 전체 스캔"""
        print("🔍 프로젝트 구조 분석 중...")

        # 1. 실행 가능한 주요 파일들 (진입점)
        entry_points = [
            "main.py",
            "scripts/auto_optimizer.py",
            "scripts/real_upbit_analyzer.py",
            "scripts/data_sync_integration.py"
        ]

        # 2. 서버에서 실행되는 파일들 (PM2 기준)
        server_active = [
            "main.py",  # auto-trader
            "scripts/auto_optimizer.py"  # auto-optimizer
        ]

        # 3. 모든 Python 파일 스캔
        all_py_files = []
        for py_file in self.project_root.rglob("*.py"):
            relative_path = py_file.relative_to(self.project_root)
            all_py_files.append(str(relative_path))

        # 4. 의존성 분석
        for file_path in all_py_files:
            full_path = self.project_root / file_path
            imports = self.analyze_imports(full_path)
            self.dependencies[file_path] = imports

        return entry_points, server_active, all_py_files

    def identify_active_files(self):
        """활성 파일 식별"""
        entry_points, server_active, all_files = self.scan_project()

        # 확실히 활성화된 파일들
        confirmed_active = set(server_active)

        # 추가로 중요한 파일들
        important_files = {
            "modules/config_manager.py",
            "modules/trading_engine.py",
            "modules/learning_system.py",
            "modules/notification_manager.py",
            "scripts/real_upbit_analyzer.py",
            "scripts/data_sync_integration.py"
        }

        confirmed_active.update(important_files)

        # 의존성을 통해 활성 파일 추적
        def trace_dependencies(file_path):
            if file_path in self.dependencies:
                for imp in self.dependencies[file_path]:
                    # 로컬 모듈 import 처리
                    if imp.startswith('modules.') or imp.startswith('scripts.'):
                        module_path = imp.replace('.', '/') + '.py'
                        if (self.project_root / module_path).exists():
                            confirmed_active.add(module_path)
                            trace_dependencies(module_path)

        # 진입점들로부터 의존성 추적
        for entry in confirmed_active.copy():
            trace_dependencies(entry)

        return confirmed_active, set(all_files) - confirmed_active

    def analyze_data_sources(self):
        """데이터 소스 분석"""
        data_files = {
            "trade_history.db": "로컬 거래 기록",
            "upbit_sync.db": "실제 업비트 동기화 데이터",
            "config.yaml": "설정 파일",
            "trading_data.json": "실시간 거래 데이터",
            "sell_signals.json": "매도 신호 데이터",
            "optimization_history.json": "최적화 기록"
        }

        return data_files

    def generate_report(self):
        """분석 결과 리포트 생성"""
        active_files, unused_files = self.identify_active_files()
        data_sources = self.analyze_data_sources()

        print("="*80)
        print("📊 프로젝트 구조 분석 결과")
        print("="*80)

        print("\n🟢 활성 파일들 (현재 사용 중):")
        for file in sorted(active_files):
            if (self.project_root / file).exists():
                print(f"   ✅ {file}")

        print("\n🟡 미사용 파일들 (정리 대상):")
        for file in sorted(unused_files):
            if (self.project_root / file).exists():
                print(f"   🗑️  {file}")

        print("\n📁 데이터 소스 현황:")
        for data_file, desc in data_sources.items():
            file_path = self.project_root / data_file
            if file_path.exists():
                size = file_path.stat().st_size
                print(f"   📄 {data_file}: {desc} ({size:,} bytes)")

        return active_files, unused_files, data_sources


def main():
    project_root = "/Users/Daeho/Projects/auto-coin"
    analyzer = ProjectAnalyzer(project_root)

    active_files, unused_files, data_sources = analyzer.generate_report()

    print("\n" + "="*80)
    print("🎯 정리 계획 제안")
    print("="*80)

    print("\n1️⃣ 핵심 구조 (유지):")
    core_structure = [
        "main.py - 메인 트레이딩 봇",
        "modules/ - 핵심 모듈들",
        "scripts/real_upbit_analyzer.py - 업비트 데이터 동기화",
        "scripts/auto_optimizer.py - 자동 최적화",
        "config.yaml - 설정 관리"
    ]
    for item in core_structure:
        print(f"   📌 {item}")

    print("\n2️⃣ 정리 대상 (이동/삭제):")
    cleanup_items = [
        "scripts/에서 미사용 파일들 → archive/ 폴더로 이동",
        "중복 기능 파일들 통합",
        "테스트 파일들 → tests/ 폴더 정리",
        "문서 파일들 → docs/ 폴더 통합"
    ]
    for item in cleanup_items:
        print(f"   🧹 {item}")

    print("\n3️⃣ 데이터 통합:")
    print("   📊 upbit_sync.db → 실제 업비트 데이터 (메인)")
    print("   📈 trade_history.db → 로컬 백업용으로 변경")
    print("   ⚙️ JSON 파일들 → 임시 데이터용으로 정리")


if __name__ == "__main__":
    main()
