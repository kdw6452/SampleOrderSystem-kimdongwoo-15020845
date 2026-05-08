# -*- coding: utf-8 -*-
# tests/test_sample_repository.py — JsonSampleRepository 단위 테스트
# tmp_path 픽스처로 JSON 파일 격리
from __future__ import annotations

import os

import pytest

from models.sample import Sample
from models.sample_repository import JsonSampleRepository


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def repo(tmp_path: pytest.TempPathFactory) -> JsonSampleRepository:
    """각 테스트마다 독립적인 임시 디렉토리를 사용하는 Repository."""
    return JsonSampleRepository(path=str(tmp_path / "samples.json"))


def _make_sample(**kwargs) -> Sample:
    defaults = {
        "id": 0,
        "name": "SampleA",
        "avg_production_time": 30.0,
        "yield_rate": 0.9,
        "stock": 0,
    }
    defaults.update(kwargs)
    return Sample(**defaults)


# ---------------------------------------------------------------------------
# add
# ---------------------------------------------------------------------------

class TestAdd:
    def test_add_first_sample_gets_id_1(self, repo: JsonSampleRepository) -> None:
        sample = _make_sample(id=0, name="S1")
        result = repo.add(sample)
        assert result.id == 1

    def test_add_returns_sample_with_assigned_id(self, repo: JsonSampleRepository) -> None:
        sample = _make_sample(id=0, name="S1")
        result = repo.add(sample)
        assert result.name == "S1"
        assert result.avg_production_time == 30.0
        assert result.yield_rate == 0.9
        assert result.stock == 0

    def test_add_second_sample_gets_id_2(self, repo: JsonSampleRepository) -> None:
        repo.add(_make_sample(id=0, name="S1"))
        result = repo.add(_make_sample(id=0, name="S2"))
        assert result.id == 2

    def test_add_id_is_monotonically_increasing(self, repo: JsonSampleRepository) -> None:
        ids = [repo.add(_make_sample(id=0, name=f"S{i}")).id for i in range(5)]
        assert ids == [1, 2, 3, 4, 5]

    def test_add_persists_to_json(self, repo: JsonSampleRepository) -> None:
        repo.add(_make_sample(id=0, name="Persist"))
        assert os.path.exists(repo._path)

    def test_add_original_sample_id_is_ignored(self, repo: JsonSampleRepository) -> None:
        """add() 호출 시 전달된 id 값은 무시되고 Repository가 새 ID를 부여한다."""
        result = repo.add(_make_sample(id=999, name="S1"))
        assert result.id == 1


# ---------------------------------------------------------------------------
# get_all
# ---------------------------------------------------------------------------

class TestGetAll:
    def test_get_all_empty_returns_empty_list(self, repo: JsonSampleRepository) -> None:
        assert repo.get_all() == []

    def test_get_all_returns_all_added_samples(self, repo: JsonSampleRepository) -> None:
        repo.add(_make_sample(id=0, name="A"))
        repo.add(_make_sample(id=0, name="B"))
        results = repo.get_all()
        assert len(results) == 2
        names = {s.name for s in results}
        assert names == {"A", "B"}

    def test_get_all_returns_correct_fields(self, repo: JsonSampleRepository) -> None:
        repo.add(_make_sample(id=0, name="X", avg_production_time=45.0, yield_rate=0.85, stock=10))
        samples = repo.get_all()
        assert len(samples) == 1
        s = samples[0]
        assert s.name == "X"
        assert s.avg_production_time == 45.0
        assert s.yield_rate == 0.85
        assert s.stock == 10


# ---------------------------------------------------------------------------
# get_by_id
# ---------------------------------------------------------------------------

class TestGetById:
    def test_get_by_id_returns_correct_sample(self, repo: JsonSampleRepository) -> None:
        repo.add(_make_sample(id=0, name="A"))
        repo.add(_make_sample(id=0, name="B"))
        result = repo.get_by_id(1)
        assert result is not None
        assert result.name == "A"

    def test_get_by_id_returns_none_when_not_found(self, repo: JsonSampleRepository) -> None:
        result = repo.get_by_id(999)
        assert result is None

    def test_get_by_id_returns_correct_id(self, repo: JsonSampleRepository) -> None:
        added = repo.add(_make_sample(id=0, name="S"))
        result = repo.get_by_id(added.id)
        assert result is not None
        assert result.id == added.id


