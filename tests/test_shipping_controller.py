# -*- coding: utf-8 -*-
# tests/test_shipping_controller.py — ShippingController 단위 테스트
# MagicMock으로 SampleRepository·OrderRepository·BaseView 격리
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from controllers.shipping_controller import ShippingController
from models.order import Order, OrderStatus
from models.sample import Sample
from views.dto import OrderDto


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
def ctrl(sample_repo, order_repo, view) -> ShippingController:
    return ShippingController(sample_repo, order_repo, view)


def _make_sample(**kwargs) -> Sample:
    defaults = {
        "id": 1,
        "name": "SampleA",
        "avg_production_time": 30.0,
        "yield_rate": 0.9,
        "stock": 20,
    }
    defaults.update(kwargs)
    return Sample(**defaults)


def _make_order(**kwargs) -> Order:
    defaults = {
        "id": 1,
        "sample_id": 1,
        "quantity": 5,
        "customer": "TestCo",
        "status": OrderStatus.CONFIRMED,
        "shortfall": None,
    }
    defaults.update(kwargs)
    return Order(**defaults)


# ---------------------------------------------------------------------------
# list_confirmed (출고 대기 목록)
# ---------------------------------------------------------------------------

class TestListConfirmed:
    def test_list_confirmed_returns_dtos_with_stock(
        self, ctrl, sample_repo, order_repo, view
    ):
        """CONFIRMED 주문을 stock 포함 OrderDto로 변환 후 show_orders() 전달."""
        orders = [_make_order(id=1, quantity=5)]
        order_repo.get_by_status.return_value = orders
        sample = _make_sample(stock=20)
        sample_repo.get_by_id.return_value = sample

        ctrl.list_confirmed()

        order_repo.get_by_status.assert_called_once_with(OrderStatus.CONFIRMED)
        view.show_orders.assert_called_once()
        dtos = view.show_orders.call_args[0][0]
        assert len(dtos) == 1
        assert isinstance(dtos[0], OrderDto)
        assert dtos[0].stock == 20

    def test_list_confirmed_empty(self, ctrl, sample_repo, order_repo, view):
        """CONFIRMED 없으면 빈 목록 전달."""
        order_repo.get_by_status.return_value = []
        ctrl.list_confirmed()
        view.show_orders.assert_called_once_with([])

    def test_list_confirmed_sample_not_found_stock_is_none(
        self, ctrl, sample_repo, order_repo, view
    ):
        """시료를 찾지 못하면 stock=None."""
        order_repo.get_by_status.return_value = [_make_order(id=1)]
        sample_repo.get_by_id.return_value = None
        ctrl.list_confirmed()
        dtos = view.show_orders.call_args[0][0]
        assert dtos[0].stock is None


# ---------------------------------------------------------------------------
# ship (출고 실행)
# ---------------------------------------------------------------------------

