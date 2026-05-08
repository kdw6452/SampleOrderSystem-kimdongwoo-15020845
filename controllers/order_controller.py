# -*- coding: utf-8 -*-
# controllers/order_controller.py — 주문 접수·승인·거절
from __future__ import annotations

import math

from controllers.base_controller import BaseController
from models.order import Order, OrderStatus
from models.order_repository import OrderRepository
from models.sample_repository import SampleRepository
from views.base_view import BaseView
from views.dto import OrderDto


def _to_dto(order: Order, sample_name: str) -> OrderDto:
    return OrderDto(
        id=order.id,
        sample_name=sample_name,
        quantity=order.quantity,
        customer=order.customer,
        status=order.status.value,
    )


class OrderController(BaseController):
    """주문 관련 서브메뉴를 담당하는 Controller.

    의존성: SampleRepository, OrderRepository, BaseView
    print()/input() 사용 금지 — View 메서드만 사용
    """

    _MENU = (
        "1. 주문 접수",
        "2. 접수된 주문 목록",
        "3. 주문 승인",
        "4. 주문 거절",
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
        """주문 관리 서브메뉴 루프."""
        while True:
            self._view.show_message("=== 주문 관리 ===")
            for item in self._MENU:
                self._view.show_message(item)
            choice = self._view.prompt_menu_choice("메뉴 선택")
            if choice == "1":
                self._receive()
            elif choice == "2":
                self._list_reserved()
            elif choice == "3":
                self._approve()
            elif choice == "4":
                self._reject()
            elif choice == "0":
                break
            else:
                self._view.show_error("올바른 메뉴 번호를 입력하세요")

    # ------------------------------------------------------------------
    # 공개 커맨드 (테스트 및 내부 호출용)
    # ------------------------------------------------------------------

    def receive(self) -> None:
        """주문 접수."""
        self._receive()

    def list_reserved(self) -> None:
        """접수된 주문 목록."""
        self._list_reserved()

    def approve(self) -> None:
        """주문 승인."""
        self._approve()

    def reject(self) -> None:
        """주문 거절."""
        self._reject()

    # ------------------------------------------------------------------
    # 내부 구현
    # ------------------------------------------------------------------

    def _receive(self) -> None:
        raw_sample_id = self._view.prompt_input("시료 ID").strip()
        try:
            sample_id = int(raw_sample_id)
        except ValueError:
            self._view.show_error("시료 ID는 정수여야 합니다")
            return

        sample = self._sample_repo.get_by_id(sample_id)
        if sample is None:
            self._view.show_error(f"존재하지 않는 시료 ID입니다: {sample_id}")
            return

        customer = self._view.prompt_input("고객명").strip()
        if not customer:
            self._view.show_error("고객명은 공백일 수 없습니다")
            return

        raw_qty = self._view.prompt_input("주문 수량").strip()
        try:
            quantity = int(raw_qty)
        except ValueError:
            self._view.show_error("주문 수량은 정수여야 합니다")
            return
        if quantity < 1:
            self._view.show_error("주문 수량은 1 이상이어야 합니다")
            return

        order = Order(
            id=0,
            sample_id=sample_id,
            quantity=quantity,
            customer=customer,
            status=OrderStatus.RESERVED,
        )
        saved = self._order_repo.add(order)
        self._view.show_message(f"주문 {saved.id} 접수 완료. 상태: RESERVED")

    def _list_reserved(self) -> None:
        orders = self._order_repo.get_by_status(OrderStatus.RESERVED)
        dtos = []
        for o in orders:
            sample = self._sample_repo.get_by_id(o.sample_id)
            sample_name = sample.name if sample else f"(ID:{o.sample_id})"
            dtos.append(_to_dto(o, sample_name))
        self._view.show_orders(dtos)

    def _approve(self) -> None:
        raw_id = self._view.prompt_input("승인할 주문 ID").strip()
        try:
            order_id = int(raw_id)
        except ValueError:
            self._view.show_error("주문 ID는 정수여야 합니다")
            return

        order = self._order_repo.get_by_id(order_id)
        if order is None:
            self._view.show_error(f"존재하지 않는 주문 ID입니다: {order_id}")
            return
        if order.status != OrderStatus.RESERVED:
            self._view.show_error(
                f"RESERVED 상태의 주문만 승인할 수 있습니다. 현재 상태: {order.status.value}"
            )
            return

        sample = self._sample_repo.get_by_id(order.sample_id)
        if sample is None:
            self._view.show_error(f"시료를 찾을 수 없습니다. sample_id={order.sample_id}")
            return

        if sample.stock >= order.quantity:
            # 재고 충분 → CONFIRMED
            try:
                self._order_repo.update_status(order.id, OrderStatus.CONFIRMED)
            except ValueError as exc:
                self._view.show_error(str(exc))
                return
            self._view.show_message(f"주문 {order.id} CONFIRMED 전환")
        else:
            # 재고 부족 → PRODUCING
            shortfall = max(0, order.quantity - sample.stock)
            order.shortfall = shortfall
            try:
                self._order_repo.update(order)
                self._order_repo.update_status(order.id, OrderStatus.PRODUCING)
            except ValueError as exc:
                self._view.show_error(str(exc))
                return
            actual_qty = math.ceil(shortfall / (sample.yield_rate * 0.9))
            self._view.show_message(
                f"주문 {order.id} PRODUCING 전환. 부족분: {shortfall}, 실생산량: {actual_qty}"
            )

    def _reject(self) -> None:
        raw_id = self._view.prompt_input("거절할 주문 ID").strip()
        try:
            order_id = int(raw_id)
        except ValueError:
            self._view.show_error("주문 ID는 정수여야 합니다")
            return

        order = self._order_repo.get_by_id(order_id)
        if order is None:
            self._view.show_error(f"존재하지 않는 주문 ID입니다: {order_id}")
            return
        if order.status != OrderStatus.RESERVED:
            self._view.show_error(
                f"RESERVED 상태의 주문만 거절할 수 있습니다. 현재 상태: {order.status.value}"
            )
            return

        try:
            self._order_repo.update_status(order.id, OrderStatus.REJECTED)
        except ValueError as exc:
            self._view.show_error(str(exc))
            return
        self._view.show_message(f"주문 {order.id} REJECTED 전환")
