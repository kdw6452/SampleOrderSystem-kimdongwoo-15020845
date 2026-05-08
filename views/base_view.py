# -*- coding: utf-8 -*-
# views/base_view.py — BaseView ABC
# 모든 콘솔 I/O 메서드 시그니처를 정의한다.
# views/ 내에서 controllers/ import 금지.
from __future__ import annotations

import abc

from views.dto import OrderDto, ProductionJobDto, SampleDto


class BaseView(abc.ABC):
    """콘솔 I/O 추상 인터페이스.

    구현 클래스(ConsoleView)는 print()/input()을 독점 사용한다.
    View는 str만 반환하며, 타입 변환을 수행하지 않는다.
    """

    @abc.abstractmethod
    def show_main_menu(self, samples: list[SampleDto]) -> None:
        """시료 요약 정보와 메인 메뉴 번호 목록을 표시한다.

        samples가 빈 리스트이면 "등록된 시료가 없습니다" 출력 후 메뉴 목록을 표시한다.
        """
        ...

    @abc.abstractmethod
    def show_samples(self, samples: list[SampleDto]) -> None:
        """전체 시료 목록을 표시한다."""
        ...

    @abc.abstractmethod
    def show_orders(self, orders: list[OrderDto]) -> None:
        """주문 목록을 표시한다."""
        ...

    @abc.abstractmethod
    def show_monitoring(
        self,
        orders: list[OrderDto],
        samples: list[SampleDto],
    ) -> None:
        """모니터링 화면을 표시한다.

        MonitoringController가 REJECTED를 제외한 4개 상태(RESERVED/PRODUCING/CONFIRMED/RELEASE)
        주문만 필터링하여 전달한다. View가 status 필드로 그룹핑하여 렌더링한다.

        Rich Table 2개 출력:
        - 주문량 Table: 상태별 그룹핑 (RESERVED → PRODUCING → CONFIRMED → RELEASE 순)
        - 재고량 Table: 시료별 재고 및 재고 상태
        """
        ...

    @abc.abstractmethod
    def show_production_status(self, job: ProductionJobDto | None) -> None:
        """현재 생산 중인 작업 정보를 표시한다.

        job이 None이면 "생산 중인 작업이 없습니다" 메시지를 출력한다.
        shortfall(부족분) 열을 포함한다.
        """
        ...

    @abc.abstractmethod
    def show_production_queue(self, jobs: list[ProductionJobDto]) -> None:
        """생산 대기 큐를 표시한다.

        enumerate(jobs, start=1)로 1-based 대기 순번을 부여한다.
        shortfall 열은 표시하지 않는다.
        jobs가 빈 리스트이면 "대기 중인 생산 작업이 없습니다" 메시지를 출력한다.
        """
        ...

    @abc.abstractmethod
    def show_message(self, message: str) -> None:
        """정상 흐름 1회성 알림을 표시한다.

        주문 생성 결과(ID + RESERVED), 주문 승인/거절 결과,
        생산 완료 결과(ID + CONFIRMED), 출고 완료 결과(차감 재고 + RELEASE) 등
        단순 1회성 안내에 범용 사용한다.
        """
        ...

    @abc.abstractmethod
    def show_error(self, message: str) -> None:
        """입력 오류·상태 위반 메시지를 표시한다."""
        ...

    @abc.abstractmethod
    def prompt_input(self, prompt: str) -> str:
        """이름·수량 등 일반 데이터 입력을 받는다. 원시 str을 반환한다."""
        ...

    @abc.abstractmethod
    def prompt_menu_choice(self, prompt: str) -> str:
        """메뉴 번호 입력을 받는다. 원시 str을 반환한다."""
        ...
