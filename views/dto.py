# -*- coding: utf-8 -*-
# views/dto.py — 표시 전용 DTO (Model → View 변환 전용)
# Controller가 Model 객체를 DTO로 변환하여 View에 전달한다.
# View는 DTO만 수신하며, 원시 Model에 직접 접근하지 않는다.
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class SampleDto:
    id: int
    name: str
    avg_production_time: float
    yield_rate: float
    stock: int
    # MonitoringController가 채움 ('여유'|'부족'|'고갈'). ""이면 View 미표시
    stock_status: str = field(default="")


@dataclass
class OrderDto:
    id: int
    sample_name: str
    quantity: int
    customer: str
    status: str  # OrderStatus.value (str)
    # ShippingController가 채움 (Sample.stock 현재값). None이면 View 미표시
    stock: int | None = field(default=None)


@dataclass
class ProductionJobDto:
    order_id: int
    sample_name: str
    customer: str
    quantity: int
    shortfall: int      # PRODUCING 주문에서만 사용, 항상 int
    actual_qty: int
    total_time: float
