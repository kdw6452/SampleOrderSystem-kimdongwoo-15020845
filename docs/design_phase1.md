# Design — Phase 1: 프로젝트 초기 설정

> 상위 계획: [`docs/plan.md`](plan.md) § Phase 1  
> 아키텍처 원칙: [`CLAUDE.md`](../CLAUDE.md)

---

## 1. 목표

실행 가능한 빈 골격을 완성한다.

- 패키지 계층 구조(디렉토리 + `__init__.py`)를 확정한다.
- 의존성과 무시 목록을 고정하여 이후 Phase의 환경 일관성을 보장한다.
- `python main.py` 가 오류 없이 실행되는 최소 진입점을 제공한다.
- 이 Phase에서는 비즈니스 로직을 작성하지 않는다.

---

## 2. 산출물 목록

| 파일/디렉토리 | 설명 |
|---|---|
| `requirements.txt` | 런타임·개발 의존성 목록 |
| `.gitignore` | 추적 제외 항목 (기존 파일에 추가) |
| `main.py` | 진입점 — "시스템 시작" 출력 후 종료 |
| `models/__init__.py` | models 패키지 선언 (빈 파일) |
| `views/__init__.py` | views 패키지 선언 (빈 파일) |
| `controllers/__init__.py` | controllers 패키지 선언 (빈 파일) |
| `tests/__init__.py` | tests 패키지 선언 (빈 파일) |
| `data/` | JSON 영속 파일 저장 디렉토리 (git 추적 제외) |

---

## 3. 디렉토리 레이아웃

Phase 1 완료 시점의 파일 트리:

```
SampleOrderSystem/
├── main.py
├── requirements.txt
├── .gitignore
├── CLAUDE.md
├── docs/
│   ├── PRD.md
│   ├── plan.md
│   └── design_phase1.md
├── models/
│   └── __init__.py
├── views/
│   └── __init__.py
├── controllers/
│   └── __init__.py
├── tests/
│   └── __init__.py
└── data/              ← git 추적 제외, 런타임 생성
```

`data/` 디렉토리는 런타임에 Repository가 생성한다. Phase 1에서는 빈 디렉토리만 두며 `.gitkeep`을 사용하지 않는다 — `.gitignore`로 내용물 전체를 제외하면 디렉토리 자체도 커밋 대상이 아니므로, Repository 구현(Phase 2)에서 `os.makedirs(exist_ok=True)`로 자동 생성한다.

---

## 4. 파일 상세 설계

---

### 4-1. `requirements.txt`

```
pytest
pytest-cov
rich
```

| 패키지 | 용도 |
|---|---|
| `pytest` | 테스트 실행기 |
| `pytest-cov` | 커버리지 측정 (`--cov` 플래그) |
| `rich` | 모니터링 콘솔 렌더러 (DataMonitor_PoC 패턴) |

> 버전 고정은 하지 않는다 — 개발 초기 단계이므로 최신 호환 버전을 사용한다. 배포 환경이 확정되면 `pip freeze > requirements.lock`으로 분리한다.

---

### 4-2. `.gitignore` 추가 항목

기존 `.gitignore`에 아래 항목을 추가한다:

```gitignore
# 런타임 데이터
data/*.json

# Python 캐시
__pycache__/
*.pyc
*.pyo

# 가상환경
.venv/
venv/

# 테스트·커버리지
.coverage
htmlcov/
.pytest_cache/
```

**설계 근거**

- `data/*.json`: 주문·시료 데이터는 런타임 상태이며 소스 관리 대상이 아니다.
- `__pycache__/`: 컴파일 캐시는 플랫폼·버전 의존적이므로 공유하지 않는다.
- `.venv/`: 가상환경 디렉토리는 로컬 환경 전용이다.
- `.coverage` / `htmlcov/`: 커버리지 산출물은 CI 아티팩트이며 소스가 아니다.

---

### 4-3. `main.py`

```python
def main() -> None:
    print("시스템 시작")


if __name__ == "__main__":
    main()
```

**설계 결정**

- `main()` 함수로 감싸는 이유: Phase 5에서 Composition Root로 확장 시 함수 본문만 교체하면 되고, `if __name__ == "__main__"` 가드는 그대로 유지된다.
- 출력 메시지 `"시스템 시작"`: 진입점 정상 동작 확인용. Phase 4(MainController 구현)에서 메인 루프로 교체된다.
- 타입 힌트(`-> None`): CLAUDE.md 규칙 — Python 3.12+ 타입 힌트 필수.

---

### 4-4. 패키지 `__init__.py`

`models/`, `views/`, `controllers/`, `tests/` 각각에 빈 `__init__.py`를 생성한다.

```python
# 빈 파일
```

**설계 근거**

- Python이 해당 디렉토리를 패키지로 인식하게 한다.
- Phase 2~4에서 각 모듈을 `from models.sample import Sample` 형태로 import하기 위해 필요하다.
- `tests/__init__.py`는 `pytest`가 패키지 내 테스트를 발견할 수 있게 한다.

---

## 5. 수용 기준

| # | 검증 항목 | 검증 방법 |
|---|---|---|
| AC-1 | `python main.py` 실행 시 `"시스템 시작"` 출력 후 정상 종료(exit 0) | 터미널 직접 실행 |
| AC-2 | `pytest` 실행 시 수집 오류 없이 0개 테스트 통과 | `pytest` 출력 확인 |
| AC-3 | `data/*.json` 파일이 `git status`에서 추적되지 않음 | `git status` 확인 |
| AC-4 | `models`, `views`, `controllers`, `tests`가 Python 패키지로 import 가능 | `python -c "import models, views, controllers, tests"` |
| AC-5 | `pip install -r requirements.txt` 오류 없이 완료 | pip 출력 확인 |

---

## 6. Phase 2 전환 조건

아래가 모두 충족되면 Phase 2(도메인 모델) 구현을 시작할 수 있다.

- [ ] AC-1 ~ AC-5 전항 통과
- [ ] 디렉토리 구조가 §3 레이아웃과 일치
- [ ] `requirements.txt`가 커밋됨
- [ ] `.gitignore` 추가 항목이 커밋됨
