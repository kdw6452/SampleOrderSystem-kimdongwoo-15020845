# -*- coding: utf-8 -*-
# controllers/production_controller.py — 생산 현황, 대기 큐, 생산 완료 명령
from __future__ import annotations

import math

from controllers.base_controller import BaseController
from models.order import Order, OrderStatus
from models.order_repository import OrderRepository
from models.sample_repository import SampleRepository
from views.base_view import BaseView
from views.dto import ProductionJobDto


def _calc_actual_qty(shortfall: int, yield_rate: float) -> int:
    """실생산량 계산: ceil(shortfall / (yield_rate * 0.9))."""
    return math.ceil(shortfall / (yield_rate * 0.9))


def _calc_total_time(avg_production_time: float, actual_qty: int) -> float:
    """총 생산시간 계산: avg_production_time * actual_qty."""
    return avg_production_time * actual_qty


class ProductionController(BaseController):
    """생산라인 서브메뉴를 담당하는 Controller.

    FIFO 보장: PRODUCING 주문을 ID 오름차순 정렬로 처리 순서를 결정한다.
    의존성: SampleRepository, OrderRepository, BaseView
    print()/input() 사용 금지 — View 메서드만 사용
    """

    _MENU = (
        "1. 생산 현황",
        "2. 생산 대기 큐",
        "3. 생산 완료",
        "0. 돌아가기",
    )

    def __init__(
        self,
        sample_repository: SampleRepository,
        order_repository: OrderRepository,
        view: BaseView,
    ) -> None:
        self._sample_repo = sample_repository
        self._order_repo = order_repository
        self._view = view

    # ------------------------------------------------------------------
    # BaseController 구현
    # ------------------------------------------------------------------

    def run(self) -> None:
        """생산라인 서브메뉴 루프."""
        while True:
            self._view.show_message("=== 생산라인 ===")
            for item in self._MENU:
                self._view.show_message(item)
            choice = self._view.prompt_menu_choice("메뉴 선택")
            if choice == "1":
                self._show_status()
            elif choice == "2":
                self._show_queue()
            elif choice == "3":
                self._complete()
            elif choice == "0":
                break
            else:
                self._view.show_error("올바른 메뉴 번호를 입력하세요")

    # ------------------------------------------------------------------
    # 공개 커맨드 (테스트 및 내부 호출용)
    # ------------------------------------------------------------------

    def show_status(self) -> None:
        """생산 현황 표시."""
        self._show_status()

    def show_queue(self) -> None:
        """생산 대기 큐 표시."""
        self._show_queue()

    def complete(self) -> None:
        """생산 완료 명령."""
        self._complete()

    # ------------------------------------------------------------------
    # 내부 헬퍼
    # ------------------------------------------------------------------

    def _get_producing_sorted(self) -> list[Order]:
        """PRODUCING 상태 주문을 ID 오름차순(FIFO)으로 반환한다."""
        return sorted(
            self._order_repo.get_by_status(OrderStatus.PRODUCING),
            key=lambda o: o.id,
        )

    def _build_job_dto(self, order: Order) -> ProductionJobDto | None:
        """Order → ProductionJobDto 변환. 시료를 찾지 못하면 None."""
        sample = self._sample_repo.get_by_id(order.sample_id)
        if sample is None:
            return None
        if order.shortfall is None:
            return None
        actual_qty = _calc_actual_qty(order.shortfall, sample.yield_rate)
        total_time = _calc_total_time(sample.avg_production_time, actual_qty)
        return ProductionJobDto(
            order_id=order.id,
            sample_name=sample.name,
            customer=order.customer,
            quantity=order.quantity,
            shortfall=order.shortfall,
            actual_qty=actual_qty,
            total_time=total_time,
        )

    # ------------------------------------------------------------------
    # 내부 구현
    # ------------------------------------------------------------------

    def _show_status(self) -> None:
        producing = self._get_producing_sorted()
        if not producing:
            self._view.show_message("생산 중인 작업이 없습니다")
            return
        job = self._build_job_dto(producing[0])
        self._view.show_production_status(job)

    def _show_queue(self) -> None:
        producing = self._get_producing_sorted()
        jobs: list[ProductionJobDto] = []
        for order in producing:
            job = self._build_job_dto(order)
            if job is not None:
                jobs.append(job)
        self._view.show_production_queue(jobs)

    def _complete(self) -> None:
        producing = self._get_producing_sorted()

        # Guard clause: PRODUCING 없으면 에러 후 중단
        if not producing:
            self._view.show_error("생산 중인 작업이 없습니다")
            return

        order = producing[0]

        # 방어 코드: shortfall None 이면 에러 후 중단 (정상 흐름에서 발생 불가)
        if order.shortfall is None:
            self._view.show_error(
                f"주문 {order.id}의 shortfall 값이 없습니다. 데이터 무결성 오류입니다."
            )
            return

        sample = self._sample_repo.get_by_id(order.sample_id)
        if sample is None:
            self._view.show_error(f"시료를 찾을 수 없습니다. sample_id={order.sample_id}")
            return

        # 상태 전이 먼저 — 실패 시 재고 변동 없음
        try:
            self._order_repo.update_status(order.id, OrderStatus.CONFIRMED)
        except ValueError as exc:
            self._view.show_error(str(exc))
            return

        # 전이 성공 후 재고 증가
        shortfall = order.shortfall
        sample.stock += shortfall
        self._sample_repo.update(sample)
        self._view.show_message(
            f"주문 {order.id} CONFIRMED 전환. 재고 +{shortfall}"
        )
