# -*- coding: utf-8 -*-
# views/console_view.py — ConsoleView 구현체
# print() / input() 독점 사용.
# rich import는 show_monitoring() 내부로만 한정한다.
# View는 str만 반환하며, 타입 변환을 수행하지 않는다.
from __future__ import annotations

import unicodedata

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


# ------------------------------------------------------------------
# 전각 문자 너비 헬퍼 (한국어·한자 등 전각 문자는 2칸 차지)
# ------------------------------------------------------------------

def _w(s: str) -> int:
    """문자열의 터미널 표시 너비를 반환한다 (전각 2, 반각 1)."""
    return sum(
        2 if unicodedata.east_asian_width(c) in ("W", "F") else 1
        for c in s
    )


def _lj(s: str, width: int) -> str:
    """표시 너비 기준 왼쪽 정렬 패딩."""
    return s + " " * max(0, width - _w(s))


def _rj(s: str, width: int) -> str:
    """표시 너비 기준 오른쪽 정렬 패딩."""
    return " " * max(0, width - _w(s)) + s


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

        print("\n[시료 현황]")
        if not samples:
            print("  등록된 시료가 없습니다")
        else:
            # 컬럼 너비: ID=4, 시료명=20(표시), 재고=6
            hdr = "  " + _lj("ID", 4) + "  " + _lj("시료명", 20) + "  " + _rj("재고", 6)
            print(hdr)
            print("  " + "-" * (4 + 2 + 20 + 2 + 6))
            for s in samples:
                print("  " + _lj(str(s.id), 4) + "  " + _lj(s.name, 20) + "  " + _rj(str(s.stock), 6))

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

        has_status = any(s.stock_status for s in samples)

        # 컬럼 표시 너비
        C_ID   = 4
        C_NAME = 20
        C_TIME = 17   # "평균생산시간(분)" 표시 너비 = 17
        C_RATE = 8    # "수율" = 4, 데이터 "0.90" = 4 → 8로 여유
        C_STOCK = 6
        C_STATUS = 8  # "재고상태" = 8

        sep = "-" * (C_ID + 2 + C_NAME + 2 + C_TIME + 2 + C_RATE + 2 + C_STOCK
                     + (2 + C_STATUS if has_status else 0))

        row = (_lj("ID", C_ID) + "  " + _lj("시료명", C_NAME) + "  "
               + _rj("평균생산시간(분)", C_TIME) + "  "
               + _rj("수율", C_RATE) + "  " + _rj("재고", C_STOCK))
        if has_status:
            row += "  " + _rj("재고상태", C_STATUS)
        print("\n" + row)
        print(sep)

        for s in samples:
            line = (_lj(str(s.id), C_ID) + "  " + _lj(s.name, C_NAME) + "  "
                    + _rj(f"{s.avg_production_time:.1f}", C_TIME) + "  "
                    + _rj(f"{s.yield_rate:.2f}", C_RATE) + "  "
                    + _rj(str(s.stock), C_STOCK))
            if has_status:
                line += "  " + _rj(s.stock_status if s.stock_status else "-", C_STATUS)
            print(line)

    # ------------------------------------------------------------------
    # 주문
    # ------------------------------------------------------------------

    def show_orders(self, orders: list[OrderDto]) -> None:
        """주문 목록을 표시한다."""
        if not orders:
            print("주문이 없습니다")
            return

        has_stock = any(o.stock is not None for o in orders)

        # 컬럼 표시 너비
        C_ID     = 6   # "주문ID" = 6
        C_NAME   = 20
        C_CUST   = 20
        C_QTY    = 6   # "수량" = 4
        C_STATUS = 12  # "상태" = 4, "CONFIRMED" = 9
        C_STOCK  = 8   # "현재재고" = 8

        sep_len = C_ID + 2 + C_NAME + 2 + C_CUST + 2 + C_QTY + 2 + C_STATUS
        if has_stock:
            sep_len += 2 + C_STOCK

        hdr = (_lj("주문ID", C_ID) + "  " + _lj("시료명", C_NAME) + "  "
               + _lj("고객명", C_CUST) + "  "
               + _rj("수량", C_QTY) + "  " + _lj("상태", C_STATUS))
        if has_stock:
            hdr += "  " + _rj("현재재고", C_STOCK)
        print("\n" + hdr)
        print("-" * sep_len)

        for o in orders:
            line = (_lj(str(o.id), C_ID) + "  " + _lj(o.sample_name, C_NAME) + "  "
                    + _lj(o.customer, C_CUST) + "  "
                    + _rj(str(o.quantity), C_QTY) + "  " + _lj(o.status, C_STATUS))
            if has_stock and o.stock is not None:
                line += "  " + _rj(str(o.stock), C_STOCK)
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

        # 레이블 너비를 표시 너비 12로 통일
        W = 12
        print("\n[현재 생산 중인 작업]")
        print("  " + _lj("주문ID", W) + f": {job.order_id}")
        print("  " + _lj("시료명", W) + f": {job.sample_name}")
        print("  " + _lj("고객명", W) + f": {job.customer}")
        print("  " + _lj("주문 수량", W) + f": {job.quantity}")
        print("  " + _lj("부족분", W) + f": {job.shortfall}")
        print("  " + _lj("실생산량", W) + f": {job.actual_qty}")
        print("  " + _lj("총 생산시간", W) + f": {job.total_time:.1f}분")

    def show_production_queue(self, jobs: list[ProductionJobDto]) -> None:
        """생산 대기 큐를 표시한다. shortfall 열 없음, 1-based 대기 순번 표시."""
        if not jobs:
            print("대기 중인 생산 작업이 없습니다")
            return

        C_SEQ  = 4   # "순번" = 4
        C_ID   = 6   # "주문ID" = 6
        C_NAME = 20
        C_CUST = 20
        C_QTY  = 6   # "수량" = 4
        C_PROD = 8   # "실생산량" = 8
        C_TIME = 10  # "총시간(분)" = 10

        sep_len = C_SEQ + 2 + C_ID + 2 + C_NAME + 2 + C_CUST + 2 + C_QTY + 2 + C_PROD + 2 + C_TIME

        hdr = (_rj("순번", C_SEQ) + "  " + _lj("주문ID", C_ID) + "  "
               + _lj("시료명", C_NAME) + "  " + _lj("고객명", C_CUST) + "  "
               + _rj("수량", C_QTY) + "  " + _rj("실생산량", C_PROD) + "  "
               + _rj("총시간(분)", C_TIME))
        print("\n[생산 대기 큐]")
        print(hdr)
        print("-" * sep_len)

        for seq, job in enumerate(jobs, start=1):
            print(
                _rj(str(seq), C_SEQ) + "  " + _lj(str(job.order_id), C_ID) + "  "
                + _lj(job.sample_name, C_NAME) + "  " + _lj(job.customer, C_CUST) + "  "
                + _rj(str(job.quantity), C_QTY) + "  " + _rj(str(job.actual_qty), C_PROD) + "  "
                + _rj(f"{job.total_time:.1f}", C_TIME)
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
