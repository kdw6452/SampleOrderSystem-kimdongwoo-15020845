# -*- coding: utf-8 -*-
# tests/test_order_controller.py — OrderController 단위 테스트
# MagicMock으로 SampleRepository·OrderRepository·BaseView 격리
# 재고 충분/부족 분기, 상태 검증, 계산 검증 포함
from __future__ import annotations

import math
from unittest.mock import MagicMock

import pytest

from controllers.order_controller import OrderController
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
def ctrl(sample_repo, order_repo, view) -> OrderController:
    return OrderController(sample_repo, order_repo, view)


def _make_sample(**kwargs) -> Sample:
    defaults = {
        "id": 1,
        "name": "SampleA",
        "avg_production_time": 30.0,
        "yield_rate": 0.9,
        "stock": 100,
    }
    defaults.update(kwargs)
    return Sample(**defaults)


def _make_order(**kwargs) -> Order:
    defaults = {
        "id": 1,
        "sample_id": 1,
        "quantity": 10,
        "customer": "TestCo",
        "status": OrderStatus.RESERVED,
        "shortfall": None,
    }
    defaults.update(kwargs)
    return Order(**defaults)


# ---------------------------------------------------------------------------
# receive (주문 접수)
# ---------------------------------------------------------------------------

class TestReceive:
    def test_receive_success(self, ctrl, sample_repo, order_repo, view):
        """정상 입력 → OrderRepository.add() 호출 + RESERVED 메시지."""
        sample_repo.get_by_id.return_value = _make_sample(id=1)
        saved = _make_order(id=5, customer="LabX", quantity=3)
        order_repo.add.return_value = saved
        view.prompt_input.side_effect = ["1", "LabX", "3"]

        ctrl.receive()

        order_repo.add.assert_called_once()
        msg = view.show_message.call_args[0][0]
        assert "5" in msg
        assert "RESERVED" in msg

    def test_receive_nonexistent_sample_id_shows_error(
        self, ctrl, sample_repo, order_repo, view
    ):
        """존재하지 않는 시료 ID → show_error(), add() 없음."""
        sample_repo.get_by_id.return_value = None
        view.prompt_input.side_effect = ["999"]
        ctrl.receive()
        view.show_error.assert_called_once()
        order_repo.add.assert_not_called()

    def test_receive_invalid_sample_id_shows_error(
        self, ctrl, sample_repo, order_repo, view
    ):
        """시료 ID가 정수 아님 → show_error()."""
        view.prompt_input.side_effect = ["abc"]
        ctrl.receive()
        view.show_error.assert_called_once()
        order_repo.add.assert_not_called()

    def test_receive_empty_customer_shows_error(
        self, ctrl, sample_repo, order_repo, view
    ):
        """고객명 공백 → show_error()."""
        sample_repo.get_by_id.return_value = _make_sample()
        view.prompt_input.side_effect = ["1", "  "]
        ctrl.receive()
        view.show_error.assert_called_once()
        order_repo.add.assert_not_called()

    def test_receive_zero_quantity_shows_error(
        self, ctrl, sample_repo, order_repo, view
    ):
        """수량 0 → show_error()."""
        sample_repo.get_by_id.return_value = _make_sample()
        view.prompt_input.side_effect = ["1", "LabX", "0"]
        ctrl.receive()
        view.show_error.assert_called_once()
        order_repo.add.assert_not_called()

    def test_receive_negative_quantity_shows_error(
        self, ctrl, sample_repo, order_repo, view
    ):
        """수량 음수 → show_error()."""
        sample_repo.get_by_id.return_value = _make_sample()
        view.prompt_input.side_effect = ["1", "LabX", "-1"]
        ctrl.receive()
        view.show_error.assert_called_once()
        order_repo.add.assert_not_called()

    def test_receive_non_integer_quantity_shows_error(
        self, ctrl, sample_repo, order_repo, view
    ):
        """수량이 정수 아님 → show_error()."""
        sample_repo.get_by_id.return_value = _make_sample()
        view.prompt_input.side_effect = ["1", "LabX", "abc"]
        ctrl.receive()
        view.show_error.assert_called_once()
        order_repo.add.assert_not_called()


