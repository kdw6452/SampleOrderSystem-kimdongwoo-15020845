# -*- coding: utf-8 -*-
# models/sample.py — Sample 엔티티
# 비즈니스 검증은 Controller 담당, 엔티티는 단순 데이터 컨테이너
from dataclasses import dataclass, field


@dataclass
class Sample:
    id: int
    name: str
    avg_production_time: float
    yield_rate: float
    stock: int = field(default=0)
