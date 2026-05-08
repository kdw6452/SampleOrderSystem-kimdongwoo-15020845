# -*- coding: utf-8 -*-
# tests/test_order_repository.py — JsonOrderRepository 단위 테스트
# tmp_path 픽스처로 JSON 파일 격리, 상태 전이 규칙 포함
from __future__ import annotations

import dataclasses
import os

import pytest

from models.order import Order, OrderStatus
from models.order_repository import JsonOrderRepository


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def repo(tmp_path) -> JsonOrderRepository:
    """각 테스트마다 독립적인 임시 디렉토리를 사용하는 Repository."""
    return JsonOrderRepository(path=str(tmp_path / "orders.json"))


def _make_order(**kwargs) -> Order:
    defaults = {
        "id": 0,
        "sample_id": 1,
        "quantity": 10,
        "customer": "TestCo",
        "status": OrderStatus.RESERVED,
        "shortfall": None,
    }
    defaults.update(kwargs)
    return Order(**defaults)


# ---------------------------------------------------------------------------
# add
# ---------------------------------------------------------------------------

class TestAdd:
    def test_add_first_order_gets_id_1(self, repo: JsonOrderRepository) -> None:
        order = _make_order(id=0)
        result = repo.add(order)
        assert result.id == 1

    def test_add_returns_order_with_fields(self, repo: JsonOrderRepository) -> None:
        result = repo.add(_make_order(id=0, quantity=5, customer="Fab"))
        assert result.quantity == 5
        assert result.customer == "Fab"
        assert result.status == OrderStatus.RESERVED

    def test_add_sequential_ids(self, repo: JsonOrderRepository) -> None:
        ids = [repo.add(_make_order(id=0, customer=f"C{i}")).id for i in range(4)]
        assert ids == [1, 2, 3, 4]

    def test_add_original_id_is_ignored(self, repo: JsonOrderRepository) -> None:
        result = repo.add(_make_order(id=999, customer="Override"))
        assert result.id == 1

    def test_add_preserves_shortfall(self, repo: JsonOrderRepository) -> None:
        result = repo.add(_make_order(id=0, shortfall=5))
        assert result.shortfall == 5

    def test_add_shortfall_none_by_default(self, repo: JsonOrderRepository) -> None:
        result = repo.add(_make_order(id=0))
        assert result.shortfall is None


# ---------------------------------------------------------------------------
# get_all
# ---------------------------------------------------------------------------

class TestGetAll:
    def test_get_all_empty(self, repo: JsonOrderRepository) -> None:
        assert repo.get_all() == []

    def test_get_all_returns_all_orders(self, repo: JsonOrderRepository) -> None:
        repo.add(_make_order(id=0, customer="A"))
        repo.add(_make_order(id=0, customer="B"))
        all_orders = repo.get_all()
        assert len(all_orders) == 2
        customers = {o.customer for o in all_orders}
        assert customers == {"A", "B"}

    def test_get_all_status_deserialized_correctly(self, repo: JsonOrderRepository) -> None:
        repo.add(_make_order(id=0, status=OrderStatus.RESERVED))
        orders = repo.get_all()
        assert orders[0].status == OrderStatus.RESERVED


# ---------------------------------------------------------------------------
# get_by_id
# ---------------------------------------------------------------------------

class TestGetById:
    def test_get_by_id_found(self, repo: JsonOrderRepository) -> None:
        added = repo.add(_make_order(id=0, customer="FoundCo"))
        result = repo.get_by_id(added.id)
        assert result is not None
        assert result.customer == "FoundCo"

    def test_get_by_id_not_found_returns_none(self, repo: JsonOrderRepository) -> None:
        assert repo.get_by_id(999) is None


# ---------------------------------------------------------------------------
# get_by_status
# ---------------------------------------------------------------------------

class TestGetByStatus:
    def test_get_by_status_reserved_only(self, repo: JsonOrderRepository) -> None:
        repo.add(_make_order(id=0, customer="R1", status=OrderStatus.RESERVED))
        repo.add(_make_order(id=0, customer="R2", status=OrderStatus.RESERVED))
        # CONFIRMED 상태로 직접 추가 (add 후 update_status 사용)
        o = repo.add(_make_order(id=0, customer="C1", status=OrderStatus.RESERVED))
        repo.update_status(o.id, OrderStatus.CONFIRMED)

        reserved = repo.get_by_status(OrderStatus.RESERVED)
        assert len(reserved) == 2
        assert all(o.status == OrderStatus.RESERVED for o in reserved)

    def test_get_by_status_empty_when_none(self, repo: JsonOrderRepository) -> None:
        repo.add(_make_order(id=0, status=OrderStatus.RESERVED))
        confirmed = repo.get_by_status(OrderStatus.CONFIRMED)
        assert confirmed == []

    def test_get_by_status_producing(self, repo: JsonOrderRepository) -> None:
        o = repo.add(_make_order(id=0, status=OrderStatus.RESERVED))
        repo.update_status(o.id, OrderStatus.PRODUCING)
        producing = repo.get_by_status(OrderStatus.PRODUCING)
        assert len(producing) == 1
        assert producing[0].id == o.id