# ---------------------------------------------------------------------------
# get_by_name
# ---------------------------------------------------------------------------

class TestGetByName:
    def test_get_by_name_exact_match(self, repo: JsonSampleRepository) -> None:
        repo.add(_make_sample(id=0, name="ExactName"))
        result = repo.get_by_name("ExactName")
        assert result is not None
        assert result.name == "ExactName"

    def test_get_by_name_returns_none_when_not_found(self, repo: JsonSampleRepository) -> None:
        result = repo.get_by_name("NonExistent")
        assert result is None

    def test_get_by_name_case_sensitive(self, repo: JsonSampleRepository) -> None:
        repo.add(_make_sample(id=0, name="CaseSensitive"))
        result = repo.get_by_name("casesensitive")
        assert result is None

    def test_get_by_name_partial_match_not_supported(self, repo: JsonSampleRepository) -> None:
        """get_by_name은 완전 일치만 지원한다. 부분 일치는 Controller 책임."""
        repo.add(_make_sample(id=0, name="SampleAlpha"))
        result = repo.get_by_name("Alpha")
        assert result is None


# ---------------------------------------------------------------------------
# update
# ---------------------------------------------------------------------------

class TestUpdate:
    def test_update_stock(self, repo: JsonSampleRepository) -> None:
        added = repo.add(_make_sample(id=0, name="S", stock=0))
        import dataclasses
        updated = dataclasses.replace(added, stock=50)
        repo.update(updated)
        retrieved = repo.get_by_id(added.id)
        assert retrieved is not None
        assert retrieved.stock == 50

    def test_update_yield_rate(self, repo: JsonSampleRepository) -> None:
        added = repo.add(_make_sample(id=0, name="S", yield_rate=0.9))
        import dataclasses
        updated = dataclasses.replace(added, yield_rate=0.75)
        repo.update(updated)
        retrieved = repo.get_by_id(added.id)
        assert retrieved is not None
        assert retrieved.yield_rate == 0.75

    def test_update_nonexistent_raises_value_error(self, repo: JsonSampleRepository) -> None:
        ghost = _make_sample(id=999, name="Ghost")
        with pytest.raises(ValueError, match="not found"):
            repo.update(ghost)

    def test_update_does_not_change_other_samples(self, repo: JsonSampleRepository) -> None:
        a = repo.add(_make_sample(id=0, name="A", stock=0))
        repo.add(_make_sample(id=0, name="B", stock=0))
        import dataclasses
        repo.update(dataclasses.replace(a, stock=100))
        b_after = repo.get_by_name("B")
        assert b_after is not None
        assert b_after.stock == 0


# ---------------------------------------------------------------------------
# 원자적 쓰기 / 영속성
# ---------------------------------------------------------------------------

class TestPersistence:
    def test_data_survives_reload(self, tmp_path) -> None:
        """같은 경로로 새 Repository 인스턴스를 만들어도 데이터가 유지된다."""
        path = str(tmp_path / "samples.json")
        repo1 = JsonSampleRepository(path=path)
        repo1.add(_make_sample(id=0, name="Persist"))

        repo2 = JsonSampleRepository(path=path)
        all_samples = repo2.get_all()
        assert len(all_samples) == 1
        assert all_samples[0].name == "Persist"

    def test_directory_auto_created(self, tmp_path) -> None:
        """하위 디렉토리가 없어도 자동으로 생성된다."""
        nested_path = str(tmp_path / "sub" / "dir" / "samples.json")
        repo = JsonSampleRepository(path=nested_path)
        repo.add(_make_sample(id=0, name="DirTest"))
        assert os.path.exists(nested_path)

    def test_id_not_reused_after_knowledge_of_max(self, tmp_path) -> None:
        """ID는 삭제 없이도 단조 증가가 보장된다. 최대 ID 기반 계산."""
        path = str(tmp_path / "samples.json")
        repo = JsonSampleRepository(path=path)
        s1 = repo.add(_make_sample(id=0, name="S1"))
        s2 = repo.add(_make_sample(id=0, name="S2"))
        assert s2.id == s1.id + 1
