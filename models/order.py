# -*- coding: utf-8 -*-
# models/order.py — OrderStatus Enum + Order 엔티티
# 비즈니스 검증은 Controller 담당, 엔티티는 단순 데이터 컨테이너
from __future__ import annotations

import enum
from dataclasses import dataclass, field


class OrderStatus(enum.Enum):
    RESERVED = "RESERVED"
    REJECTED = "REJECTED"
    PRODUCING = "PRODUCING"
    CONFIRMED = "CONFIRMED"
    RELEASE = "RELEASE"


@dataclass
class Order:
    id: int
    sample_id: int
    quantity: int
    customer: str
    status: OrderStatus
    shortfall: int | None = field(default=None)
