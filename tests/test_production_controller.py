# -*- coding: utf-8 -*-
# tests/test_production_controller.py — ProductionController 단위 테스트
# MagicMock으로 SampleRepository·OrderRepository·BaseView 격리
# 생산량 계산 검증, FIFO 순서, guard clause 포함
from __future__ import annotations

import math
from unittest.mock import MagicMock, call

import pytest

from controllers.production_controller import ProductionController
from models.order import Order, OrderStatus
from models.sample import Sample
from views.dto import ProductionJobDto


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
def ctrl(sample_repo, order_repo, view) -> ProductionController:
    return ProductionController(sample_repo, order_repo, view)


def _make_sample(**kwargs) -> Sample:
    defaults = {
        "id": 1,
        "name": "SampleA",
        "avg_production_time": 30.0,
        "yield_rate": 0.9,
        "stock": 0,
    }
    defaults.update(kwargs)
    return Sample(**defaults)


def _make_order(**kwargs) -> Order:
    defaults = {
        "id": 1,
        "sample_id": 1,
        "quantity": 20,
        "customer": "TestCo",
        "status": OrderStatus.PRODUCING,
        "shortfall": 10,
    }
    defaults.update(kwargs)
    return Order(**defaults)


# ---------------------------------------------------------------------------
# _get_producing_sorted (내부 헬퍼: FIFO 정렬)
# ---------------------------------------------------------------------------

class TestGetProducingSorted:
    def test_sorted_by_id_ascending(self, ctrl, order_repo):
        """ID 오름차순 정렬 → FIFO 보장."""
        orders = [
            _make_order(id=3),
            _make_order(id=1),
            _make_order(id=2),
        ]
        order_repo.get_by_status.return_value = orders
        result = ctrl._get_producing_sorted()
        assert [o.id for o in result] == [1, 2, 3]

    def test_empty_returns_empty(self, ctrl, order_repo):
        order_repo.get_by_status.return_value = []
        result = ctrl._get_producing_sorted()
        assert result == []


# ---------------------------------------------------------------------------
# show_status (생산 현황)
# ---------------------------------------------------------------------------

class TestShowStatus:
    def test_show_status_no_producing_shows_message(
        self, ctrl, order_repo, view
    ):
        """PRODUCING 없으면 show_message() (단순 안내)."""
        order_repo.get_by_status.return_value = []
        ctrl.show_status()
        view.show_message.assert_called_once_with("생산 중인 작업이 없습니다")
        view.show_production_status.assert_not_called()

    def test_show_status_calls_show_production_status_with_dto(
        self, ctrl, order_repo, sample_repo, view
    ):
        """PRODUCING 있으면 첫 번째 주문의 ProductionJobDto 전달."""
        order = _make_order(id=1, shortfall=10)
        order_repo.get_by_status.return_value = [order]
        sample = _make_sample(yield_rate=0.9, avg_production_time=30.0)
        sample_repo.get_by_id.return_value = sample

        ctrl.show_status()

        view.show_production_status.assert_called_once()
        dto = view.show_production_status.call_args[0][0]
        assert isinstance(dto, ProductionJobDto)
        assert dto.order_id == 1
        assert dto.shortfall == 10

    def test_show_status_selects_first_by_id(
        self, ctrl, order_repo, sample_repo, view
    ):
        """여러 PRODUCING 중 ID가 가장 작은 것을 선택."""
        orders = [_make_order(id=3, shortfall=5), _make_order(id=1, shortfall=8)]
        order_repo.get_by_status.return_value = orders
        sample_repo.get_by_id.return_value = _make_sample()

        ctrl.show_status()

        dto = view.show_production_status.call_args[0][0]
        assert dto.order_id == 1

    def test_show_status_dto_actual_qty_calculation(
        self, ctrl, order_repo, sample_repo, view
    ):
        """actual_qty = ceil(shortfall / (yield_rate * 0.9)) 검증."""
        # shortfall=10, yield_rate=0.9 → ceil(10/0.81) = ceil(12.35) = 13
        order = _make_order(id=1, shortfall=10)
        order_repo.get_by_status.return_value = [order]
        sample_repo.get_by_id.return_value = _make_sample(yield_rate=0.9)

        ctrl.show_status()

        dto = view.show_production_status.call_args[0][0]
        expected = math.ceil(10 / (0.9 * 0.9))
        assert dto.actual_qty == expected

    def test_show_status_dto_total_time_calculation(
        self, ctrl, order_repo, sample_repo, view
    ):
        """total_time = avg_production_time * actual_qty 검증."""
        order = _make_order(id=1, shortfall=10)
        order_repo.get_by_status.return_value = [order]
        sample = _make_sample(yield_rate=0.9, avg_production_time=30.0)
        sample_repo.get_by_id.return_value = sample

        ctrl.show_status()

        dto = view.show_production_status.call_args[0][0]
        actual_qty = math.ceil(10 / (0.9 * 0.9))
        expected_total = 30.0 * actual_qty
        assert dto.total_time == expected_total


