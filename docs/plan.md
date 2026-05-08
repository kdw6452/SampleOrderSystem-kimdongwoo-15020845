# 구현 계획 — 반도체 시료 생산 주문 관리 시스템

> 기능 명세: [`docs/PRD.md`](PRD.md) 참조  
> 아키텍처 및 개발 명령어: [`CLAUDE.md`](../CLAUDE.md) 참조

---

## 기술 스택

| 항목 | 선택 |
|------|------|
| 언어 | Python 3.12+ |
| 테스트 | pytest, pytest-cov |
| Mock | unittest.mock.MagicMock |
| 영속성 | JSON 파일 (`os.replace()` 원자적 쓰기) |
| DI | 없음 — `main.py` 수동 생성자 주입 |

---

## 모듈 간 의존성

```
main.py
  └──▶ MainController
         ├──▶ SampleController      ← SampleRepository, BaseView
         ├──▶ OrderController        ← SampleRepository, OrderRepository, BaseView
         ├──▶ MonitoringController   ← SampleRepository, OrderRepository, BaseView
         ├──▶ ShippingController     ← SampleRepository, OrderRepository, BaseView
         └──▶ ProductionController   ← SampleRepository, OrderRepository, BaseView

models/      ──X──▶  views/, controllers/   (import 금지)
views/       ──X──▶  controllers/            (import 금지)
```
> 다이어그램은 런타임 의존성만 표시한다. `BaseController` ABC 상속 관계는 생략.

생산 큐는 별도 클래스 없이 Controller 내부 메서드로 구현한다 — `OrderRepository.get_by_status(PRODUCING)` 결과를 `ProductionController`가 `sorted(key=lambda o: o.id)`로 정렬하여 FIFO를 보장한다. Repository는 정렬 책임 없음.

---

## 단계별 구현 계획

---

### Phase 1 — 프로젝트 초기 설정

> 목표: 실행 가능한 빈 골격 완성

- [ ] `requirements.txt` 작성 (`pytest`, `pytest-cov`, `flake8`, `mypy`)
- [ ] `controllers/base_controller.py` — `BaseController` ABC 빈 파일 생성 (Phase 4에서 내용 구현)
- [ ] 패키지 디렉토리 및 `__init__.py` 생성 (`models/`, `views/`, `controllers/`, `tests/`, `data/`)
- [ ] `.gitignore` 업데이트: `data/*.json`, `__pycache__/`, `*.pyc`, `.venv/`, `venv/`, `.coverage`, `htmlcov/`, `.pytest_cache/`
- [ ] `main.py` 빈 진입점 작성 (실행 시 "시스템 시작" 출력 후 종료)

---

### Phase 2 — 도메인 모델

> 목표: 비즈니스 규칙과 영속성 계층 완성. View·Controller 의존성 없음

#### 2-1. 엔티티

- [ ] `models/sample.py` — `Sample` dataclass

  | 필드 | 타입 | 비고 |
  |------|------|------|
  | `id` | int | Repository 자동 부여 |
  | `name` | str | 고유값 |
  | `avg_production_time` | float | 단위: 분 |
  | `yield_rate` | float | 0.0 초과 1.0 이하 |
  | `stock` | int | 기본값 0 |

- [ ] `models/order.py` — `OrderStatus` Enum + `Order` dataclass

  | OrderStatus | 설명 |
  |-------------|------|
  | `RESERVED` | 주문 접수 |
  | `REJECTED` | 주문 거절 (모니터링 제외) |
  | `PRODUCING` | 재고 부족으로 생산 중 |
  | `CONFIRMED` | 출고 대기 |
  | `RELEASE` | 출고 완료 |

  | 필드 | 타입 | 비고 |
  |------|------|------|
  | `id` | int | Repository 자동 부여 |
  | `sample_id` | int | |
  | `quantity` | int | |
  | `customer` | str | |
  | `shortfall` | `int \| None` | 승인 시 재고 부족분 (PRODUCING 전환 시 저장, 이외 None) |
  | `status` | OrderStatus |

#### 2-2. Repository

- [ ] `models/sample_repository.py` — `SampleRepository` ABC + `JsonSampleRepository`
  - 메서드: `add(sample) -> Sample`, `get_all() -> list[Sample]`, `get_by_id(id) -> Sample | None`, `get_by_name(name) -> Sample | None`, `update(sample) -> None`
  - ID는 Repository가 자동 부여하는 단조 증가 정수 (기존 최대 ID + 1, 최초 등록 시 ID = 1)
  - `os.replace()` 원자적 쓰기, 저장 경로: `data/samples.json`
  - 재고 변경: Controller가 Sample 객체의 stock을 수정 후 `update(sample)` 호출

