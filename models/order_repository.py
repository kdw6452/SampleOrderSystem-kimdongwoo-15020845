# -*- coding: utf-8 -*-
# models/order_repository.py — OrderRepository ABC + JsonOrderRepository
# models/ 내에서 views/, controllers/ import 금지
from __future__ import annotations

import abc
import dataclasses
import json
import os
import tempfile

from models.order import Order, OrderStatus

# 허용 상태 전이 맵 — 값이 빈 frozenset이면 종단 상태
_ALLOWED_TRANSITIONS: dict[OrderStatus, frozenset[OrderStatus]] = {
    OrderStatus.RESERVED: frozenset(
        {OrderStatus.CONFIRMED, OrderStatus.PRODUCING, OrderStatus.REJECTED}
    ),
    OrderStatus.PRODUCING: frozenset({OrderStatus.CONFIRMED}),
    OrderStatus.CONFIRMED: frozenset({OrderStatus.RELEASE}),
    OrderStatus.REJECTED: frozenset(),
    OrderStatus.RELEASE: frozenset(),
}


class OrderRepository(abc.ABC):
    """OrderRepository 추상 기반 클래스."""

    @abc.abstractmethod
    def add(self, order: Order) -> Order:
        """주문을 저장하고 ID가 부여된 Order를 반환한다."""

    @abc.abstractmethod
    def get_all(self) -> list[Order]:
        """등록된 전체 주문 목록을 반환한다."""

    @abc.abstractmethod
    def get_by_id(self, id: int) -> Order | None:
        """ID로 주문을 조회한다. 없으면 None 반환."""

    @abc.abstractmethod
    def get_by_status(self, status: OrderStatus) -> list[Order]:
        """특정 상태의 주문 목록을 반환한다."""

    @abc.abstractmethod
    def update_status(self, order_id: int, new_status: OrderStatus) -> Order:
        """주문 상태를 전이한다. 허용되지 않은 전이 시 ValueError를 발생시킨다."""


class JsonOrderRepository(OrderRepository):
    """JSON 파일 기반 OrderRepository 구현체.

    os.replace()를 사용한 원자적 쓰기로 중간 상태 노출을 방지한다.
    ID는 기존 최대 ID + 1로 단조 증가하며, 삭제 후에도 재사용하지 않는다.
    상태 전이 규칙은 _ALLOWED_TRANSITIONS로 강제하며, 위반 시 ValueError.
    """

    def __init__(self, path: str = "data/orders.json") -> None:
        self._path = path
        dir_name = os.path.dirname(path)
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def add(self, order: Order) -> Order:
        orders = self._load()
        new_id = self._next_id(orders)
        new_order = dataclasses.replace(order, id=new_id)
        orders.append(new_order)
        self._save(orders)
        return new_order

    def get_all(self) -> list[Order]:
        return self._load()

    def get_by_id(self, id: int) -> Order | None:
        for order in self._load():
            if order.id == id:
                return order
        return None

    def get_by_status(self, status: OrderStatus) -> list[Order]:
        return [o for o in self._load() if o.status == status]

    def update_status(self, order_id: int, new_status: OrderStatus) -> Order:
        orders = self._load()
        for i, order in enumerate(orders):
            if order.id == order_id:
                allowed = _ALLOWED_TRANSITIONS[order.status]
                if new_status not in allowed:
                    raise ValueError(
                        f"허용되지 않은 상태 전이: {order.status.value} → {new_status.value}"
                    )
                updated = dataclasses.replace(order, status=new_status)
                orders[i] = updated
                self._save(orders)
                return updated
        raise ValueError(f"Order with id={order_id} not found.")

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _next_id(self, orders: list[Order]) -> int:
        if not orders:
            return 1
        return max(o.id for o in orders) + 1

    def _load(self) -> list[Order]:
        if not os.path.exists(self._path):
            return []
        with open(self._path, encoding="utf-8") as f:
            raw: list[dict] = json.load(f)
        result: list[Order] = []
        for item in raw:
            item["status"] = OrderStatus(item["status"])
            result.append(Order(**item))
        return result

    def _save(self, orders: list[Order]) -> None:
        data: list[dict] = []
        for o in orders:
            d = dataclasses.asdict(o)
            d["status"] = o.status.value  # Enum → 문자열 직렬화
            data.append(d)
        dir_name = os.path.dirname(self._path)
        fd, tmp_path = tempfile.mkstemp(
            dir=dir_name if dir_name else ".", suffix=".tmp"
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            os.replace(tmp_path, self._path)
        except Exception:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise
