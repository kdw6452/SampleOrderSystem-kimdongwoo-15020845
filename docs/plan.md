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

생산 큐는 별도 클래스 없이 Controller 내부 메서드로 구현한다 — `OrderRepository.get_by_status(PRODUCING)`을 주문 ID 오름차순 정렬하여 FIFO를 보장한다.

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
  - 메서드: `add(order) -> Order`, `get_all() -> list[Order]`, `get_by_id(id) -> Order | None`, `get_by_status(status) -> list[Order]`, `update_status(order_id, new_status) -> Order`
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

  | DTO | 필드 |
  |-----|------|
  | `SampleDto` | id, name, avg_production_time, yield_rate, stock |
  | `OrderDto` | id, sample_name, quantity, customer, status |
  | `ProductionJobDto` | order_id, sample_name, customer, quantity, shortfall, actual_qty, total_time |
  > 대기 순번(queue position)은 DTO 필드가 아닌 View의 `enumerate` 로 부여한다.

- [ ] `views/base_view.py` — `BaseView` ABC
  - `show_samples`, `show_orders`, `show_monitoring`, `show_production_status`, `show_production_queue`
  - `show_message`, `show_error`, `prompt_input`, `prompt_menu_choice`

- [ ] `views/console_view.py` — `ConsoleView` 구현체
  - `print()` / `input()` 독점 사용
  - View는 입력값을 타입 변환하지 않음 — 원시 `str` 반환

---

### Phase 4 — Controller 계층

> 목표: 입력 해석, Model 갱신, DTO 변환, 에러 처리

- [ ] `controllers/base_controller.py` — `BaseController` ABC (`run()` 추상 메서드)

- [ ] `controllers/sample_controller.py`
  - 시료 등록: 입력 검증(이름 중복·공백, 수율 0.0 초과~1.0 이하, 생산시간 > 0) → `SampleRepository.add()`
  - 시료 조회: `get_all()` → `SampleDto` 변환 → `view.show_samples()`
  - 시료 검색: 이름 부분 일치 필터링, 공백 검색어는 오류 출력

- [ ] `controllers/order_controller.py`
  - 주문 접수: 입력 검증 → `RESERVED` 상태로 `OrderRepository.add()`
  - 접수 목록: `get_by_status(RESERVED)` 표시
  - 주문 승인: 재고 확인 → `CONFIRMED` 또는 `PRODUCING` 분기
    - `PRODUCING` 전환 시 생산량 계산 후 생산 큐 등록
  - 주문 거절: `REJECTED` 전환

- [ ] `controllers/monitoring_controller.py`
  - 주문량: 유효 4개 상태별 목록 표시 (`REJECTED` 제외)
  - 재고량: 시료별 재고 + 진행 중 주문(`RESERVED` + `PRODUCING` + `CONFIRMED`) 수량 합산 → 여유/부족/고갈 판정

- [ ] `controllers/shipping_controller.py`
  - 출고 대기 목록: `get_by_status(CONFIRMED)` 표시
  - 출고 실행: 재고 차감 → `RELEASE` 전환 → 차감된 재고 수량과 전환 결과 화면 표시

- [ ] `controllers/production_controller.py`
  - 생산량 계산: `actual_qty = ceil(shortfall / (yield_rate × 0.9))`, `total_time = avg_production_time × actual_qty`
  - 생산 현황: `get_by_status(PRODUCING)` 첫 번째 항목 표시
  - 대기 큐: `get_by_status(PRODUCING)`을 주문 ID 오름차순(FIFO)으로 표시
  - 생산 완료 명령: 현재 생산 중(`PRODUCING`) 첫 번째 주문을 `CONFIRMED`로 전이, `stock += shortfall` (수동 트리거, 비동기 없음)

- [ ] `controllers/main_controller.py`
  - 메인 루프: 전체 시료 요약 표시 후 메뉴 번호 입력 대기 (시료 없을 때도 요약 영역 표시)
  - `MainMenu` Enum 분기 → 하위 컨트롤러 `run()` 호출
  - 목록에 없는 번호 입력 시 오류 메시지 출력 후 메뉴 재표시

---

### Phase 5 — 통합 및 테스트

> 목표: 전체 흐름 동작 확인 및 커버리지 달성

#### 5-1. Composition Root

- [ ] `main.py` — 모든 Repository·View·Controller를 생성자 주입으로 조립

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

- [ ] 커버리지 확인: `pytest --cov=. --cov-report=term-missing` → Controller·Model ≥ 80%

#### 5-3. 수동 통합 확인

- [ ] `python main.py` 실행 후 5개 메뉴 전체 진입 확인
- [ ] 황금 경로 시나리오 실행
  1. 시료 등록 → 주문 접수 → 재고 충분 승인 → 출고
  2. 시료 등록 → 주문 접수 → 재고 부족 승인 → 생산 큐 확인 → 생산 완료(수동) → 출고
  3. 주문 접수 → 거절 → 모니터링에서 미표시 확인

---

## 수용 기준 체크리스트

- [ ] `python main.py` 실행 시 5개 메뉴 모두 진입 및 기본 흐름 동작
- [ ] 주문 상태 전이 규칙 위반 시 `ValueError` → `view.show_error()` 출력
- [ ] `print()` / `input()` 이 `views/` 패키지 외부에 존재하지 않음 (Phase 1 `main.py`의 임시 `print()` 제외 — Phase 4 완료 시 제거)
- [ ] `models/` 내 파일에 `from views` / `from controllers` import 없음
- [ ] `pytest` 전체 통과
- [ ] `pytest --cov` Controller·Model 커버리지 ≥ 80%