- [ ] `models/order_repository.py` — `OrderRepository` ABC + `JsonOrderRepository`
  - 메서드: `add(order) -> Order`, `get_all() -> list[Order]`, `get_by_id(id) -> Order | None`, `get_by_status(status) -> list[Order]`, `update_status(order_id, new_status) -> Order`, `update(order) -> None`
  - `update(order)`: Order 전체를 덮어씀 (shortfall 등 필드 변경 후 영속화 용도)
  - ID는 Repository가 자동 부여하는 단조 증가 정수 (기존 최대 ID + 1, 최초 등록 시 ID = 1, 삭제 후에도 재사용 없음, FIFO 보장)
  - 허용 전이 규칙 강제 (위반 시 `ValueError`)

  | 현재 상태 | 허용 전이 |
  |-----------|-----------|
  | `RESERVED` | `CONFIRMED`, `PRODUCING`, `REJECTED` |
  | `PRODUCING` | `CONFIRMED` |
  | `CONFIRMED` | `RELEASE` |
  | `REJECTED`, `RELEASE` | (없음) |

  - 저장 경로: `data/orders.json`

---

### Phase 3 — View 계층

> 목표: 모든 콘솔 I/O를 View에 격리

- [ ] `requirements.txt`에 `rich` 추가 (모니터링 렌더러 — Phase 1에서 의도적으로 제외한 분리 추가)

- [ ] `views/dto.py` — 표시 전용 dataclass

  | DTO | 필드 | 비고 |
  |-----|------|------|
  | `SampleDto` | id: int, name: str, avg_production_time: float, yield_rate: float, stock: int, stock_status: str = "" | stock_status: MonitoringController가 판정 후 채움 ('여유'\|'부족'\|'고갈'). ""이면 View는 해당 열 미표시 |
  | `OrderDto` | id: int, sample_name: str, quantity: int, customer: str, status: str, stock: int \| None = None | status는 OrderStatus.value(str). stock은 ShippingController가 Sample.stock 현재값으로 채움(None이면 View 미표시) |
  | `ProductionJobDto` | order_id: int, sample_name: str, customer: str, quantity: int, shortfall: int, actual_qty: int, total_time: float | shortfall은 PRODUCING 주문에 항상 존재(int) |
  > 대기 순번은 View의 `enumerate(jobs, start=1)`로 부여한다 (1-based).

- [ ] `views/base_view.py` — `BaseView` ABC (메서드 시그니처)
  ```python
  def show_main_menu(self, samples: list[SampleDto]) -> None: ...   # 시료 요약 + 메뉴 번호 목록
  def show_samples(self, samples: list[SampleDto]) -> None: ...
  def show_orders(self, orders: list[OrderDto]) -> None: ...
  def show_monitoring(self, orders: list[OrderDto], samples: list[SampleDto]) -> None: ...
  # MonitoringController가 REJECTED를 제외한 4개 상태 주문만 필터링하여 전달, View가 status 필드로 그룹핑 렌더링
  def show_production_status(self, job: ProductionJobDto | None) -> None: ...
  def show_production_queue(self, jobs: list[ProductionJobDto]) -> None: ...  # enumerate로 대기 순번 부여
  def show_message(self, message: str) -> None: ...
  # show_message()는 주문 생성 결과(ID + RESERVED), 주문 승인/거절 결과,
  # 생산 완료 결과(ID + CONFIRMED), 출고 완료 결과(차감 재고 + RELEASE) 등
  # 단순 1회성 알림에 범용 사용한다. 메인 메뉴 입력 오류는 show_error()로 처리.
  def show_error(self, message: str) -> None: ...
  def prompt_input(self, prompt: str) -> str: ...
  def prompt_menu_choice(self, prompt: str) -> str: ...
  ```