# ---------------------------------------------------------------------------
# list_reserved (접수된 주문 목록)
# ---------------------------------------------------------------------------

class TestListReserved:
    def test_list_reserved_returns_dtos(self, ctrl, sample_repo, order_repo, view):
        """RESERVED 주문을 OrderDto로 변환하여 show_orders() 전달."""
        order_repo.get_by_status.return_value = [
            _make_order(id=1, customer="A"),
            _make_order(id=2, customer="B"),
        ]
        sample_repo.get_by_id.return_value = _make_sample(name="SampleX")

        ctrl.list_reserved()

        view.show_orders.assert_called_once()
        dtos = view.show_orders.call_args[0][0]
        assert len(dtos) == 2
        assert all(isinstance(d, OrderDto) for d in dtos)

    def test_list_reserved_empty(self, ctrl, sample_repo, order_repo, view):
        """RESERVED 없으면 빈 목록 전달."""
        order_repo.get_by_status.return_value = []
        ctrl.list_reserved()
        view.show_orders.assert_called_once_with([])


# ---------------------------------------------------------------------------
# approve (주문 승인) — 재고 충분 분기
# ---------------------------------------------------------------------------

class TestApproveEnoughStock:
    def test_approve_confirmed_when_stock_sufficient(
        self, ctrl, sample_repo, order_repo, view
    ):
        """재고 충분 → update_status(CONFIRMED) 호출."""
        order = _make_order(id=1, quantity=5)
        order_repo.get_by_id.return_value = order
        sample = _make_sample(stock=10)
        sample_repo.get_by_id.return_value = sample
        view.prompt_input.return_value = "1"

        ctrl.approve()

        order_repo.update_status.assert_called_once_with(1, OrderStatus.CONFIRMED)
        msg = view.show_message.call_args[0][0]
        assert "CONFIRMED" in msg

    def test_approve_stock_equals_quantity_is_sufficient(
        self, ctrl, sample_repo, order_repo, view
    ):
        """재고 == 수량 → CONFIRMED."""
        order = _make_order(id=1, quantity=10)
        order_repo.get_by_id.return_value = order
        sample = _make_sample(stock=10)
        sample_repo.get_by_id.return_value = sample
        view.prompt_input.return_value = "1"

        ctrl.approve()

        order_repo.update_status.assert_called_once_with(1, OrderStatus.CONFIRMED)

    def test_approve_confirmed_shows_order_id(
        self, ctrl, sample_repo, order_repo, view
    ):
        """메시지에 주문 ID가 포함된다."""
        order = _make_order(id=7, quantity=3)
        order_repo.get_by_id.return_value = order
        sample_repo.get_by_id.return_value = _make_sample(stock=50)
        view.prompt_input.return_value = "7"

        ctrl.approve()

        msg = view.show_message.call_args[0][0]
        assert "7" in msg


# ---------------------------------------------------------------------------
# approve (주문 승인) — 재고 부족 분기
# ---------------------------------------------------------------------------