# ---------------------------------------------------------------------------
# show_queue (생산 대기 큐)
# ---------------------------------------------------------------------------

class TestShowQueue:
    def test_show_queue_empty_passes_empty_list(
        self, ctrl, order_repo, view
    ):
        """PRODUCING 없으면 빈 리스트 전달."""
        order_repo.get_by_status.return_value = []
        ctrl.show_queue()
        view.show_production_queue.assert_called_once_with([])

    def test_show_queue_passes_all_in_fifo_order(
        self, ctrl, order_repo, sample_repo, view
    ):
        """모든 PRODUCING 주문을 FIFO 순서로 전달."""
        orders = [
            _make_order(id=3, shortfall=5),
            _make_order(id=1, shortfall=8),
            _make_order(id=2, shortfall=3),
        ]
        order_repo.get_by_status.return_value = orders
        sample_repo.get_by_id.return_value = _make_sample()

        ctrl.show_queue()

        view.show_production_queue.assert_called_once()
        jobs = view.show_production_queue.call_args[0][0]
        assert len(jobs) == 3
        assert [j.order_id for j in jobs] == [1, 2, 3]

    def test_show_queue_dto_fields(
        self, ctrl, order_repo, sample_repo, view
    ):
        """ProductionJobDto 필드 검증."""
        order = _make_order(id=5, quantity=20, shortfall=12, customer="LabA")
        order_repo.get_by_status.return_value = [order]
        sample = _make_sample(name="SampleX", yield_rate=0.8, avg_production_time=45.0)
        sample_repo.get_by_id.return_value = sample

        ctrl.show_queue()

        jobs = view.show_production_queue.call_args[0][0]
        dto = jobs[0]
        assert dto.order_id == 5
        assert dto.sample_name == "SampleX"
        assert dto.customer == "LabA"
        assert dto.quantity == 20
        assert dto.shortfall == 12
        expected_actual = math.ceil(12 / (0.8 * 0.9))
        assert dto.actual_qty == expected_actual
        assert dto.total_time == 45.0 * expected_actual


# ---------------------------------------------------------------------------
# complete (생산 완료 명령)
# ---------------------------------------------------------------------------

class TestComplete:
    def test_complete_no_producing_shows_error(
        self, ctrl, order_repo, view
    ):
        """PRODUCING 없으면 show_error() 후 중단 (guard clause)."""
        order_repo.get_by_status.return_value = []
        ctrl.complete()
        view.show_error.assert_called_once_with("생산 중인 작업이 없습니다")
        order_repo.update_status.assert_not_called()

    def test_complete_updates_status_then_stock(
        self, ctrl, order_repo, sample_repo, view
    ):
        """update_status(CONFIRMED) 먼저 → 성공 후 stock += shortfall."""
        order = _make_order(id=1, shortfall=10)
        order_repo.get_by_status.return_value = [order]
        sample = _make_sample(stock=0)
        sample_repo.get_by_id.return_value = sample

        ctrl.complete()

        order_repo.update_status.assert_called_once_with(1, OrderStatus.CONFIRMED)
        sample_repo.update.assert_called_once()
        updated = sample_repo.update.call_args[0][0]
        assert updated.stock == 10  # 0 + 10

    def test_complete_message_contains_confirmed_and_shortfall(
        self, ctrl, order_repo, sample_repo, view
    ):
        """메시지에 CONFIRMED와 shortfall(재고 증가분) 포함."""
        order = _make_order(id=3, shortfall=15)
        order_repo.get_by_status.return_value = [order]
        sample_repo.get_by_id.return_value = _make_sample(stock=5)

        ctrl.complete()

        msg = view.show_message.call_args[0][0]
        assert "CONFIRMED" in msg
        assert "15" in msg  # shortfall

    def test_complete_selects_first_by_id_fifo(
        self, ctrl, order_repo, sample_repo, view
    ):
        """여러 PRODUCING 중 ID 최소값 주문을 먼저 처리."""
        orders = [
            _make_order(id=5, shortfall=7),
            _make_order(id=2, shortfall=3),
        ]
        order_repo.get_by_status.return_value = orders
        sample_repo.get_by_id.return_value = _make_sample()

        ctrl.complete()

        order_repo.update_status.assert_called_once_with(2, OrderStatus.CONFIRMED)

    def test_complete_update_status_failure_does_not_update_stock(
        self, ctrl, order_repo, sample_repo, view
    ):
        """update_status() 실패 시 재고 변동 없음 (원자성 보장)."""
        order = _make_order(id=1, shortfall=10)
        order_repo.get_by_status.return_value = [order]
        sample_repo.get_by_id.return_value = _make_sample(stock=0)
        order_repo.update_status.side_effect = ValueError("전이 오류")

        ctrl.complete()

        view.show_error.assert_called_once()
        sample_repo.update.assert_not_called()

    def test_complete_order_id_in_message(
        self, ctrl, order_repo, sample_repo, view
    ):
        """메시지에 주문 ID 포함."""
        order = _make_order(id=7, shortfall=5)
        order_repo.get_by_status.return_value = [order]
        sample_repo.get_by_id.return_value = _make_sample()

        ctrl.complete()

        msg = view.show_message.call_args[0][0]
        assert "7" in msg

    def test_complete_shortfall_none_shows_error(
        self, ctrl, order_repo, view
    ):
        """shortfall=None인 경우 방어 코드: show_error() 후 중단."""
        order = _make_order(id=1, shortfall=None)
        order_repo.get_by_status.return_value = [order]

        ctrl.complete()

        view.show_error.assert_called_once()
        order_repo.update_status.assert_not_called()

    def test_complete_sample_not_found_shows_error(
        self, ctrl, order_repo, sample_repo, view
    ):
        """시료를 찾을 수 없으면 show_error() 후 중단."""
        order = _make_order(id=1, shortfall=5)
        order_repo.get_by_status.return_value = [order]
        sample_repo.get_by_id.return_value = None

        ctrl.complete()

        view.show_error.assert_called_once()
        order_repo.update_status.assert_not_called()


