# -*- coding: utf-8 -*-
# views/console_view.py — ConsoleView 구현체
# print() / input() 독점 사용.
# rich import는 show_monitoring() 내부로만 한정한다.
# View는 str만 반환하며, 타입 변환을 수행하지 않는다.
from __future__ import annotations

from views.base_view import BaseView
from views.dto import OrderDto, ProductionJobDto, SampleDto

# 메인 메뉴 항목 정의 (번호: 설명)
_MAIN_MENU_ITEMS: list[tuple[str, str]] = [
    ("1", "시료관리"),
    ("2", "주문"),
    ("3", "모니터링"),
    ("4", "출고처리"),
    ("5", "생산라인"),
    ("0", "종료"),
]

# 모니터링에서 표시할 상태 순서 (REJECTED 제외)
_MONITORING_STATUS_ORDER: list[str] = [
    "RESERVED",
    "PRODUCING",
    "CONFIRMED",
    "RELEASE",
]


class ConsoleView(BaseView):
    """표준 콘솔 I/O 구현체.

    모든 print()/input() 호출은 이 클래스에서만 이루어진다.
    비즈니스 로직 없음 — 받은 데이터를 화면에 표시할 뿐이다.
    """

    # ------------------------------------------------------------------
    # 메인 메뉴
    # ------------------------------------------------------------------

    def show_main_menu(self, samples: list[SampleDto]) -> None:
        """시료 요약 정보와 메인 메뉴 번호 목록을 표시한다."""
        print("\n==============================")
        print("  S-Semi 시료 생산 주문 관리 시스템")
        print("==============================")

        # 시료 요약
        print("\n[시료 현황]")
        if not samples:
            print("  등록된 시료가 없습니다")
        else:
            print(f"  {'ID':<5} {'시료명':<20} {'재고':>6}")
            print("  " + "-" * 33)
            for s in samples:
                print(f"  {s.id:<5} {s.name:<20} {s.stock:>6}")

        # 메뉴 목록
        print("\n[메뉴]")
        for num, label in _MAIN_MENU_ITEMS:
            print(f"  {num}. {label}")
        print()

    # ------------------------------------------------------------------
    # 시료
    # ------------------------------------------------------------------

    def show_samples(self, samples: list[SampleDto]) -> None:
        """전체 시료 목록을 표시한다."""
        if not samples:
            print("등록된 시료가 없습니다")
            return

        print(f"\n{'ID':<5} {'시료명':<20} {'평균생산시간(분)':>15} {'수율':>8} {'재고':>6}", end="")
        # stock_status 열은 첫 번째 항목에 값이 있을 때만 헤더 추가
        has_stock_status = any(s.stock_status for s in samples)
        if has_stock_status:
            print(f" {'재고상태':>8}", end="")
        print()
        print("-" * (5 + 1 + 20 + 1 + 15 + 1 + 8 + 1 + 6 + (1 + 8 if has_stock_status else 0)))

        for s in samples:
            print(f"{s.id:<5} {s.name:<20} {s.avg_production_time:>15.1f} {s.yield_rate:>8.2f} {s.stock:>6}", end="")
            if has_stock_status:
                print(f" {s.stock_status:>8}", end="")
            print()

    # ------------------------------------------------------------------
    # 주문
    # ------------------------------------------------------------------

    def show_orders(self, orders: list[OrderDto]) -> None:
        """주문 목록을 표시한다."""
        if not orders:
            print("주문이 없습니다")
            return

        has_stock = any(o.stock is not None for o in orders)
        header = f"{'주문ID':<8} {'시료명':<20} {'고객명':<20} {'수량':>6} {'상태':<12}"
        if has_stock:
            header += f" {'현재재고':>8}"
        print(f"\n{header}")
        print("-" * (8 + 1 + 20 + 1 + 20 + 1 + 6 + 1 + 12 + (1 + 8 if has_stock else 0)))

        for o in orders:
            line = f"{o.id:<8} {o.sample_name:<20} {o.customer:<20} {o.quantity:>6} {o.status:<12}"
            if has_stock and o.stock is not None:
                line += f" {o.stock:>8}"
            print(line)

    # ------------------------------------------------------------------
    # 모니터링 (Rich Table 필수)
    # ------------------------------------------------------------------

    def show_monitoring(
        self,
        orders: list[OrderDto],
        samples: list[SampleDto],
    ) -> None:
        """모니터링 화면을 Rich Table로 표시한다.

        rich import는 이 메서드 내부로만 한정한다.
        - 주문량 Table: RESERVED/PRODUCING/CONFIRMED/RELEASE 순 그룹
        - 재고량 Table: 시료명·재고·재고상태
        """
        from rich.console import Console
        from rich.table import Table

        console = Console()

        # ── 주문량 Table ──────────────────────────────────────────────
        order_table = Table(title="주문 현황 (REJECTED 제외)", show_header=True, header_style="bold cyan")
        order_table.add_column("주문ID", justify="right", style="dim")
        order_table.add_column("시료명")
        order_table.add_column("고객명")
        order_table.add_column("수량", justify="right")
        order_table.add_column("상태")

        # 상태별 그룹핑 후 정해진 순서로 출력
        order_map: dict[str, list[OrderDto]] = {s: [] for s in _MONITORING_STATUS_ORDER}
        for o in orders:
            if o.status in order_map:
                order_map[o.status].append(o)

        for status in _MONITORING_STATUS_ORDER:
            group = order_map[status]
            if group:
                for o in group:
                    order_table.add_row(
                        str(o.id),
                        o.sample_name,
                        o.customer,
                        str(o.quantity),
                        o.status,
                    )
            else:
                order_table.add_row("—", "—", "—", "—", f"{status} (없음)")

        console.print(order_table)

        # ── 재고량 Table ──────────────────────────────────────────────
        stock_table = Table(title="재고 현황", show_header=True, header_style="bold cyan")
        stock_table.add_column("시료명")
        stock_table.add_column("재고", justify="right")
        stock_table.add_column("재고상태")

        if not samples:
            stock_table.add_row("—", "—", "등록된 시료가 없습니다")
        else:
            for s in samples:
                # stock_status 색상 매핑
                status_text = s.stock_status if s.stock_status else "—"
                if s.stock_status == "고갈":
                    status_style = "[bold red]고갈[/bold red]"
                elif s.stock_status == "부족":
                    status_style = "[yellow]부족[/yellow]"
                elif s.stock_status == "여유":
                    status_style = "[green]여유[/green]"
                else:
                    status_style = status_text
                stock_table.add_row(s.name, str(s.stock), status_style)

        console.print(stock_table)

    # ------------------------------------------------------------------
    # 생산라인
    # ------------------------------------------------------------------

    def show_production_status(self, job: ProductionJobDto | None) -> None:
        """현재 생산 중인 작업 정보를 표시한다. shortfall 열 포함."""
        if job is None:
            print("생산 중인 작업이 없습니다")
            return

        print("\n[현재 생산 중인 작업]")
        print(f"  주문ID      : {job.order_id}")
        print(f"  시료명      : {job.sample_name}")
        print(f"  고객명      : {job.customer}")
        print(f"  주문 수량   : {job.quantity}")
        print(f"  부족분      : {job.shortfall}")
        print(f"  실생산량    : {job.actual_qty}")
        print(f"  총 생산시간 : {job.total_time:.1f}분")

    def show_production_queue(self, jobs: list[ProductionJobDto]) -> None:
        """생산 대기 큐를 표시한다. shortfall 열 없음, 1-based 대기 순번 표시."""
        if not jobs:
            print("대기 중인 생산 작업이 없습니다")
            return

        print("\n[생산 대기 큐]")
        print(f"{'순번':>4} {'주문ID':<8} {'시료명':<20} {'고객명':<20} {'수량':>6} {'실생산량':>8} {'총시간(분)':>10}")
        print("-" * (4 + 1 + 8 + 1 + 20 + 1 + 20 + 1 + 6 + 1 + 8 + 1 + 10))

        for seq, job in enumerate(jobs, start=1):
            print(
                f"{seq:>4} {job.order_id:<8} {job.sample_name:<20} {job.customer:<20} "
                f"{job.quantity:>6} {job.actual_qty:>8} {job.total_time:>10.1f}"
            )

    # ------------------------------------------------------------------
    # 공통 메시지 / 오류 / 입력
    # ------------------------------------------------------------------

    def show_message(self, message: str) -> None:
        """정상 흐름 1회성 알림을 표시한다."""
        print(f"[알림] {message}")

    def show_error(self, message: str) -> None:
        """입력 오류·상태 위반 메시지를 표시한다."""
        print(f"[오류] {message}")

    def prompt_input(self, prompt: str) -> str:
        """이름·수량 등 일반 데이터 입력을 받는다. 원시 str을 반환한다."""
        return input(f"{prompt}: ")

    def prompt_menu_choice(self, prompt: str) -> str:
        """메뉴 번호 입력을 받는다. 원시 str을 반환한다."""
        return input(f"{prompt} > ")