class TestApproveInsufficientStock:
    def test_approve_producing_when_stock_insufficient(
        self, ctrl, sample_repo, order_repo, view
    ):
        """재고 부족 → order.shortfall 설정, update() 호출, update_status(PRODUCING)."""
        order = _make_order(id=1, quantity=15)
        order_repo.get_by_id.return_value = order
        sample = _make_sample(stock=5, yield_rate=0.9)
        sample_repo.get_by_id.return_value = sample
        view.prompt_input.return_value = "1"

        ctrl.approve()

        order_repo.update.assert_called_once()
        updated_order = order_repo.update.call_args[0][0]
        assert updated_order.shortfall == 10  # 15 - 5

        order_repo.update_status.assert_called_once_with(1, OrderStatus.PRODUCING)

    def test_approve_producing_message_includes_shortfall_and_actual_qty(
        self, ctrl, sample_repo, order_repo, view
    ):
        """PRODUCING 메시지에 부족분과 실생산량 포함."""
        order = _make_order(id=2, quantity=20)
        order_repo.get_by_id.return_value = order
        # stock=10, shortfall=10, yield_rate=0.9
        # actual_qty = ceil(10 / (0.9 * 0.9)) = ceil(10 / 0.81) = ceil(12.34) = 13
        sample = _make_sample(stock=10, yield_rate=0.9)
        sample_repo.get_by_id.return_value = sample
        view.prompt_input.return_value = "2"

        ctrl.approve()

        msg = view.show_message.call_args[0][0]
        assert "PRODUCING" in msg
        assert "10" in msg   # 부족분
        assert "13" in msg   # 실생산량 ceil(10/0.81) = 13

    def test_approve_shortfall_max_zero(self, ctrl, sample_repo, order_repo, view):
        """shortfall = max(0, quantity - stock). stock > quantity여도 부족분 0 미만 없음."""
        # stock=3, quantity=10 → shortfall=7
        order = _make_order(id=1, quantity=10)
        order_repo.get_by_id.return_value = order
        sample = _make_sample(stock=3, yield_rate=0.8)
        sample_repo.get_by_id.return_value = sample
        view.prompt_input.return_value = "1"

        ctrl.approve()

        updated_order = order_repo.update.call_args[0][0]
        assert updated_order.shortfall == 7
        assert updated_order.shortfall >= 0

    def test_approve_actual_qty_calculation(self, ctrl, sample_repo, order_repo, view):
        """실생산량 계산 검증: ceil(shortfall / (yield_rate * 0.9))."""
        # shortfall=100, yield_rate=0.8
        # actual_qty = ceil(100 / 0.72) = ceil(138.88) = 139
        order = _make_order(id=1, quantity=100)
        order_repo.get_by_id.return_value = order
        sample = _make_sample(stock=0, yield_rate=0.8)
        sample_repo.get_by_id.return_value = sample
        view.prompt_input.return_value = "1"

        ctrl.approve()

        msg = view.show_message.call_args[0][0]
        expected = math.ceil(100 / (0.8 * 0.9))  # 139
        assert str(expected) in msg


# ---------------------------------------------------------------------------
# approve — 오류 케이스
# ---------------------------------------------------------------------------

class TestApproveErrors:
    def test_approve_nonexistent_order_shows_error(
        self, ctrl, sample_repo, order_repo, view
    ):
        """존재하지 않는 주문 ID → show_error()."""
        order_repo.get_by_id.return_value = None
        view.prompt_input.return_value = "999"
        ctrl.approve()
        view.show_error.assert_called_once()

    def test_approve_non_reserved_order_shows_error(
        self, ctrl, sample_repo, order_repo, view
    ):
        """RESERVED 아닌 주문 → show_error()."""
        order = _make_order(id=1, status=OrderStatus.CONFIRMED)
        order_repo.get_by_id.return_value = order
        view.prompt_input.return_value = "1"
        ctrl.approve()
        view.show_error.assert_called_once()

    def test_approve_invalid_order_id_shows_error(
        self, ctrl, sample_repo, order_repo, view
    ):
        """주문 ID가 정수 아님 → show_error()."""
        view.prompt_input.return_value = "abc"
        ctrl.approve()
        view.show_error.assert_called_once()

    def test_approve_update_status_raises_shows_error(
        self, ctrl, sample_repo, order_repo, view
    ):
        """update_status()가 ValueError 발생 시 show_error()."""
        order = _make_order(id=1, quantity=5)
        order_repo.get_by_id.return_value = order
        sample_repo.get_by_id.return_value = _make_sample(stock=10)
        view.prompt_input.return_value = "1"
        order_repo.update_status.side_effect = ValueError("전이 오류")

        ctrl.approve()

        view.show_error.assert_called_once()

    def test_approve_sample_not_found_shows_error(
        self, ctrl, sample_repo, order_repo, view
    ):
        """승인 시 시료를 찾을 수 없으면 show_error()."""
        order = _make_order(id=1, quantity=5)
        order_repo.get_by_id.return_value = order
        sample_repo.get_by_id.return_value = None
        view.prompt_input.return_value = "1"

        ctrl.approve()

        view.show_error.assert_called_once()
        order_repo.update_status.assert_not_called()


# ---------------------------------------------------------------------------
# reject (주문 거절)
# ---------------------------------------------------------------------------

