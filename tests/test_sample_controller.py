# -*- coding: utf-8 -*-
# tests/test_sample_controller.py — SampleController 단위 테스트
# MagicMock으로 SampleRepository·BaseView 격리
from __future__ import annotations

from unittest.mock import MagicMock, call

import pytest

from controllers.sample_controller import SampleController
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
def ctrl(sample_repo, view) -> SampleController:
    return SampleController(sample_repo, view)


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


# ---------------------------------------------------------------------------
# register (시료 등록)
# ---------------------------------------------------------------------------

class TestRegister:
    def test_register_success(self, ctrl, sample_repo, view):
        """정상 입력 → SampleRepository.add() 호출 + show_message()."""
        sample_repo.get_by_name.return_value = None
        saved = _make_sample(id=1, name="NewSample")
        sample_repo.add.return_value = saved

        view.prompt_input.side_effect = ["NewSample", "30.0", "0.9"]

        ctrl.register()

        sample_repo.get_by_name.assert_called_once_with("NewSample")
        sample_repo.add.assert_called_once()
        view.show_message.assert_called_once()
        msg = view.show_message.call_args[0][0]
        assert "NewSample" in msg
        assert "1" in msg

    def test_register_empty_name_shows_error(self, ctrl, sample_repo, view):
        """이름이 공백이면 show_error() 호출, add() 호출 없음."""
        view.prompt_input.side_effect = ["   "]
        ctrl.register()
        view.show_error.assert_called_once()
        sample_repo.add.assert_not_called()

    def test_register_duplicate_name_shows_error(self, ctrl, sample_repo, view):
        """이미 등록된 이름이면 show_error(), add() 호출 없음."""
        sample_repo.get_by_name.return_value = _make_sample(name="Dup")
        view.prompt_input.side_effect = ["Dup"]
        ctrl.register()
        view.show_error.assert_called_once()
        sample_repo.add.assert_not_called()

    def test_register_non_numeric_time_shows_error(self, ctrl, sample_repo, view):
        """생산시간이 숫자 아닌 문자열 → show_error()."""
        sample_repo.get_by_name.return_value = None
        view.prompt_input.side_effect = ["NewSample", "abc"]
        ctrl.register()
        view.show_error.assert_called_once()
        sample_repo.add.assert_not_called()

    def test_register_zero_time_shows_error(self, ctrl, sample_repo, view):
        """생산시간 0 이하 → show_error()."""
        sample_repo.get_by_name.return_value = None
        view.prompt_input.side_effect = ["NewSample", "0"]
        ctrl.register()
        view.show_error.assert_called_once()
        sample_repo.add.assert_not_called()

    def test_register_negative_time_shows_error(self, ctrl, sample_repo, view):
        """생산시간 음수 → show_error()."""
        sample_repo.get_by_name.return_value = None
        view.prompt_input.side_effect = ["NewSample", "-5.0"]
        ctrl.register()
        view.show_error.assert_called_once()
        sample_repo.add.assert_not_called()

    def test_register_zero_yield_shows_error(self, ctrl, sample_repo, view):
        """수율 0.0 → show_error()."""
        sample_repo.get_by_name.return_value = None
        view.prompt_input.side_effect = ["NewSample", "30.0", "0.0"]
        ctrl.register()
        view.show_error.assert_called_once()
        sample_repo.add.assert_not_called()

    def test_register_over_one_yield_shows_error(self, ctrl, sample_repo, view):
        """수율 1.0 초과 → show_error()."""
        sample_repo.get_by_name.return_value = None
        view.prompt_input.side_effect = ["NewSample", "30.0", "1.1"]
        ctrl.register()
        view.show_error.assert_called_once()
        sample_repo.add.assert_not_called()

    def test_register_yield_boundary_1_0_succeeds(self, ctrl, sample_repo, view):
        """수율 1.0 경계값은 허용된다."""
        sample_repo.get_by_name.return_value = None
        saved = _make_sample(name="S", yield_rate=1.0)
        sample_repo.add.return_value = saved
        view.prompt_input.side_effect = ["S", "30.0", "1.0"]
        ctrl.register()
        sample_repo.add.assert_called_once()

    def test_register_non_numeric_yield_shows_error(self, ctrl, sample_repo, view):
        """수율이 숫자 아닌 문자열 → show_error()."""
        sample_repo.get_by_name.return_value = None
        view.prompt_input.side_effect = ["NewSample", "30.0", "xyz"]
        ctrl.register()
        view.show_error.assert_called_once()
        sample_repo.add.assert_not_called()


# ---------------------------------------------------------------------------
# list_all (시료 목록 조회)
# ---------------------------------------------------------------------------

class TestListAll:
    def test_list_all_calls_show_samples_with_dtos(self, ctrl, sample_repo, view):
        """get_all() 결과를 SampleDto로 변환하여 show_samples() 전달."""
        samples = [
            _make_sample(id=1, name="A", stock=10),
            _make_sample(id=2, name="B", stock=5),
        ]
        sample_repo.get_all.return_value = samples
        ctrl.list_all()

        view.show_samples.assert_called_once()
        dtos = view.show_samples.call_args[0][0]
        assert len(dtos) == 2
        assert all(isinstance(d, SampleDto) for d in dtos)
        assert dtos[0].name == "A"
        assert dtos[1].name == "B"

    def test_list_all_empty_calls_show_samples_with_empty_list(
        self, ctrl, sample_repo, view
    ):
        """등록된 시료 없을 때 빈 목록 전달."""
        sample_repo.get_all.return_value = []
        ctrl.list_all()
        view.show_samples.assert_called_once_with([])

    def test_list_all_dto_stock_status_is_empty_by_default(
        self, ctrl, sample_repo, view
    ):
        """MonitoringController가 채우지 않은 stock_status는 기본값 ''."""
        sample_repo.get_all.return_value = [_make_sample(id=1, name="X", stock=3)]
        ctrl.list_all()
        dtos = view.show_samples.call_args[0][0]
        assert dtos[0].stock_status == ""


# ---------------------------------------------------------------------------
# search (시료 검색)
# ---------------------------------------------------------------------------

class TestSearch:
    def test_search_empty_keyword_shows_error(self, ctrl, sample_repo, view):
        """공백 검색어 → show_error(), get_all() 호출 없음."""
        view.prompt_input.return_value = "   "
        ctrl.search()
        view.show_error.assert_called_once()
        sample_repo.get_all.assert_not_called()

    def test_search_partial_match_returns_results(self, ctrl, sample_repo, view):
        """부분 일치 검색 결과를 show_samples()로 전달."""
        samples = [
            _make_sample(id=1, name="AlphaX"),
            _make_sample(id=2, name="BetaY"),
        ]
        sample_repo.get_all.return_value = samples
        view.prompt_input.return_value = "Alpha"
        ctrl.search()

        view.show_samples.assert_called_once()
        dtos = view.show_samples.call_args[0][0]
        assert len(dtos) == 1
        assert dtos[0].name == "AlphaX"

    def test_search_no_match_shows_message(self, ctrl, sample_repo, view):
        """검색 결과 없으면 show_message() 호출."""
        sample_repo.get_all.return_value = [_make_sample(name="Omega")]
        view.prompt_input.return_value = "Zeta"
        ctrl.search()
        view.show_message.assert_called_once()
        view.show_samples.assert_not_called()

    def test_search_multiple_matches(self, ctrl, sample_repo, view):
        """여러 결과 모두 전달."""
        samples = [
            _make_sample(id=1, name="SampleA"),
            _make_sample(id=2, name="SampleB"),
            _make_sample(id=3, name="Other"),
        ]
        sample_repo.get_all.return_value = samples
        view.prompt_input.return_value = "Sample"
        ctrl.search()
        dtos = view.show_samples.call_args[0][0]
        assert len(dtos) == 2


# ---------------------------------------------------------------------------
# run() 루프 분기 커버
# ---------------------------------------------------------------------------

class TestRunLoop:
    def test_run_exit(self, ctrl, sample_repo, view):
        """0 입력 → 루프 종료."""
        sample_repo.get_all.return_value = []
        sample_repo.get_by_name.return_value = None
        view.prompt_menu_choice.return_value = "0"
        ctrl.run()
        assert view.prompt_menu_choice.call_count == 1

    def test_run_register_via_menu(self, ctrl, sample_repo, view):
        """1 → register() 호출."""
        sample_repo.get_by_name.return_value = None
        saved = _make_sample(id=1, name="S")
        sample_repo.add.return_value = saved
        view.prompt_menu_choice.side_effect = ["1", "0"]
        view.prompt_input.side_effect = ["S", "30.0", "0.9"]
        ctrl.run()
        sample_repo.add.assert_called_once()

    def test_run_list_all_via_menu(self, ctrl, sample_repo, view):
        """2 → list_all() 호출."""
        sample_repo.get_all.return_value = []
        view.prompt_menu_choice.side_effect = ["2", "0"]
        ctrl.run()
        view.show_samples.assert_called_once_with([])

    def test_run_search_via_menu(self, ctrl, sample_repo, view):
        """3 → search() 호출."""
        sample_repo.get_all.return_value = []
        view.prompt_menu_choice.side_effect = ["3", "0"]
        view.prompt_input.return_value = "   "
        ctrl.run()
        view.show_error.assert_called_once()

    def test_run_invalid_choice_shows_error(self, ctrl, sample_repo, view):
        """잘못된 번호 → show_error()."""
        sample_repo.get_all.return_value = []
        view.prompt_menu_choice.side_effect = ["9", "0"]
        ctrl.run()
        view.show_error.assert_called_once_with("올바른 메뉴 번호를 입력하세요")
