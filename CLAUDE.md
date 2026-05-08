# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 프로젝트 배경

가상의 반도체 회사 S-Semi가 시료(Sample) 생산·주문 관리를 엑셀/메모장에서 벗어나 체계화하기 위해 개발하는 콘솔 기반 시스템. 고객(연구소·팹리스·대학)의 주문을 접수하여 웨이퍼 공정 설비를 거쳐 출고까지의 전 흐름을 관리한다.

이 프로젝트는 동일 저장소 내 3개의 PoC를 통합하여 완성된다 (DummyDataGenerator_PoC는 범위 외):

| PoC | 역할 |
|-----|------|
| `ConsoleMVC_PoC` | MVC 골격 — 5개 메뉴 도메인 구조 |
| `DataPersistence_PoC` | JSON 파일 기반 영속성 — Repository 패턴, 원자적 쓰기 |
| `DataMonitor_PoC` | 실시간 콘솔 모니터링 — JSON 파일 폴링, Rich 렌더러 |

## 개발 명령어

```bash
# 의존성 설치
pip install -r requirements.txt

# 실행
python main.py

# 전체 테스트
pytest

# 단일 테스트
pytest tests/test_order_controller.py::TestOrderController::test_approve_order

# 커버리지 포함 (전체)
pytest --cov=. --cov-report=term-missing

# 커버리지 수용 기준 확인 (Controller·Model 전체 평균 ≥ 80%)
pytest --cov=models --cov=controllers --cov-report=term-missing --cov-fail-under=80

# 린트
flake8 models/ views/ controllers/ tests/

# 타입 체크
mypy models/ views/ controllers/

```

## 도메인 핵심 제약

> 이해관계자 및 기능 범위 상세: [`docs/PRD.md`](docs/PRD.md) 참조

- **생산라인은 시료를 한 번에 하나씩 순차 생산**한다 — 병렬 생산 없음.
- **주문된 시료에 한해서만** 생산을 진행한다 — 재고 충분 시 생산 불필요.
- **고객은 시스템에 직접 접근하지 않는다** — 주문담당자가 콘솔에서 대리 입력.
- **shortfall은 주문 승인 시 PRODUCING 분기에서만 계산·저장** — `shortfall = max(0, quantity - stock)` (승인 시점 기준). CONFIRMED 분기에서는 None 유지. 생산 완료 시 `stock += order.shortfall`.
- **주문 ID는 Repository가 자동 부여하는 단조 증가 정수** — ID 오름차순 = FIFO 보장.
- **CONFIRMED 상태는 재고 논리 예약 상태** — 물리 재고 차감은 RELEASE 전이 시점(출고 실행)에 발생한다.

## 아키텍처

### 계층 구조

ConsoleMVC_PoC의 MVC 골격 위에 DataPersistence의 JSON Repository와 DataMonitor의 모니터링 루프를 조합한다.

```
main.py  ← Composition Root (모든 의존성 수동 주입)
├── controllers/
│   ├── base_controller.py       # BaseController ABC (run() 추상 메서드)
│   ├── main_controller.py       # 메인 이벤트 루프, MainMenu Enum 분기
│   ├── sample_controller.py     # 시료 등록·조회·검색
│   ├── order_controller.py      # 주문 접수·승인·거절
│   ├── monitoring_controller.py # 상태별 집계, 재고 현황 (DataMonitor 통합)
│   ├── shipping_controller.py   # CONFIRMED → RELEASE 출고
│   └── production_controller.py # 생산 현황·대기 큐(FIFO) 표시, 실생산량 = ceil(부족분/(수율×0.9))
├── models/
│   ├── sample.py                # Sample 엔티티 (id, name, avg_production_time, yield_rate, stock)
│   ├── order.py                 # Order 엔티티 + OrderStatus Enum
│   ├── sample_repository.py     # SampleRepository ABC + JsonSampleRepository
│   └── order_repository.py      # OrderRepository ABC + JsonOrderRepository
├── views/
│   ├── dto.py                   # SampleDto / OrderDto / ProductionJobDto (Model→View 변환 전용)
│   ├── base_view.py             # BaseView ABC
│   └── console_view.py          # ConsoleView 구현체
├── data/
│   └── __init__.py
└── tests/
```

### 주문 상태 전이

> 상태 정의 및 모니터링 범위 상세: [`docs/PRD.md`](docs/PRD.md) § 주문 상태 참조

```
RESERVED (주문접수)
    ├─ 거절 ──▶ REJECTED          ← 모니터링 제외, 정상 흐름 외
    └─ 승인
         ├─ 재고 충분 ──▶ CONFIRMED (출고대기) ──▶ RELEASE (출고완료)
         └─ 재고 부족 ──▶ PRODUCING (생산중) ──▶ CONFIRMED ──▶ RELEASE
```

전이 규칙은 `OrderRepository.update_status()`가 강제한다 — 허용되지 않은 전이 시 `ValueError`.

`PRODUCING → CONFIRMED` 전이는 생산담당자가 `ProductionController`의 "생산 완료" 명령을 실행할 때 수동으로 트리거된다 (비동기 자동 전이 없음).

### 계층 간 의존성 규칙

```
main.py
  └──▶ Controller ──▶ Repository (Model), View
                          │
                    DTO 변환 후 View 전달

models/ ──X──▶ views/, controllers/  (import 금지)
views/  ──X──▶ controllers/           (import 금지)
print() / input() ──X──▶ views/ 외부  (사용 금지)
```

- Controller가 Model → DTO 변환을 전담한다.
- View는 `SampleDto` / `OrderDto` / `ProductionJobDto`만 수신하며, 원시 `str`만 반환한다.
- `main.py`가 유일한 Composition Root — 모든 구체 클래스를 생성자 주입으로 조립한다.

### 영속성 (DataPersistence_PoC 패턴)

- 저장 포맷: `data/samples.json`, `data/orders.json`
- `os.replace()`를 사용한 원자적 쓰기 (중간 상태 노출 방지)
- `SampleRepository` ABC + `JsonSampleRepository`, `OrderRepository` ABC + `JsonOrderRepository` — 각 도메인별 개별 ABC로 구현. InMemoryRepository는 구현 대상 외(테스트는 `tmp_path` 픽스처로 격리)

### 모니터링 (DataMonitor_PoC 패턴)

- `MonitoringController`가 JSON 파일을 주기적으로 폴링하여 상태 집계를 갱신한다.
- Rich 렌더러를 통해 재고 현황·주문 상태를 실시간 출력한다.

## 핵심 규칙

- Python 3.12+, 타입 힌트 필수 (`str | None` 문법)
- 메뉴 상수는 `enum.Enum` 사용
- Controller 내 에러 처리: `try/except` → `view.show_error()` 출력
- 테스트: Controller는 `MagicMock`으로 격리, Repository는 `pytest`의 `tmp_path` 픽스처로 JSON 파일 격리
- 커버리지 목표: Controller·Model 전체 평균 ≥ 80% (`--cov-fail-under=80`)