# ---------------------------------------------------------------------------
# _build_job_dto 내부 분기 커버
# ---------------------------------------------------------------------------

class TestBuildJobDto:
    def test_build_job_dto_sample_none_returns_none(
        self, ctrl, sample_repo
    ):
        """시료 찾지 못하면 None 반환."""
        sample_repo.get_by_id.return_value = None
        order = _make_order(id=1, shortfall=5)
        result = ctrl._build_job_dto(order)
        assert result is None

    def test_build_job_dto_shortfall_none_returns_none(
        self, ctrl, sample_repo
    ):
        """shortfall=None이면 None 반환."""
        sample_repo.get_by_id.return_value = _make_sample()
        order = _make_order(id=1, shortfall=None)
        result = ctrl._build_job_dto(order)
        assert result is None


# ---------------------------------------------------------------------------
# run() 루프 분기 커버
# ---------------------------------------------------------------------------

class TestRunLoop:
    def test_run_exit(self, ctrl, order_repo, view):
        """0 입력 → 루프 종료."""
        order_repo.get_by_status.return_value = []
        view.prompt_menu_choice.return_value = "0"
        ctrl.run()
        # show_message가 메뉴 출력용으로 호출되고 루프 종료
        assert view.prompt_menu_choice.call_count == 1

    def test_run_invalid_choice_shows_error(self, ctrl, order_repo, view):
        """잘못된 번호 → show_error() 후 재루프."""
        order_repo.get_by_status.return_value = []
        view.prompt_menu_choice.side_effect = ["9", "0"]
        ctrl.run()
        view.show_error.assert_called_once_with("올바른 메뉴 번호를 입력하세요")

    def test_run_show_status_via_menu(self, ctrl, order_repo, view):
        """1 → _show_status() 호출."""
        order_repo.get_by_status.return_value = []
        view.prompt_menu_choice.side_effect = ["1", "0"]
        ctrl.run()
        view.show_message.assert_any_call("생산 중인 작업이 없습니다")

    def test_run_show_queue_via_menu(self, ctrl, order_repo, view):
        """2 → _show_queue() 호출."""
        order_repo.get_by_status.return_value = []
        view.prompt_menu_choice.side_effect = ["2", "0"]
        ctrl.run()
        view.show_production_queue.assert_called_once_with([])

    def test_run_complete_via_menu(self, ctrl, order_repo, view):
        """3 → _complete() 호출 (PRODUCING 없으면 show_error)."""
        order_repo.get_by_status.return_value = []
        view.prompt_menu_choice.side_effect = ["3", "0"]
        ctrl.run()
        view.show_error.assert_called_once_with("생산 중인 작업이 없습니다")