- [ ] `views/console_view.py` — `ConsoleView` 구현체
  - `print()` / `input()` 독점 사용. `rich` 모듈 import는 `show_monitoring()` 내부로만 한정
  - View는 입력값을 타입 변환하지 않음 — 원시 `str` 반환
  - `show_monitoring()`만 Rich Table 필수 (주문량 Table 1개 + 재고량 Table 1개, 상태별 그룹핑). 나머지는 plain `print()`
  - `show_production_status()`: shortfall(부족분) 열 표시함 (PRD §5-6 생산 현황 항목)
  - `show_production_queue()`: `shortfall` 열 표시 안 함 (대기 순번·주문ID·시료명·고객명·수량·실생산량·총시간만 표시)
  - 정상 흐름 결과(성공·안내)는 `show_message()`, 입력 오류·상태 위반은 `show_error()` 사용
  - `show_main_menu(samples)`: 빈 리스트이면 "등록된 시료가 없습니다" 출력 후 메뉴 목록 표시
  - 메뉴 입력 오류 후 재표시 루프는 `MainController`의 while 루프가 담당 (View에 루프 없음)

---

### Phase 4 — Controller 계층

> 목표: 입력 해석, Model 갱신, DTO 변환, 에러 처리

- [ ] `controllers/base_controller.py` — `BaseController` ABC
  - 시그니처: `def run(self) -> None: ...`

- [ ] `controllers/sample_controller.py`
  - 시료 등록: 입력 검증(이름 중복·공백, 수율 0.0 초과~1.0 이하, 생산시간 > 0) → `SampleRepository.add()`
  - 시료 조회: `get_all()` → `SampleDto` 변환 → `view.show_samples()`
  - 시료 검색: 이름 부분 일치 필터링, 공백 검색어는 오류 출력

- [ ] `controllers/order_controller.py`
  - 주문 접수: 입력 검증 → `RESERVED` 상태로 `OrderRepository.add()` → `show_message(f"주문 {order.id} 접수 완료. 상태: RESERVED")`
  - 접수 목록: `get_by_status(RESERVED)` 표시
  - 주문 승인: 재고 확인 → `CONFIRMED` 또는 `PRODUCING` 분기
    - 재고 충분 → `CONFIRMED` 전환 (Order.shortfall = None 유지), `show_message(f"주문 {order.id} CONFIRMED 전환")`
    - 재고 부족 → `shortfall = max(0, quantity - stock)` 계산, `order.shortfall = shortfall` 설정, `order_repository.update(order)` 저장, `update_status(PRODUCING)`, `actual_qty = ceil(shortfall / (yield_rate × 0.9))` 계산 후 `show_message(f"주문 {order.id} PRODUCING 전환. 부족분: {shortfall}, 실생산량: {actual_qty}")`로 표시
  - 주문 거절: `REJECTED` 전환 → `show_message(f"주문 {order.id} REJECTED 전환")`

- [ ] `controllers/monitoring_controller.py`
  - 주문량: 유효 4개 상태별 목록 표시 (`REJECTED` 제외)
  - 재고량: 시료별로 해당 `sample_id`를 가진 진행 중 주문(`RESERVED`+`PRODUCING`+`CONFIRMED`)의 `quantity` 합산 → 여유/부족/고갈 판정 후 `SampleDto.stock_status` 채워 `show_monitoring()` 호출

- [ ] `controllers/shipping_controller.py`
  - 출고 대기 목록: `get_by_status(CONFIRMED)` 표시
  - 출고 실행: `update_status(RELEASE)` 먼저 → 성공 후 `sample.stock -= quantity` → `sample_repository.update(sample)` → `show_message(f"주문 {order.id} RELEASE 전환. 차감 수량: {quantity}, 잔여 재고: {sample.stock}")` (상태 전이 실패 시 재고 변동 없음)

- [ ] `controllers/production_controller.py`
  - 생산량 계산 헬퍼: `_get_producing_sorted()` 내부 메서드로 추출 — `sorted(order_repo.get_by_status(PRODUCING), key=lambda o: o.id)` 반환. 생산 현황·대기 큐·생산 완료 명령에서 공통 사용
  - `actual_qty = ceil(order.shortfall / (sample.yield_rate × 0.9))`, `total_time = sample.avg_production_time × actual_qty` (ProductionController가 호출 시마다 재계산. shortfall 자체는 재계산하지 않음 — Order에 저장된 값 사용)
  - 생산 현황: `get_by_status(PRODUCING)` 결과를 ID 오름차순 정렬 후 첫 번째 항목을 ProductionJobDto로 변환하여 `show_production_status()` 호출. 없으면 `show_message("생산 중인 작업이 없습니다")` (단순 상태 안내 → show_message)
  - 대기 큐: `get_by_status(PRODUCING)` 결과를 ID 오름차순(FIFO) 정렬 후 ProductionJobDto 리스트로 변환하여 `show_production_queue()` 호출
  - 생산 완료 명령: PRODUCING 주문 없으면 `show_error("생산 중인 작업이 없습니다")` 후 중단 (실행 불가 사전 조건 → guard clause, show_error 사용)
    - `shortfall`이 None이면 `view.show_error()` 출력 후 처리 중단 (정상 흐름에서 발생 불가 — 방어 코드, 테스트 대상 제외)
    - 재고 갱신 절차: `get_by_status(PRODUCING)` ID 오름차순 정렬 후 첫 번째 주문 선택 → `update_status(CONFIRMED)` 먼저 → 성공 후 `sample.stock += order.shortfall` → `sample_repository.update(sample)` (상태 전이 실패 시 재고 변동 없음) → `show_message(f"주문 {order.id} CONFIRMED 전환. 재고 +{order.shortfall}")`

