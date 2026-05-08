# -*- coding: utf-8 -*-
# tests/test_main_controller.py — MainController 단위 테스트
# MagicMock으로 하위 Controller·Repository·View 격리
# 메뉴 라우팅, 잘못된 번호 오류, EXIT 처리 포함
from __future__ import annotations

from unittest.mock import MagicMock, call

import pytest

from controllers.main_controller import MainController, MainMenu
from models.sample import Sample
from views.dto import SampleDto


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_repo():
    return MagicMock()


@pytest.fixture
def view():
    return MagicMock()


@pytest.fixture
def sub_ctrls():
    return {
        "sample": MagicMock(),
        "order": MagicMock(),
        "monitoring": MagicMock(),
        "shipping": MagicMock(),
        "production": MagicMock(),
    }


@pytest.fixture
def ctrl(sample_repo, sub_ctrls, view) -> MainController:
    return MainController(
        sample_repository=sample_repo,
        sample_controller=sub_ctrls["sample"],
        order_controller=sub_ctrls["order"],
        monitoring_controller=sub_ctrls["monitoring"],
        shipping_controller=sub_ctrls["shipping"],
        production_controller=sub_ctrls["production"],
        view=view,
    )


def _make_sample(**kwargs) -> Sample:
    defaults = {
        "id": 1,
        "name": "SampleA",
        "avg_production_time": 30.0,
        "yield_rate": 0.9,
        "stock": 5,
    }
    defaults.update(kwargs)
    return Sample(**defaults)


# ---------------------------------------------------------------------------
# MainMenu Enum 검증
# ---------------------------------------------------------------------------

class TestMainMenuEnum:
    def test_enum_values(self):
        assert MainMenu.SAMPLE_MGMT.value == 1
        assert MainMenu.ORDER.value == 2
        assert MainMenu.MONITORING.value == 3
        assert MainMenu.SHIPPING.value == 4
        assert MainMenu.PRODUCTION.value == 5
        assert MainMenu.EXIT.value == 0


# ---------------------------------------------------------------------------
# 메뉴 라우팅
# ---------------------------------------------------------------------------

class TestMenuRouting:
    def test_exit_stops_loop(self, ctrl, sample_repo, view):
        """0 입력 → 루프 종료."""
        sample_repo.get_all.return_value = []
        view.prompt_menu_choice.return_value = "0"
        ctrl.run()
        view.show_main_menu.assert_called_once()

    def test_sample_mgmt_calls_sample_ctrl_run(
        self, ctrl, sample_repo, sub_ctrls, view
    ):
        """1 → SampleController.run() 호출 후 0으로 종료."""
        sample_repo.get_all.return_value = []
        view.prompt_menu_choice.side_effect = ["1", "0"]
        ctrl.run()
        sub_ctrls["sample"].run.assert_called_once()

    def test_order_calls_order_ctrl_run(
        self, ctrl, sample_repo, sub_ctrls, view
    ):
        """2 → OrderController.run() 호출."""
        sample_repo.get_all.return_value = []
        view.prompt_menu_choice.side_effect = ["2", "0"]
        ctrl.run()
        sub_ctrls["order"].run.assert_called_once()

    def test_monitoring_calls_monitoring_ctrl_run(
        self, ctrl, sample_repo, sub_ctrls, view
    ):
        """3 → MonitoringController.run() 호출."""
        sample_repo.get_all.return_value = []
        view.prompt_menu_choice.side_effect = ["3", "0"]
        ctrl.run()
        sub_ctrls["monitoring"].run.assert_called_once()

    def test_shipping_calls_shipping_ctrl_run(
        self, ctrl, sample_repo, sub_ctrls, view
    ):
        """4 → ShippingController.run() 호출."""
        sample_repo.get_all.return_value = []
        view.prompt_menu_choice.side_effect = ["4", "0"]
        ctrl.run()
        sub_ctrls["shipping"].run.assert_called_once()

    def test_production_calls_production_ctrl_run(
        self, ctrl, sample_repo, sub_ctrls, view
    ):
        """5 → ProductionController.run() 호출."""
        sample_repo.get_all.return_value = []
        view.prompt_menu_choice.side_effect = ["5", "0"]
        ctrl.run()
        sub_ctrls["production"].run.assert_called_once()

    def test_invalid_choice_shows_error_and_continues(
        self, ctrl, sample_repo, view
    ):
        """잘못된 번호 → show_error() 후 메뉴 재표시."""
        sample_repo.get_all.return_value = []
        view.prompt_menu_choice.side_effect = ["9", "0"]
        ctrl.run()
        view.show_error.assert_called_once()
        assert view.show_main_menu.call_count == 2

    def test_non_integer_choice_shows_error(
        self, ctrl, sample_repo, view
    ):
        """문자 입력 → show_error() 후 메뉴 재표시."""
        sample_repo.get_all.return_value = []
        view.prompt_menu_choice.side_effect = ["abc", "0"]
        ctrl.run()
        view.show_error.assert_called_once()

    def test_show_main_menu_called_with_sample_dtos(
        self, ctrl, sample_repo, view
    ):
        """show_main_menu()에 SampleDto 목록이 전달된다."""
        samples = [_make_sample(id=1, name="S1"), _make_sample(id=2, name="S2")]
        sample_repo.get_all.return_value = samples
        view.prompt_menu_choice.return_value = "0"
        ctrl.run()

        args = view.show_main_menu.call_args[0][0]
        assert len(args) == 2
        assert all(isinstance(d, SampleDto) for d in args)
        assert args[0].name == "S1"
        assert args[1].name == "S2"

    def test_show_main_menu_called_with_empty_list_when_no_samples(
        self, ctrl, sample_repo, view
    ):
        """시료 없을 때 빈 리스트 전달."""
        sample_repo.get_all.return_value = []
        view.prompt_menu_choice.return_value = "0"
        ctrl.run()
        view.show_main_menu.assert_called_once_with([])

    def test_exit_shows_message(self, ctrl, sample_repo, view):
        """EXIT 시 show_message() 호출."""
        sample_repo.get_all.return_value = []
        view.prompt_menu_choice.return_value = "0"
        ctrl.run()
        view.show_message.assert_called_once()
        msg = view.show_message.call_args[0][0]
        assert "종료" in msg
