# -*- coding: utf-8 -*-
# controllers/main_controller.py — 메인 이벤트 루프, MainMenu Enum 분기
from __future__ import annotations

import enum

from controllers.base_controller import BaseController
from controllers.monitoring_controller import MonitoringController
from controllers.order_controller import OrderController
from controllers.production_controller import ProductionController
from controllers.sample_controller import SampleController
from controllers.shipping_controller import ShippingController
from models.sample import Sample
from models.sample_repository import SampleRepository
from views.base_view import BaseView
from views.dto import SampleDto


class MainMenu(enum.Enum):
    """메인 메뉴 상수."""

    SAMPLE_MGMT = 1
    ORDER = 2
    MONITORING = 3
    SHIPPING = 4
    PRODUCTION = 5
    EXIT = 0


def _sample_to_dto(sample: Sample) -> SampleDto:
    return SampleDto(
        id=sample.id,
        name=sample.name,
        avg_production_time=sample.avg_production_time,
        yield_rate=sample.yield_rate,
        stock=sample.stock,
    )


class MainController(BaseController):
    """메인 이벤트 루프를 담당하는 Controller.

    하위 컨트롤러 5개를 주입받아 메뉴 번호에 따라 분기한다.
    잘못된 번호 입력 시 show_error() 후 메뉴를 재표시한다.
    """

    def __init__(
        self,
        sample_repository: SampleRepository,
        sample_controller: SampleController,
        order_controller: OrderController,
        monitoring_controller: MonitoringController,
        shipping_controller: ShippingController,
        production_controller: ProductionController,
        view: BaseView,
    ) -> None:
        self._sample_repo = sample_repository
        self._sample_ctrl = sample_controller
        self._order_ctrl = order_controller
        self._monitoring_ctrl = monitoring_controller
        self._shipping_ctrl = shipping_controller
        self._production_ctrl = production_controller
        self._view = view

    # ------------------------------------------------------------------
    # BaseController 구현
    # ------------------------------------------------------------------

    def run(self) -> None:
        """메인 이벤트 루프."""
        while True:
            samples = self._sample_repo.get_all()
            sample_dtos = [_sample_to_dto(s) for s in samples]
            self._view.show_main_menu(sample_dtos)

            raw = self._view.prompt_menu_choice("메뉴 선택")
            try:
                choice_int = int(raw)
                menu = MainMenu(choice_int)
            except (ValueError, KeyError):
                self._view.show_error(f"올바른 메뉴 번호를 입력하세요: {raw}")
                continue

            if menu == MainMenu.EXIT:
                self._view.show_message("시스템을 종료합니다")
                break
            elif menu == MainMenu.SAMPLE_MGMT:
                self._sample_ctrl.run()
            elif menu == MainMenu.ORDER:
                self._order_ctrl.run()
            elif menu == MainMenu.MONITORING:
                self._monitoring_ctrl.run()
            elif menu == MainMenu.SHIPPING:
                self._shipping_ctrl.run()
            elif menu == MainMenu.PRODUCTION:
                self._production_ctrl.run()
