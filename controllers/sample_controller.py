# -*- coding: utf-8 -*-
# controllers/sample_controller.py — 시료 등록·조회·검색
from __future__ import annotations

from controllers.base_controller import BaseController
from models.sample import Sample
from models.sample_repository import SampleRepository
from views.base_view import BaseView
from views.dto import SampleDto


def _to_dto(sample: Sample) -> SampleDto:
    return SampleDto(
        id=sample.id,
        name=sample.name,
        avg_production_time=sample.avg_production_time,
        yield_rate=sample.yield_rate,
        stock=sample.stock,
    )


class SampleController(BaseController):
    """시료 관련 서브메뉴를 담당하는 Controller.

    의존성: SampleRepository, BaseView
    print()/input() 사용 금지 — View 메서드만 사용
    """

    _MENU = (
        "1. 시료 등록",
        "2. 시료 목록 조회",
        "3. 시료 이름 검색",
        "0. 돌아가기",
    )

    def __init__(
        self,
        sample_repository: SampleRepository,
        view: BaseView,
    ) -> None:
        self._repo = sample_repository
        self._view = view

    # ------------------------------------------------------------------
    # BaseController 구현
    # ------------------------------------------------------------------

    def run(self) -> None:
        """시료 관리 서브메뉴 루프."""
        while True:
            self._view.show_message("=== 시료 관리 ===")
            for item in self._MENU:
                self._view.show_message(item)
            choice = self._view.prompt_menu_choice("메뉴 선택")
            if choice == "1":
                self._register()
            elif choice == "2":
                self._list_all()
            elif choice == "3":
                self._search()
            elif choice == "0":
                break
            else:
                self._view.show_error("올바른 메뉴 번호를 입력하세요")

    # ------------------------------------------------------------------
    # 공개 커맨드 (테스트 및 내부 호출용)
    # ------------------------------------------------------------------

    def register(self) -> None:
        """시료 등록: 입력 검증 → SampleRepository.add()."""
        self._register()

    def list_all(self) -> None:
        """시료 목록 조회: get_all() → SampleDto → show_samples()."""
        self._list_all()

    def search(self) -> None:
        """시료 검색: 이름 부분 일치."""
        self._search()

    # ------------------------------------------------------------------
    # 내부 구현
    # ------------------------------------------------------------------

    def _register(self) -> None:
        name = self._view.prompt_input("시료 이름").strip()
        if not name:
            self._view.show_error("시료 이름은 공백일 수 없습니다")
            return

        if self._repo.get_by_name(name) is not None:
            self._view.show_error(f"이미 등록된 시료 이름입니다: {name}")
            return

        raw_time = self._view.prompt_input("평균 생산시간(분)").strip()
        try:
            avg_production_time = float(raw_time)
        except ValueError:
            self._view.show_error("평균 생산시간은 숫자여야 합니다")
            return
        if avg_production_time <= 0:
            self._view.show_error("평균 생산시간은 0보다 커야 합니다")
            return

        raw_yield = self._view.prompt_input("수율 (0.0 초과 ~ 1.0 이하)").strip()
        try:
            yield_rate = float(raw_yield)
        except ValueError:
            self._view.show_error("수율은 숫자여야 합니다")
            return
        if not (0.0 < yield_rate <= 1.0):
            self._view.show_error("수율은 0.0 초과 1.0 이하여야 합니다")
            return

        sample = Sample(
            id=0,
            name=name,
            avg_production_time=avg_production_time,
            yield_rate=yield_rate,
            stock=0,
        )
        saved = self._repo.add(sample)
        self._view.show_message(f"시료 '{saved.name}' 등록 완료. ID: {saved.id}")

    def _list_all(self) -> None:
        samples = self._repo.get_all()
        dtos = [_to_dto(s) for s in samples]
        self._view.show_samples(dtos)

    def _search(self) -> None:
        keyword = self._view.prompt_input("검색어 (이름 부분 일치)").strip()
        if not keyword:
            self._view.show_error("검색어는 공백일 수 없습니다")
            return
        matched = [s for s in self._repo.get_all() if keyword in s.name]
        if not matched:
            self._view.show_message("검색 결과가 없습니다")
            return
        dtos = [_to_dto(s) for s in matched]
        self._view.show_samples(dtos)
