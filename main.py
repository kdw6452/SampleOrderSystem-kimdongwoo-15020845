# -*- coding: utf-8 -*-
# main.py — Composition Root
# Phase 1: 빈 진입점 (실행 확인용)
# Phase 4 완료 시 print() 제거 후 MainController 조립 예정
import sys
import io


def main() -> None:
    # Windows 콘솔 UTF-8 출력 설정
    if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    # TODO Phase 4: MainController 생성자 주입 조립 및 실행으로 교체
    print("시스템 시작")


if __name__ == "__main__":
    main()