- [ ] `controllers/main_controller.py`
  - 메인 루프: 전체 시료 요약 표시 후 메뉴 번호 입력 대기 (시료 없을 때도 요약 영역 표시)
  - `MainMenu` Enum 분기 → 하위 컨트롤러 `run()` 호출
  - 목록에 없는 번호 입력 시 오류 메시지 출력 후 메뉴 재표시

---

### Phase 5 — 통합 및 테스트

> 목표: 전체 흐름 동작 확인 및 커버리지 달성

#### 5-1. Composition Root

- [ ] `main.py` — 모든 Repository·View·Controller를 생성자 주입으로 조립
  - 조립 대상: `JsonSampleRepository`, `JsonOrderRepository`, `ConsoleView`
  - 컨트롤러 의존성은 CLAUDE.md §계층 구조 다이어그램 기준 (Phase 4에서 구현 완료)

#### 5-2. 테스트

| 파일 | 대상 | 격리 방식 |
|------|------|-----------|
| `tests/test_sample_repository.py` | `JsonSampleRepository` | `tmp_path` 픽스처 |
| `tests/test_order_repository.py` | `JsonOrderRepository` (상태 전이 포함) | `tmp_path` 픽스처 |
| `tests/test_sample_controller.py` | `SampleController` | `MagicMock` |
| `tests/test_order_controller.py` | `OrderController` (재고 분기 포함) | `MagicMock` |
| `tests/test_shipping_controller.py` | `ShippingController` | `MagicMock` |
| `tests/test_production_controller.py` | `ProductionController` (생산량 계산 포함) | `MagicMock` |
| `tests/test_monitoring_controller.py` | `MonitoringController` (재고 상태 판정) | `MagicMock` |
| `tests/test_main_controller.py` | `MainController` (메뉴 라우팅) | `MagicMock` |

- [ ] 커버리지 확인: `pytest --cov=models --cov=controllers --cov-report=term-missing --cov-fail-under=80` → 전체 평균 ≥ 80% (views/, tests/ 제외)

#### 5-3. 수동 통합 확인

- [ ] `python main.py` 실행 후 5개 메뉴 전체 진입 확인
- [ ] 황금 경로 시나리오 실행
  1. 시료 등록 → 주문 접수 → 재고 충분 승인 → 출고
  2. 시료 등록 → 주문 접수 → 재고 부족 승인 → 생산 큐 확인 → 생산 완료(수동) → 출고
  3. (시나리오 1에서 등록한 시료 재사용) 주문 접수 → 거절 → 모니터링에서 미표시 확인

---

## 수용 기준 체크리스트

- [ ] `python main.py` 실행 시 5개 메뉴 모두 진입 및 기본 흐름 동작
- [ ] 주문 상태 전이 규칙 위반 시 `ValueError` → `view.show_error()` 출력
- [ ] `print()` / `input()` 이 `views/` 패키지 외부에 존재하지 않음 (Phase 4에서 임시 `print()` 제거 완료 — PowerShell: `Get-ChildItem -Recurse controllers,models -Filter *.py | ForEach-Object { Select-String -Path $_.FullName -Pattern 'print\(|input\(' }` 로 확인. `main.py`는 Composition Root이므로 제외)
- [ ] `models/` 내 파일에 `from views` / `from controllers` import 없음
- [ ] `pytest` 전체 통과
- [ ] `pytest --cov=models --cov=controllers --cov-report=term-missing --cov-fail-under=80` Controller·Model 전체 평균 ≥ 80%
- [ ] `flake8 models/ views/ controllers/` 린트 통과
- [ ] `mypy models/ views/ controllers/` 타입 체크 통과
