# -*- coding: utf-8 -*-
# controllers/base_controller.py — BaseController ABC
from __future__ import annotations

from abc import ABC, abstractmethod


class BaseController(ABC):
    """모든 Controller의 추상 기반 클래스.

    run() 메서드를 구현하여 해당 도메인의 서브메뉴 루프를 담당한다.
    """

    @abstractmethod
    def run(self) -> None:
        """서브메뉴 루프를 실행한다."""
        ...
