#!/usr/bin/env python3
"""
Скрипт для запуска API тестов ноды
"""
import sys
import subprocess


def run_tests():
    """Запускает тесты API"""
    print("=" * 60)
    print("Запуск тестов API инициализации ноды")
    print("=" * 60)
    print()
    
    cmd = [
        sys.executable, "-m", "pytest",
        "tests/test_api/test_node.py",
        "-v",
        "--tb=short",
        "--color=yes"
    ]
    
    try:
        result = subprocess.run(cmd, check=False)
        return result.returncode
    except Exception as e:
        print(f"Ошибка при запуске тестов: {e}")
        return 1


def run_tests_with_coverage():
    """Запускает тесты с coverage"""
    print("=" * 60)
    print("Запуск тестов API с coverage")
    print("=" * 60)
    print()
    
    cmd = [
        sys.executable, "-m", "pytest",
        "tests/test_api/test_node.py",
        "-v",
        "--tb=short",
        "--color=yes",
        "--cov=services.node",
        "--cov=dependencies.settings",
        "--cov-report=term-missing",
        "--cov-report=html"
    ]
    
    try:
        result = subprocess.run(cmd, check=False)
        if result.returncode == 0:
            print()
            print("=" * 60)
            print("Coverage отчет сохранен в htmlcov/index.html")
            print("=" * 60)
        return result.returncode
    except Exception as e:
        print(f"Ошибка при запуске тестов: {e}")
        return 1


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Запуск API тестов")
    parser.add_argument(
        "--coverage",
        action="store_true",
        help="Запустить с coverage анализом"
    )
    
    args = parser.parse_args()
    
    if args.coverage:
        exit_code = run_tests_with_coverage()
    else:
        exit_code = run_tests()
    
    sys.exit(exit_code)

