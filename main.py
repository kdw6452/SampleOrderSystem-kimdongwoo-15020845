# -*- coding: utf-8 -*-
# main.py — Composition Root
# 모든 Repository·View·Controller를 생성자 주입으로 조립한다.
from __future__ import annotations

import sys
import io


def main() -> None:
    # Windows 콘솔 UTF-8 출력 설정
    if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

    # 지연 import: 의존성 조립은 실행 시점에만 수행
    from models.sample_repository import JsonSampleRepository
    from models.order_repository import JsonOrderRepository
    from views.console_view import ConsoleView
    from controllers.sample_controller import SampleController
    from controllers.order_controller import OrderController
    from controllers.monitoring_controller import MonitoringController
    from controllers.shipping_controller import ShippingController
    from controllers.production_controller import ProductionController
    from controllers.main_controller import MainController

    # Repository 생성
    sample_repo = JsonSampleRepository(path="data/samples.json")
    order_repo = JsonOrderRepository(path="data/orders.json")

    # View 생성
    view = ConsoleView()

    # 하위 Controller 생성
    sample_ctrl = SampleController(sample_repo, view)
    order_ctrl = OrderController(sample_repo, order_repo, view)
    monitoring_ctrl = MonitoringController(sample_repo, order_repo, view)
    shipping_ctrl = ShippingController(sample_repo, order_repo, view)
    production_ctrl = ProductionController(sample_repo, order_repo, view)

    # 메인 Controller 조립 및 실행
    main_ctrl = MainController(
        sample_repository=sample_repo,
        sample_controller=sample_ctrl,
        order_controller=order_ctrl,
        monitoring_controller=monitoring_ctrl,
        shipping_controller=shipping_ctrl,
        production_controller=production_ctrl,
        view=view,
    )
    main_ctrl.run()


if __name__ == "__main__":
    main()
