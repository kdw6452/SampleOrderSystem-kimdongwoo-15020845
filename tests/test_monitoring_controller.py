# -*- coding: utf-8 -*-
# tests/test_monitoring_controller.py — MonitoringController 단위 테스트
# MagicMock으로 SampleRepository·OrderRepository·BaseView 격리
# 재고 상태 판정(여유/부족/고갈), REJECTED 제외, 진행 중 수량 합산 포함
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from controllers.monitoring_controller import (
    MonitoringController,
    _determine_stock_status,
)
from models.order import Order, OrderStatus
from models.sample import Sample
from views.dto import OrderDto, SampleDto


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_repo():
    return MagicMock()


@pytest.fixture
def order_repo():
    return MagicMock()


@pytest.fixture
def view():
    return MagicMock()


@pytest.fixture
def ctrl(sample_repo, order_repo, view) -> MonitoringController:
    return MonitoringController(sample_repo, order_repo, view)


def _make_sample(**kwargs) -> Sample:
    defaults = {
        "id": 1,
        "name": "SampleA",
        "avg_production_time": 30.0,
        "yield_rate": 0.9,
        "stock": 10,
    }
    defaults.update(kwargs)
    return Sample(**defaults)


def _make_order(**kwargs) -> Order:
    defaults = {
        "id": 1,
        "sample_id": 1,
        "quantity": 5,
        "customer": "TestCo",
        "status": OrderStatus.RESERVED,
        "shortfall": None,
    }
    defaults.update(kwargs)
    return Order(**defaults)


# ---------------------------------------------------------------------------
# _determine_stock_status 단위 테스트
# ---------------------------------------------------------------------------

class TestDetermineStockStatus:
    def test_stock_zero_is_고갈(self):
        assert _determine_stock_status(0, 5) == "고갈"

    def test_stock_zero_no_orders_is_고갈(self):
        assert _determine_stock_status(0, 0) == "고갈"

    def test_stock_less_than_in_progress_is_부족(self):
        assert _determine_stock_status(3, 10) == "부족"

    def test_stock_equals_in_progress_is_여유(self):
        assert _determine_stock_status(10, 10) == "여유"

    def test_stock_greater_than_in_progress_is_여유(self):
        assert _determine_stock_status(20, 10) == "여유"

    def test_stock_positive_no_orders_is_여유(self):
        assert _determine_stock_status(5, 0) == "여유"


# ---------------------------------------------------------------------------
# run (모니터링 화면 표시)
# ---------------------------------------------------------------------------