class TestReject:
    def test_reject_success(self, ctrl, sample_repo, order_repo, view):
        """RESERVED 주문 거절 → update_status(REJECTED) + show_message()."""
        order = _make_order(id=3)
        order_repo.get_by_id.return_value = order
        view.prompt_input.return_value = "3"

        ctrl.reject()

        order_repo.update_status.assert_called_once_with(3, OrderStatus.REJECTED)
        msg = view.show_message.call_args[0][0]
        assert "REJECTED" in msg
        assert "3" in msg

    def test_reject_nonexistent_order_shows_error(
        self, ctrl, sample_repo, order_repo, view
    ):
        """존재하지 않는 주문 ID → show_error()."""
        order_repo.get_by_id.return_value = None
        view.prompt_input.return_value = "999"
        ctrl.reject()
        view.show_error.assert_called_once()
        order_repo.update_status.assert_not_called()

    def test_reject_non_reserved_shows_error(
        self, ctrl, sample_repo, order_repo, view
    ):
        """RESERVED 아닌 주문 거절 시도 → show_error()."""
        order = _make_order(id=1, status=OrderStatus.PRODUCING)
        order_repo.get_by_id.return_value = order
        view.prompt_input.return_value = "1"
        ctrl.reject()
        view.show_error.assert_called_once()
        order_repo.update_status.assert_not_called()

    def test_reject_invalid_id_shows_error(
        self, ctrl, sample_repo, order_repo, view
    ):
        """주문 ID가 정수 아님 → show_error()."""
        view.prompt_input.return_value = "xyz"
        ctrl.reject()
        view.show_error.assert_called_once()
        order_repo.update_status.assert_not_called()

    def test_reject_update_status_raises_shows_error(
        self, ctrl, sample_repo, order_repo, view
    ):
        """update_status() ValueError → show_error()."""
        order = _make_order(id=1)
        order_repo.get_by_id.return_value = order
        view.prompt_input.return_value = "1"
        order_repo.update_status.side_effect = ValueError("오류")
        ctrl.reject()
        view.show_error.assert_called_once()


# ---------------------------------------------------------------------------
# approve — PRODUCING시 update() 실패 케이스
# ---------------------------------------------------------------------------

class TestApproveProducingErrors:
    def test_approve_producing_update_raises_shows_error(
        self, ctrl, sample_repo, order_repo, view
    ):
        """재고 부족 시 update() ValueError → show_error()."""
        order = _make_order(id=1, quantity=20)
        order_repo.get_by_id.return_value = order
        sample = _make_sample(stock=5, yield_rate=0.9)
        sample_repo.get_by_id.return_value = sample
        view.prompt_input.return_value = "1"
        order_repo.update.side_effect = ValueError("업데이트 오류")

        ctrl.approve()

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

    def test_run_receive_via_menu(self, ctrl, sample_repo, order_repo, view):
        """1 → receive() 호출."""
        sample_repo.get_by_id.return_value = None
        view.prompt_menu_choice.side_effect = ["1", "0"]
        view.prompt_input.return_value = "999"
        ctrl.run()
        view.show_error.assert_called_once()

    def test_run_list_reserved_via_menu(self, ctrl, order_repo, view):
        """2 → list_reserved() 호출."""
        order_repo.get_by_status.return_value = []
        view.prompt_menu_choice.side_effect = ["2", "0"]
        ctrl.run()
        view.show_orders.assert_called_once_with([])

    def test_run_approve_via_menu(self, ctrl, order_repo, view):
        """3 → approve() 호출."""
        order_repo.get_by_id.return_value = None
        view.prompt_menu_choice.side_effect = ["3", "0"]
        view.prompt_input.return_value = "999"
        ctrl.run()
        view.show_error.assert_called_once()

    def test_run_reject_via_menu(self, ctrl, order_repo, view):
        """4 → reject() 호출."""
        order_repo.get_by_id.return_value = None
        view.prompt_menu_choice.side_effect = ["4", "0"]
        view.prompt_input.return_value = "999"
        ctrl.run()
        view.show_error.assert_called_once()

    def test_run_invalid_choice_shows_error(self, ctrl, order_repo, view):
        """잘못된 번호 → show_error()."""
        order_repo.get_by_status.return_value = []
        view.prompt_menu_choice.side_effect = ["8", "0"]
        ctrl.run()
        view.show_error.assert_called_once_with("올바른 메뉴 번호를 입력하세요")