# ---------------------------------------------------------------------------
# update_status — 성공 케이스
# ---------------------------------------------------------------------------

class TestUpdateStatusAllowed:
    def test_reserved_to_confirmed(self, repo: JsonOrderRepository) -> None:
        o = repo.add(_make_order(id=0))
        result = repo.update_status(o.id, OrderStatus.CONFIRMED)
        assert result.status == OrderStatus.CONFIRMED

    def test_reserved_to_producing(self, repo: JsonOrderRepository) -> None:
        o = repo.add(_make_order(id=0))
        result = repo.update_status(o.id, OrderStatus.PRODUCING)
        assert result.status == OrderStatus.PRODUCING

    def test_reserved_to_rejected(self, repo: JsonOrderRepository) -> None:
        o = repo.add(_make_order(id=0))
        result = repo.update_status(o.id, OrderStatus.REJECTED)
        assert result.status == OrderStatus.REJECTED

    def test_producing_to_confirmed(self, repo: JsonOrderRepository) -> None:
        o = repo.add(_make_order(id=0))
        repo.update_status(o.id, OrderStatus.PRODUCING)
        result = repo.update_status(o.id, OrderStatus.CONFIRMED)
        assert result.status == OrderStatus.CONFIRMED

    def test_confirmed_to_release(self, repo: JsonOrderRepository) -> None:
        o = repo.add(_make_order(id=0))
        repo.update_status(o.id, OrderStatus.CONFIRMED)
        result = repo.update_status(o.id, OrderStatus.RELEASE)
        assert result.status == OrderStatus.RELEASE

    def test_update_status_returns_updated_order(self, repo: JsonOrderRepository) -> None:
        o = repo.add(_make_order(id=0, customer="ReturnCheck"))
        result = repo.update_status(o.id, OrderStatus.CONFIRMED)
        assert result.customer == "ReturnCheck"

    def test_update_status_persists(self, repo: JsonOrderRepository) -> None:
        o = repo.add(_make_order(id=0))
        repo.update_status(o.id, OrderStatus.CONFIRMED)
        reloaded = repo.get_by_id(o.id)
        assert reloaded is not None
        assert reloaded.status == OrderStatus.CONFIRMED


# ---------------------------------------------------------------------------
# update_status — 금지 전이 (ValueError 강제)
# ---------------------------------------------------------------------------

class TestUpdateStatusForbidden:
    def test_reserved_to_release_raises(self, repo: JsonOrderRepository) -> None:
        o = repo.add(_make_order(id=0))
        with pytest.raises(ValueError, match="허용되지 않은 상태 전이"):
            repo.update_status(o.id, OrderStatus.RELEASE)

    def test_producing_to_reserved_raises(self, repo: JsonOrderRepository) -> None:
        o = repo.add(_make_order(id=0))
        repo.update_status(o.id, OrderStatus.PRODUCING)
        with pytest.raises(ValueError, match="허용되지 않은 상태 전이"):
            repo.update_status(o.id, OrderStatus.RESERVED)

    def test_producing_to_rejected_raises(self, repo: JsonOrderRepository) -> None:
        o = repo.add(_make_order(id=0))
        repo.update_status(o.id, OrderStatus.PRODUCING)
        with pytest.raises(ValueError, match="허용되지 않은 상태 전이"):
            repo.update_status(o.id, OrderStatus.REJECTED)

    def test_confirmed_to_reserved_raises(self, repo: JsonOrderRepository) -> None:
        o = repo.add(_make_order(id=0))
        repo.update_status(o.id, OrderStatus.CONFIRMED)
        with pytest.raises(ValueError, match="허용되지 않은 상태 전이"):
            repo.update_status(o.id, OrderStatus.RESERVED)

    def test_confirmed_to_producing_raises(self, repo: JsonOrderRepository) -> None:
        o = repo.add(_make_order(id=0))
        repo.update_status(o.id, OrderStatus.CONFIRMED)
        with pytest.raises(ValueError, match="허용되지 않은 상태 전이"):
            repo.update_status(o.id, OrderStatus.PRODUCING)

    def test_rejected_to_any_raises(self, repo: JsonOrderRepository) -> None:
        o = repo.add(_make_order(id=0))
        repo.update_status(o.id, OrderStatus.REJECTED)
        for status in [
            OrderStatus.RESERVED,
            OrderStatus.PRODUCING,
            OrderStatus.CONFIRMED,
            OrderStatus.RELEASE,
        ]:
            with pytest.raises(ValueError, match="허용되지 않은 상태 전이"):
                repo.update_status(o.id, status)

    def test_release_to_any_raises(self, repo: JsonOrderRepository) -> None:
        o = repo.add(_make_order(id=0))
        repo.update_status(o.id, OrderStatus.CONFIRMED)
        repo.update_status(o.id, OrderStatus.RELEASE)
        for status in [
            OrderStatus.RESERVED,
            OrderStatus.PRODUCING,
            OrderStatus.CONFIRMED,
            OrderStatus.REJECTED,
        ]:
            with pytest.raises(ValueError, match="허용되지 않은 상태 전이"):
                repo.update_status(o.id, status)

    def test_update_status_nonexistent_order_raises(self, repo: JsonOrderRepository) -> None:
        with pytest.raises(ValueError, match="not found"):
            repo.update_status(999, OrderStatus.CONFIRMED)