class TestMonitoringRun:
    def test_run_calls_show_monitoring(self, ctrl, sample_repo, order_repo, view):
        """run() → show_monitoring() 호출 확인."""
        order_repo.get_all.return_value = []
        sample_repo.get_all.return_value = []
        ctrl.run()
        view.show_monitoring.assert_called_once()

    def test_rejected_orders_excluded(self, ctrl, sample_repo, order_repo, view):
        """REJECTED 주문은 show_monitoring()에 전달하지 않는다."""
        orders = [
            _make_order(id=1, status=OrderStatus.RESERVED),
            _make_order(id=2, status=OrderStatus.REJECTED),
        ]
        order_repo.get_all.return_value = orders
        sample_repo.get_all.return_value = [_make_sample()]

        ctrl.run()

        order_dtos, _ = view.show_monitoring.call_args[0]
        statuses = {d.status for d in order_dtos}
        assert "REJECTED" not in statuses
        assert len(order_dtos) == 1

    def test_all_four_valid_statuses_included(
        self, ctrl, sample_repo, order_repo, view
    ):
        """4개 유효 상태(RESERVED/PRODUCING/CONFIRMED/RELEASE) 모두 포함."""
        orders = [
            _make_order(id=1, status=OrderStatus.RESERVED),
            _make_order(id=2, status=OrderStatus.PRODUCING, shortfall=3),
            _make_order(id=3, status=OrderStatus.CONFIRMED),
            _make_order(id=4, status=OrderStatus.RELEASE),
        ]
        order_repo.get_all.return_value = orders
        sample_repo.get_all.return_value = [_make_sample()]

        ctrl.run()

        order_dtos, _ = view.show_monitoring.call_args[0]
        statuses = {d.status for d in order_dtos}
        assert statuses == {"RESERVED", "PRODUCING", "CONFIRMED", "RELEASE"}

    def test_stock_status_여유_when_stock_sufficient(
        self, ctrl, sample_repo, order_repo, view
    ):
        """재고 >= 진행 중 수량 합산 → '여유'."""
        # stock=20, RESERVED qty=5+PRODUCING qty=3 → in_progress=8 < 20 → 여유
        orders = [
            _make_order(id=1, status=OrderStatus.RESERVED, quantity=5),
            _make_order(id=2, status=OrderStatus.PRODUCING, quantity=3, shortfall=3),
        ]
        order_repo.get_all.return_value = orders
        sample_repo.get_all.return_value = [_make_sample(stock=20)]

        ctrl.run()

        _, sample_dtos = view.show_monitoring.call_args[0]
        assert sample_dtos[0].stock_status == "여유"

    def test_stock_status_부족_when_stock_insufficient(
        self, ctrl, sample_repo, order_repo, view
    ):
        """0 < 재고 < 진행 중 수량 합산 → '부족'."""
        # stock=3, RESERVED qty=10 → in_progress=10 > 3 → 부족
        orders = [_make_order(id=1, status=OrderStatus.RESERVED, quantity=10)]
        order_repo.get_all.return_value = orders
        sample_repo.get_all.return_value = [_make_sample(stock=3)]

        ctrl.run()

        _, sample_dtos = view.show_monitoring.call_args[0]
        assert sample_dtos[0].stock_status == "부족"

    def test_stock_status_고갈_when_stock_zero(
        self, ctrl, sample_repo, order_repo, view
    ):
        """재고 == 0 → '고갈'."""
        order_repo.get_all.return_value = []
        sample_repo.get_all.return_value = [_make_sample(stock=0)]

        ctrl.run()

        _, sample_dtos = view.show_monitoring.call_args[0]
        assert sample_dtos[0].stock_status == "고갈"

    def test_confirmed_orders_included_in_in_progress_qty(
        self, ctrl, sample_repo, order_repo, view
    ):
        """CONFIRMED 주문도 진행 중 수량에 포함된다."""
        # stock=5, CONFIRMED qty=10 → in_progress=10 > 5 → 부족
        orders = [_make_order(id=1, status=OrderStatus.CONFIRMED, quantity=10)]
        order_repo.get_all.return_value = orders
        sample_repo.get_all.return_value = [_make_sample(stock=5)]

        ctrl.run()

        _, sample_dtos = view.show_monitoring.call_args[0]
        assert sample_dtos[0].stock_status == "부족"

    def test_release_orders_excluded_from_in_progress_qty(
        self, ctrl, sample_repo, order_repo, view
    ):
        """RELEASE 주문은 진행 중 수량에서 제외된다."""
        # stock=2, RELEASE qty=100 → in_progress=0 → 여유(stock>0)
        orders = [_make_order(id=1, status=OrderStatus.RELEASE, quantity=100)]
        order_repo.get_all.return_value = orders
        sample_repo.get_all.return_value = [_make_sample(stock=2)]

        ctrl.run()

        _, sample_dtos = view.show_monitoring.call_args[0]
        assert sample_dtos[0].stock_status == "여유"

    def test_multiple_orders_same_sample_summed(
        self, ctrl, sample_repo, order_repo, view
    ):
        """동일 시료의 진행 중 주문 수량이 합산된다."""
        # stock=10, RESERVED qty=4 + PRODUCING qty=4 = 8 < 10 → 여유
        orders = [
            _make_order(id=1, status=OrderStatus.RESERVED, quantity=4),
            _make_order(id=2, status=OrderStatus.PRODUCING, quantity=4, shortfall=4),
        ]
        order_repo.get_all.return_value = orders
        sample_repo.get_all.return_value = [_make_sample(stock=10)]

        ctrl.run()

        _, sample_dtos = view.show_monitoring.call_args[0]
        assert sample_dtos[0].stock_status == "여유"

    def test_no_samples_passes_empty_sample_list(
        self, ctrl, sample_repo, order_repo, view
    ):
        """시료 없으면 빈 SampleDto 목록 전달."""
        order_repo.get_all.return_value = []
        sample_repo.get_all.return_value = []

        ctrl.run()

        _, sample_dtos = view.show_monitoring.call_args[0]
        assert sample_dtos == []

    def test_order_dto_contains_correct_fields(
        self, ctrl, sample_repo, order_repo, view
    ):
        """OrderDto의 필드가 올바르게 채워진다."""
        orders = [_make_order(id=1, quantity=7, customer="LabX")]
        order_repo.get_all.return_value = orders
        sample = _make_sample(id=1, name="SampleX")
        sample_repo.get_all.return_value = [sample]

        ctrl.run()

        order_dtos, _ = view.show_monitoring.call_args[0]
        assert order_dtos[0].id == 1
        assert order_dtos[0].quantity == 7
        assert order_dtos[0].customer == "LabX"
        assert order_dtos[0].sample_name == "SampleX"
