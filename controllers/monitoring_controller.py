# -*- coding: utf-8 -*-
# controllers/monitoring_controller.py — 상태별 집계, 재고 현황
from __future__ import annotations

from controllers.base_controller import BaseController
from models.order import Order, OrderStatus
from models.order_repository import OrderRepository
from models.sample import Sample
from models.sample_repository import SampleRepository
from views.base_view import BaseView
from views.dto import OrderDto, SampleDto

# 모니터링에서 표시하는 4개 유효 상태 (REJECTED 제외)
_VALID_STATUSES = frozenset(
    {
        OrderStatus.RESERVED,
        OrderStatus.PRODUCING,
        OrderStatus.CONFIRMED,
        OrderStatus.RELEASE,
    }
)

# 재고 부족 판정 기준이 되는 진행 중 주문 상태
_IN_PROGRESS_STATUSES = frozenset(
    {
        OrderStatus.RESERVED,
        OrderStatus.PRODUCING,
        OrderStatus.CONFIRMED,
    }
)


def _order_to_dto(order: Order, sample_name: str) -> OrderDto:
    return OrderDto(
        id=order.id,
        sample_name=sample_name,
        quantity=order.quantity,
        customer=order.customer,
        status=order.status.value,
    )


def _determine_stock_status(stock: int, in_progress_qty: int) -> str:
    """재고 상태를 판정한다.

    고갈: stock == 0
    부족: 0 < stock < in_progress_qty
    여유: stock >= in_progress_qty
    """
    if stock == 0:
        return "고갈"
    if stock < in_progress_qty:
        return "부족"
    return "여유"


class MonitoringController(BaseController):
    """모니터링 서브메뉴를 담당하는 Controller.

    REJECTED를 제외한 4개 상태의 주문량과 시료별 재고 현황을 표시한다.
    의존성: SampleRepository, OrderRepository, BaseView
    """

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
        """모니터링 화면을 표시한다."""
        self._show()

    # ------------------------------------------------------------------
    # 내부 구현
    # ------------------------------------------------------------------

    def _show(self) -> None:
        all_orders = self._order_repo.get_all()
        all_samples = self._sample_repo.get_all()

        # 시료 ID → 이름 맵
        sample_name_map: dict[int, str] = {s.id: s.name for s in all_samples}

        # REJECTED 제외 4개 상태 주문만 필터링
        valid_orders = [o for o in all_orders if o.status in _VALID_STATUSES]
        order_dtos = [
            _order_to_dto(o, sample_name_map.get(o.sample_id, f"(ID:{o.sample_id})"))
            for o in valid_orders
        ]

        # 시료별 진행 중 주문 수량 합산 (RESERVED + PRODUCING + CONFIRMED)
        in_progress_qty_map: dict[int, int] = {}
        for o in all_orders:
            if o.status in _IN_PROGRESS_STATUSES:
                in_progress_qty_map[o.sample_id] = (
                    in_progress_qty_map.get(o.sample_id, 0) + o.quantity
                )

        sample_dtos: list[SampleDto] = []
        for s in all_samples:
            in_progress = in_progress_qty_map.get(s.id, 0)
            stock_status = _determine_stock_status(s.stock, in_progress)
            sample_dtos.append(
                SampleDto(
                    id=s.id,
                    name=s.name,
                    avg_production_time=s.avg_production_time,
                    yield_rate=s.yield_rate,
                    stock=s.stock,
                    stock_status=stock_status,
                )
            )

        self._view.show_monitoring(order_dtos, sample_dtos)