# ---------------------------------------------------------------------------
# 영속성 / 직렬화
# ---------------------------------------------------------------------------

class TestPersistence:
    def test_data_survives_reload(self, tmp_path) -> None:
        path = str(tmp_path / "orders.json")
        repo1 = JsonOrderRepository(path=path)
        repo1.add(_make_order(id=0, customer="Survive"))

        repo2 = JsonOrderRepository(path=path)
        all_orders = repo2.get_all()
        assert len(all_orders) == 1
        assert all_orders[0].customer == "Survive"

    def test_status_enum_round_trips(self, tmp_path) -> None:
        """OrderStatus Enum 값이 JSON 직렬화/역직렬화 후에도 유지된다."""
        path = str(tmp_path / "orders.json")
        repo1 = JsonOrderRepository(path=path)
        o = repo1.add(_make_order(id=0, status=OrderStatus.RESERVED))
        repo1.update_status(o.id, OrderStatus.PRODUCING)

        repo2 = JsonOrderRepository(path=path)
        reloaded = repo2.get_by_id(o.id)
        assert reloaded is not None
        assert reloaded.status == OrderStatus.PRODUCING

    def test_shortfall_none_round_trips(self, tmp_path) -> None:
        path = str(tmp_path / "orders.json")
        repo1 = JsonOrderRepository(path=path)
        repo1.add(_make_order(id=0, shortfall=None))

        repo2 = JsonOrderRepository(path=path)
        reloaded = repo2.get_all()[0]
        assert reloaded.shortfall is None

    def test_shortfall_int_round_trips(self, tmp_path) -> None:
        path = str(tmp_path / "orders.json")
        repo1 = JsonOrderRepository(path=path)
        repo1.add(_make_order(id=0, shortfall=7))

        repo2 = JsonOrderRepository(path=path)
        reloaded = repo2.get_all()[0]
        assert reloaded.shortfall == 7

    def test_directory_auto_created(self, tmp_path) -> None:
        nested_path = str(tmp_path / "sub" / "dir" / "orders.json")
        repo = JsonOrderRepository(path=nested_path)
        repo.add(_make_order(id=0))
        assert os.path.exists(nested_path)

    def test_id_monotonically_increasing(self, tmp_path) -> None:
        path = str(tmp_path / "orders.json")
        repo = JsonOrderRepository(path=path)
        o1 = repo.add(_make_order(id=0, customer="C1"))
        o2 = repo.add(_make_order(id=0, customer="C2"))
        assert o2.id == o1.id + 1

    def test_fifo_order_preserved_by_id(self, repo: JsonOrderRepository) -> None:
        """PRODUCING 주문을 ID 오름차순으로 정렬하면 FIFO 순서가 보장된다."""
        orders = [repo.add(_make_order(id=0, customer=f"C{i}")) for i in range(3)]
        for o in orders:
            repo.update_status(o.id, OrderStatus.PRODUCING)
        producing = repo.get_by_status(OrderStatus.PRODUCING)
        # ID 오름차순 정렬이 등록 순서(FIFO)와 일치해야 한다
        sorted_ids = sorted(o.id for o in producing)
        expected_ids = [o.id for o in orders]
        assert sorted_ids == expected_ids
