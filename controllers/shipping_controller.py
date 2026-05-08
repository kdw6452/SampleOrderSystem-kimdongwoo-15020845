# -*- coding: utf-8 -*-
# controllers/shipping_controller.py — 출고 대기 목록 조회 및 출고 실행
from __future__ import annotations

from controllers.base_controller import BaseController
from models.order import Order, OrderStatus
from models.order_repository import OrderRepository
from models.sample_repository import SampleRepository
from views.base_view import BaseView
from views.dto import OrderDto


def _to_dto(order: Order, sample_name: str, stock: int | None = None) -> OrderDto:
    return OrderDto(
        id=order.id,
        sample_name=sample_name,
        quantity=order.quantity,
        customer=order.customer,
        status=order.status.value,
        stock=stock,
    )


class ShippingController(BaseController):
    """출고 처리 서브메뉴를 담당하는 Controller.

    의존성: SampleRepository, OrderRepository, BaseView
    print()/input() 사용 금지 — View 메서드만 사용
    """

    _MENU = (
        "1. 출고 대기 목록",
        "2. 출고 실행",
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
        """출고 처리 서브메뉴 루프."""
        while True:
            self._view.show_message("=== 출고 처리 ===")
            for item in self._MENU:
                self._view.show_message(item)
            choice = self._view.prompt_menu_choice("메뉴 선택")
            if choice == "1":
                self._list_confirmed()
            elif choice == "2":
                self._ship()
            elif choice == "0":
                break
            else:
                self._view.show_error("올바른 메뉴 번호를 입력하세요")

    # ------------------------------------------------------------------
    # 공개 커맨드 (테스트 및 내부 호출용)
    # ------------------------------------------------------------------

    def list_confirmed(self) -> None:
        """출고 대기 목록 표시."""
        self._list_confirmed()

    def ship(self) -> None:
        """출고 실행."""
        self._ship()

    # ------------------------------------------------------------------
    # 내부 구현
    # ------------------------------------------------------------------

    def _list_confirmed(self) -> None:
        orders = self._order_repo.get_by_status(OrderStatus.CONFIRMED)
        dtos = []
        for o in orders:
            sample = self._sample_repo.get_by_id(o.sample_id)
            sample_name = sample.name if sample else f"(ID:{o.sample_id})"
            stock = sample.stock if sample else None
            dtos.append(_to_dto(o, sample_name, stock))
        self._view.show_orders(dtos)

    def _ship(self) -> None:
        raw_id = self._view.prompt_input("출고할 주문 ID").strip()
        try:
            order_id = int(raw_id)
        except ValueError:
            self._view.show_error("주문 ID는 정수여야 합니다")
            return

        order = self._order_repo.get_by_id(order_id)
        if order is None:
            self._view.show_error(f"존재하지 않는 주문 ID입니다: {order_id}")
            return
        if order.status != OrderStatus.CONFIRMED:
            self._view.show_error(
                f"CONFIRMED 상태의 주문만 출고할 수 있습니다. 현재 상태: {order.status.value}"
            )
            return

        sample = self._sample_repo.get_by_id(order.sample_id)
        if sample is None:
            self._view.show_error(f"시료를 찾을 수 없습니다. sample_id={order.sample_id}")
            return

        # 상태 전이 먼저 — 실패 시 재고 변동 없음
        try:
            self._order_repo.update_status(order.id, OrderStatus.RELEASE)
        except ValueError as exc:
            self._view.show_error(str(exc))
            return

        # 전이 성공 후 재고 차감
        quantity = order.quantity
        sample.stock -= quantity
        self._sample_repo.update(sample)
        self._view.show_message(
            f"주문 {order.id} RELEASE 전환. 차감 수량: {quantity}, 잔여 재고: {sample.stock}"
        )