class TestShip:
    def test_ship_success_calls_update_status_then_updates_stock(
        self, ctrl, sample_repo, order_repo, view
    ):
        """정상 출고: update_status(RELEASE) → sample.stock -= quantity → update()."""
        order = _make_order(id=1, quantity=5)
        order_repo.get_by_id.return_value = order
        sample = _make_sample(stock=20)
        sample_repo.get_by_id.return_value = sample
        view.prompt_input.return_value = "1"

        ctrl.ship()

        order_repo.update_status.assert_called_once_with(1, OrderStatus.RELEASE)
        # 재고 차감 확인
        sample_repo.update.assert_called_once()
        updated_sample = sample_repo.update.call_args[0][0]
        assert updated_sample.stock == 15  # 20 - 5

    def test_ship_message_contains_release_and_remaining_stock(
        self, ctrl, sample_repo, order_repo, view
    ):
        """메시지에 RELEASE, 차감 수량, 잔여 재고 포함."""
        order = _make_order(id=2, quantity=3)
        order_repo.get_by_id.return_value = order
        sample = _make_sample(stock=10)
        sample_repo.get_by_id.return_value = sample
        view.prompt_input.return_value = "2"

        ctrl.ship()

        msg = view.show_message.call_args[0][0]
        assert "RELEASE" in msg
        assert "3" in msg   # 차감 수량
        assert "7" in msg   # 잔여 재고 = 10 - 3

    def test_ship_nonexistent_order_shows_error(
        self, ctrl, sample_repo, order_repo, view
    ):
        """존재하지 않는 주문 ID → show_error(), update_status() 없음."""
        order_repo.get_by_id.return_value = None
        view.prompt_input.return_value = "999"
        ctrl.ship()
        view.show_error.assert_called_once()
        order_repo.update_status.assert_not_called()

    def test_ship_non_confirmed_order_shows_error(
        self, ctrl, sample_repo, order_repo, view
    ):
        """CONFIRMED 아닌 주문 → show_error()."""
        order = _make_order(id=1, status=OrderStatus.RESERVED)
        order_repo.get_by_id.return_value = order
        view.prompt_input.return_value = "1"
        ctrl.ship()
        view.show_error.assert_called_once()
        order_repo.update_status.assert_not_called()

    def test_ship_invalid_order_id_shows_error(
        self, ctrl, sample_repo, order_repo, view
    ):
        """주문 ID가 정수 아님 → show_error()."""
        view.prompt_input.return_value = "abc"
        ctrl.ship()
        view.show_error.assert_called_once()

    def test_ship_update_status_failure_does_not_update_stock(
        self, ctrl, sample_repo, order_repo, view
    ):
        """update_status() 실패 시 재고 변동 없음 (원자성 보장)."""
        order = _make_order(id=1, quantity=5)
        order_repo.get_by_id.return_value = order
        sample = _make_sample(stock=20)
        sample_repo.get_by_id.return_value = sample
        view.prompt_input.return_value = "1"
        order_repo.update_status.side_effect = ValueError("전이 오류")

        ctrl.ship()

        view.show_error.assert_called_once()
        sample_repo.update.assert_not_called()

    def test_ship_order_id_2_with_quantity_8(
        self, ctrl, sample_repo, order_repo, view
    ):
        """주문 ID 포함 메시지 검증."""
        order = _make_order(id=4, quantity=8)
        order_repo.get_by_id.return_value = order
        sample = _make_sample(stock=15)
        sample_repo.get_by_id.return_value = sample
        view.prompt_input.return_value = "4"

        ctrl.ship()

        msg = view.show_message.call_args[0][0]
        assert "4" in msg

    def test_ship_sample_not_found_shows_error(
        self, ctrl, sample_repo, order_repo, view
    ):
        """출고 시 시료를 찾을 수 없으면 show_error()."""
        order = _make_order(id=1, quantity=5)
        order_repo.get_by_id.return_value = order
        sample_repo.get_by_id.return_value = None
        view.prompt_input.return_value = "1"

        ctrl.ship()

        view.show_error.assert_called_once()
        order_repo.update_status.assert_not_called()


# ---------------------------------------------------------------------------
# run() 루프 분기 커버
# ---------------------------------------------------------------------------

class TestRunLoop:
    def test_run_exit(self, ctrl, order_repo, view):
        """0 입력 → 루프 종료."""
        order_repo.get_by_status.return_value = []
        view.prompt_menu_choice.return_value = "0"
        ctrl.run()
        assert view.prompt_menu_choice.call_count == 1

    def test_run_list_confirmed_via_menu(self, ctrl, order_repo, view):
        """1 → list_confirmed() 호출."""
        order_repo.get_by_status.return_value = []
        view.prompt_menu_choice.side_effect = ["1", "0"]
        ctrl.run()
        view.show_orders.assert_called_once_with([])

    def test_run_ship_via_menu(self, ctrl, sample_repo, order_repo, view):
        """2 → ship() 호출."""
        order_repo.get_by_id.return_value = None
        view.prompt_menu_choice.side_effect = ["2", "0"]
        view.prompt_input.return_value = "999"
        ctrl.run()
        view.show_error.assert_called_once()

    def test_run_invalid_choice_shows_error(self, ctrl, order_repo, view):
        """잘못된 번호 → show_error()."""
        order_repo.get_by_status.return_value = []
        view.prompt_menu_choice.side_effect = ["7", "0"]
        ctrl.run()
        view.show_error.assert_called_once_with("올바른 메뉴 번호를 입력하세요")
