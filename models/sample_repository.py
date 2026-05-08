# -*- coding: utf-8 -*-
# models/sample_repository.py — SampleRepository ABC + JsonSampleRepository
# models/ 내에서 views/, controllers/ import 금지
from __future__ import annotations

import abc
import dataclasses
import json
import os
import tempfile

from models.sample import Sample


class SampleRepository(abc.ABC):
    """SampleRepository 추상 기반 클래스."""

    @abc.abstractmethod
    def add(self, sample: Sample) -> Sample:
        """시료를 저장하고 ID가 부여된 Sample을 반환한다."""

    @abc.abstractmethod
    def get_all(self) -> list[Sample]:
        """등록된 전체 시료 목록을 반환한다."""

    @abc.abstractmethod
    def get_by_id(self, id: int) -> Sample | None:
        """ID로 시료를 조회한다. 없으면 None 반환."""

    @abc.abstractmethod
    def get_by_name(self, name: str) -> Sample | None:
        """이름으로 시료를 조회한다. 없으면 None 반환."""

    @abc.abstractmethod
    def update(self, sample: Sample) -> None:
        """기존 시료 정보를 갱신한다."""


class JsonSampleRepository(SampleRepository):
    """JSON 파일 기반 SampleRepository 구현체.

    os.replace()를 사용한 원자적 쓰기로 중간 상태 노출을 방지한다.
    ID는 기존 최대 ID + 1로 단조 증가하며, 삭제 후에도 재사용하지 않는다.
    """

    def __init__(self, path: str = "data/samples.json") -> None:
        self._path = path
        dir_name = os.path.dirname(path)
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def add(self, sample: Sample) -> Sample:
        samples = self._load()
        new_id = self._next_id(samples)
        new_sample = dataclasses.replace(sample, id=new_id)
        samples.append(new_sample)
        self._save(samples)
        return new_sample

    def get_all(self) -> list[Sample]:
        return self._load()

    def get_by_id(self, id: int) -> Sample | None:
        for sample in self._load():
            if sample.id == id:
                return sample
        return None

    def get_by_name(self, name: str) -> Sample | None:
        for sample in self._load():
            if sample.name == name:
                return sample
        return None

    def update(self, sample: Sample) -> None:
        samples = self._load()
        for i, s in enumerate(samples):
            if s.id == sample.id:
                samples[i] = sample
                self._save(samples)
                return
        raise ValueError(f"Sample with id={sample.id} not found.")

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _next_id(self, samples: list[Sample]) -> int:
        if not samples:
            return 1
        return max(s.id for s in samples) + 1

    def _load(self) -> list[Sample]:
        if not os.path.exists(self._path):
            return []
        with open(self._path, encoding="utf-8") as f:
            raw: list[dict] = json.load(f)
        return [Sample(**item) for item in raw]

    def _save(self, samples: list[Sample]) -> None:
        data = [dataclasses.asdict(s) for s in samples]
        dir_name = os.path.dirname(self._path)
        # tempfile을 동일 디렉토리에 생성해 os.replace()가 원자적으로 동작하게 함
        fd, tmp_path = tempfile.mkstemp(
            dir=dir_name if dir_name else ".", suffix=".tmp"
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            os.replace(tmp_path, self._path)
        except Exception:
            # 실패 시 임시 파일 정리
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise
