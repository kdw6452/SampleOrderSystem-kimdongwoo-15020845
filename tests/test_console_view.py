# -*- coding: utf-8 -*-
# tests/test_console_view.py — ConsoleView smoke test
#
# 전략:
# - ConsoleView가 올바른 타입의 인자를 받아 예외 없이 실행되는지 확인한다.
# - capsys(pytest)로 출력 내용의 핵심 키워드를 검증한다.
# - show_monitoring()은 rich.console.Console을 사용하므로 별도 처리 없이
#   예외 발생 여부만 확인한다 (rich가 force_terminal=False 환경에서 텍스트 출력).
from __future__ import annotations

import pytest

from views.console_view import ConsoleView
from views.dto import OrderDto, ProductionJobDto, SampleDto


@pytest.fixture()
def view() -> ConsoleView:
    return ConsoleView()


# ─────────────────────────────────────────────
# SampleDto / OrderDto / ProductionJobDto 픽스처
# ─────────────────────────────────────────────

@pytest.fixture()
def sample_dto() -> SampleDto:
    return SampleDto(
        id=1,
        name="AlphaChip",
        avg_production_time=30.0,
        yield_rate=0.9,
        stock=100,
        stock_status="여유",
    )


@pytest.fixture()
def sample_dto_no_status() -> SampleDto:
    return SampleDto(
        id=2,
        name="BetaChip",
        avg_production_time=45.0,
        yield_rate=0.85,
        stock=0,
        stock_status="",  # 미표시
    )


@pytest.fixture()
def order_dto() -> OrderDto:
    return OrderDto(
        id=10,
        sample_name="AlphaChip",
        quantity=50,
        customer="서울대학교",
        status="RESERVED",
        stock=None,
    )


@pytest.fixture()
def order_dto_with_stock() -> OrderDto:
    return OrderDto(
        id=11,
        sample_name="AlphaChip",
        quantity=20,
        customer="KAIST",
        status="CONFIRMED",
        stock=80,
    )


@pytest.fixture()
def production_job_dto() -> ProductionJobDto:
    return ProductionJobDto(
        order_id=10,
        sample_name="AlphaChip",
        customer="서울대학교",
        quantity=50,
        shortfall=30,
        actual_qty=38,
        total_time=1140.0,
    )


# ─────────────────────────────────────────────
# show_main_menu
# ─────────────────────────────────────────────

class TestShowMainMenu:
    def test_with_samples(self, view: ConsoleView, sample_dto: SampleDto, capsys: pytest.CaptureFixture[str]) -> None:
        """시료가 있을 때 시료 현황과 메뉴 목록이 출력된다."""
        view.show_main_menu([sample_dto])
        captured = capsys.readouterr()
        assert "AlphaChip" in captured.out
        assert "1. 시료관리" in captured.out
        assert "0. 종료" in captured.out

    def test_with_empty_samples(self, view: ConsoleView, capsys: pytest.CaptureFixture[str]) -> None:
        """시료가 없을 때 '등록된 시료가 없습니다' 출력 후 메뉴 목록 표시."""
        view.show_main_menu([])
        captured = capsys.readouterr()
        assert "등록된 시료가 없습니다" in captured.out
        assert "1. 시료관리" in captured.out

    def test_menu_items_present(self, view: ConsoleView, capsys: pytest.CaptureFixture[str]) -> None:
        """모든 메뉴 항목(0~5)이 표시된다."""
        view.show_main_menu([])
        captured = capsys.readouterr()
        for num in ("0", "1", "2", "3", "4", "5"):
            assert num in captured.out


# ─────────────────────────────────────────────
# show_samples
# ─────────────────────────────────────────────

class TestShowSamples:
    def test_with_samples(self, view: ConsoleView, sample_dto: SampleDto, capsys: pytest.CaptureFixture[str]) -> None:
        """시료 목록이 정상 출력된다."""
        view.show_samples([sample_dto])
        captured = capsys.readouterr()
        assert "AlphaChip" in captured.out
        assert "여유" in captured.out  # stock_status 표시

    def test_with_empty_list(self, view: ConsoleView, capsys: pytest.CaptureFixture[str]) -> None:
        """빈 목록이면 '등록된 시료가 없습니다' 출력."""
        view.show_samples([])
        captured = capsys.readouterr()
        assert "등록된 시료가 없습니다" in captured.out

    def test_stock_status_empty_string_not_shown_as_column(
        self,
        view: ConsoleView,
        sample_dto_no_status: SampleDto,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """stock_status가 ""인 시료만 있으면 재고상태 열이 헤더에 없다."""
        view.show_samples([sample_dto_no_status])
        captured = capsys.readouterr()
        assert "재고상태" not in captured.out

    def test_stock_status_shown_when_present(
        self,
        view: ConsoleView,
        sample_dto: SampleDto,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """stock_status가 있는 시료가 하나라도 있으면 재고상태 열이 표시된다."""
        view.show_samples([sample_dto])
        captured = capsys.readouterr()
        assert "재고상태" in captured.out


# ─────────────────────────────────────────────
# show_orders
# ─────────────────────────────────────────────

class TestShowOrders:
    def test_with_orders(
        self,
        view: ConsoleView,
        order_dto: OrderDto,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """주문 목록이 정상 출력된다."""
        view.show_orders([order_dto])
        captured = capsys.readouterr()
        assert "서울대학교" in captured.out
        assert "RESERVED" in captured.out

    def test_with_empty_list(self, view: ConsoleView, capsys: pytest.CaptureFixture[str]) -> None:
        """빈 목록이면 '주문이 없습니다' 출력."""
        view.show_orders([])
        captured = capsys.readouterr()
        assert "주문이 없습니다" in captured.out

    def test_stock_none_not_shown(
        self,
        view: ConsoleView,
        order_dto: OrderDto,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """stock=None인 주문은 재고 열 없이 출력된다."""
        view.show_orders([order_dto])
        captured = capsys.readouterr()
        assert "현재재고" not in captured.out

    def test_stock_shown_when_present(
        self,
        view: ConsoleView,
        order_dto_with_stock: OrderDto,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """stock이 있는 주문에는 현재재고 열이 표시된다."""
        view.show_orders([order_dto_with_stock])
        captured = capsys.readouterr()
        assert "현재재고" in captured.out
        assert "80" in captured.out


# ─────────────────────────────────────────────
# show_monitoring
# ─────────────────────────────────────────────

class TestShowMonitoring:
    def test_no_exception_with_full_data(
        self,
        view: ConsoleView,
        order_dto: OrderDto,
        sample_dto: SampleDto,
    ) -> None:
        """정상 데이터로 예외 없이 실행된다."""
        view.show_monitoring([order_dto], [sample_dto])

    def test_no_exception_with_empty_data(self, view: ConsoleView) -> None:
        """빈 데이터로 예외 없이 실행된다."""
        view.show_monitoring([], [])

    def test_no_exception_with_multiple_statuses(self, view: ConsoleView) -> None:
        """여러 상태의 주문이 있을 때 예외 없이 실행된다."""
        orders = [
            OrderDto(id=1, sample_name="A", quantity=10, customer="고객1", status="RESERVED"),
            OrderDto(id=2, sample_name="A", quantity=5, customer="고객2", status="PRODUCING"),
            OrderDto(id=3, sample_name="B", quantity=20, customer="고객3", status="CONFIRMED"),
            OrderDto(id=4, sample_name="B", quantity=15, customer="고객4", status="RELEASE"),
        ]
        samples = [
            SampleDto(id=1, name="A", avg_production_time=30.0, yield_rate=0.9, stock=10, stock_status="부족"),
            SampleDto(id=2, name="B", avg_production_time=20.0, yield_rate=0.8, stock=0, stock_status="고갈"),
        ]
        view.show_monitoring(orders, samples)

    def test_rejected_status_not_in_standard_groups(self, view: ConsoleView) -> None:
        """REJECTED 상태 주문은 show_monitoring 내부 그룹에 포함되지 않아 예외 없이 실행된다."""
        orders = [
            OrderDto(id=99, sample_name="X", quantity=1, customer="고객X", status="REJECTED"),
        ]
        # REJECTED는 order_map 키에 없으므로 그냥 무시되어야 한다
        view.show_monitoring(orders, [])


# ─────────────────────────────────────────────
# show_production_status
# ─────────────────────────────────────────────

class TestShowProductionStatus:
    def test_with_job(
        self,
        view: ConsoleView,
        production_job_dto: ProductionJobDto,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """생산 작업 정보가 shortfall 포함 출력된다."""
        view.show_production_status(production_job_dto)
        captured = capsys.readouterr()
        assert "AlphaChip" in captured.out
        assert "서울대학교" in captured.out
        assert "30" in captured.out   # shortfall
        assert "38" in captured.out   # actual_qty
        assert "1140" in captured.out  # total_time

    def test_with_none(self, view: ConsoleView, capsys: pytest.CaptureFixture[str]) -> None:
        """job=None이면 '생산 중인 작업이 없습니다' 출력."""
        view.show_production_status(None)
        captured = capsys.readouterr()
        assert "생산 중인 작업이 없습니다" in captured.out

    def test_shortfall_label_present(
        self,
        view: ConsoleView,
        production_job_dto: ProductionJobDto,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """'부족분' 레이블이 출력에 포함된다."""
        view.show_production_status(production_job_dto)
        captured = capsys.readouterr()
        assert "부족분" in captured.out


# ─────────────────────────────────────────────
# show_production_queue
# ─────────────────────────────────────────────

class TestShowProductionQueue:
    def test_with_jobs(
        self,
        view: ConsoleView,
        production_job_dto: ProductionJobDto,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """생산 대기 큐가 1-based 순번과 함께 출력된다."""
        job2 = ProductionJobDto(
            order_id=11,
            sample_name="BetaChip",
            customer="KAIST",
            quantity=20,
            shortfall=20,
            actual_qty=25,
            total_time=500.0,
        )
        view.show_production_queue([production_job_dto, job2])
        captured = capsys.readouterr()
        # 1-based 순번
        assert "1" in captured.out
        assert "2" in captured.out
        assert "AlphaChip" in captured.out
        assert "BetaChip" in captured.out

    def test_shortfall_not_in_output(
        self,
        view: ConsoleView,
        production_job_dto: ProductionJobDto,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """대기 큐 출력에는 '부족분' 레이블이 없다."""
        view.show_production_queue([production_job_dto])
        captured = capsys.readouterr()
        assert "부족분" not in captured.out

    def test_with_empty_list(self, view: ConsoleView, capsys: pytest.CaptureFixture[str]) -> None:
        """빈 목록이면 '대기 중인 생산 작업이 없습니다' 출력."""
        view.show_production_queue([])
        captured = capsys.readouterr()
        assert "대기 중인 생산 작업이 없습니다" in captured.out


# ─────────────────────────────────────────────
# show_message / show_error
# ─────────────────────────────────────────────

class TestShowMessageAndError:
    def test_show_message(self, view: ConsoleView, capsys: pytest.CaptureFixture[str]) -> None:
        """show_message가 메시지 내용을 출력한다."""
        view.show_message("주문 #5가 RESERVED 상태로 접수되었습니다.")
        captured = capsys.readouterr()
        assert "주문 #5가 RESERVED 상태로 접수되었습니다." in captured.out

    def test_show_error(self, view: ConsoleView, capsys: pytest.CaptureFixture[str]) -> None:
        """show_error가 오류 메시지를 출력한다."""
        view.show_error("존재하지 않는 시료 ID입니다.")
        captured = capsys.readouterr()
        assert "존재하지 않는 시료 ID입니다." in captured.out

    def test_show_message_prefix(self, view: ConsoleView, capsys: pytest.CaptureFixture[str]) -> None:
        """show_message 출력에 [알림] 접두어가 포함된다."""
        view.show_message("테스트 메시지")
        captured = capsys.readouterr()
        assert "[알림]" in captured.out

    def test_show_error_prefix(self, view: ConsoleView, capsys: pytest.CaptureFixture[str]) -> None:
        """show_error 출력에 [오류] 접두어가 포함된다."""
        view.show_error("입력값 오류")
        captured = capsys.readouterr()
        assert "[오류]" in captured.out


# ─────────────────────────────────────────────
# prompt_input / prompt_menu_choice
# ─────────────────────────────────────────────

class TestPromptMethods:
    def test_prompt_input_returns_str(self, view: ConsoleView, monkeypatch: pytest.MonkeyPatch) -> None:
        """prompt_input이 사용자 입력을 str로 반환한다."""
        monkeypatch.setattr("builtins.input", lambda _: "AlphaChip")
        result = view.prompt_input("시료명 입력")
        assert result == "AlphaChip"
        assert isinstance(result, str)

    def test_prompt_menu_choice_returns_str(self, view: ConsoleView, monkeypatch: pytest.MonkeyPatch) -> None:
        """prompt_menu_choice가 메뉴 번호를 str로 반환한다."""
        monkeypatch.setattr("builtins.input", lambda _: "3")
        result = view.prompt_menu_choice("메뉴 선택")
        assert result == "3"
        assert isinstance(result, str)

    def test_prompt_input_no_type_conversion(self, view: ConsoleView, monkeypatch: pytest.MonkeyPatch) -> None:
        """prompt_input은 숫자처럼 보이는 입력도 str로 반환한다 (타입 변환 없음)."""
        monkeypatch.setattr("builtins.input", lambda _: "42")
        result = view.prompt_input("수량 입력")
        assert result == "42"
        assert type(result) is str

    def test_prompt_menu_choice_no_type_conversion(self, view: ConsoleView, monkeypatch: pytest.MonkeyPatch) -> None:
        """prompt_menu_choice는 숫자처럼 보이는 입력도 str로 반환한다 (타입 변환 없음)."""
        monkeypatch.setattr("builtins.input", lambda _: "1")
        result = view.prompt_menu_choice("메뉴 선택")
        assert result == "1"
        assert type(result) is str


# ─────────────────────────────────────────────
# BaseView ABC 계약 확인
# ─────────────────────────────────────────────

class TestBaseViewContract:
    def test_console_view_is_instance_of_base_view(self, view: ConsoleView) -> None:
        """ConsoleView는 BaseView의 구현체여야 한다."""
        from views.base_view import BaseView
        assert isinstance(view, BaseView)

    def test_all_abstract_methods_implemented(self) -> None:
        """ConsoleView가 모든 추상 메서드를 구현하여 인스턴스화가 가능하다."""
        # 인스턴스 생성 자체가 성공하면 모든 추상 메서드 구현 확인
        cv = ConsoleView()
        assert cv is not None
