"""Adapter protocol and safe read-only defaults."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass
from os import PathLike
from typing import Any, Literal, Mapping, Protocol, Sequence, runtime_checkable

from ..models import AccountSnapshot

CapabilityMode = Literal["export-read", "live-read", "draft-write", "live-write"]
CapabilityStatus = Literal["declared", "implemented", "fixture-verified", "live-verified", "disabled"]


class AdapterError(RuntimeError):
    """Base exception for adapter failures."""


class MutationDisabledError(AdapterError):
    """Raised when an adapter is asked to mutate without write capability."""


@dataclass(frozen=True)
class Capability:
    """One independently discoverable adapter capability."""

    capability_id: str
    mode: CapabilityMode
    status: CapabilityStatus
    disabled_reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class AdapterCapabilities:
    """Runtime capability discovery result for one adapter."""

    schema_version: Literal["1.0.0"]
    adapter_id: str
    platform: str
    default_mutation_mode: Literal["read-only"]
    capabilities: tuple[Capability, ...]

    @property
    def writes_enabled(self) -> bool:
        return any(
            item.mode in {"draft-write", "live-write"}
            and item.status in {"implemented", "fixture-verified", "live-verified"}
            for item in self.capabilities
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "adapter_id": self.adapter_id,
            "platform": self.platform,
            "default_mutation_mode": self.default_mutation_mode,
            "writes_enabled": self.writes_enabled,
            "capabilities": [item.to_dict() for item in self.capabilities],
        }


@runtime_checkable
class Adapter(Protocol):
    """Common interface for export, live-read, and future write adapters."""

    def discover_capabilities(self) -> AdapterCapabilities: ...

    def read_snapshot(self, source: str | PathLike[str]) -> AccountSnapshot: ...

    def draft_changes(self, requested_changes: Sequence[Mapping[str, Any]]) -> Mapping[str, Any]: ...

    def apply_changes(self, mutation_plan: Mapping[str, Any]) -> Mapping[str, Any]: ...

    def verify_changes(self, mutation_record: Mapping[str, Any]) -> Mapping[str, Any]: ...

    def rollback(self, mutation_record: Mapping[str, Any]) -> Mapping[str, Any]: ...


class BaseAdapter(ABC):
    """Base adapter whose mutation surface is denied unless overridden."""

    platform: str
    adapter_id: str

    @abstractmethod
    def discover_capabilities(self) -> AdapterCapabilities:
        """Return executable capabilities rather than inferred platform support."""

    @abstractmethod
    def read_snapshot(self, source: str | PathLike[str]) -> AccountSnapshot:
        """Read authorized data and normalize it to an AccountSnapshot."""

    def _mutation_disabled(self, operation: str) -> MutationDisabledError:
        return MutationDisabledError(
            f"{self.adapter_id} is read-only; {operation} requires a separately verified write adapter"
        )

    def draft_changes(self, requested_changes: Sequence[Mapping[str, Any]]) -> Mapping[str, Any]:
        raise self._mutation_disabled("draft_changes")

    def apply_changes(self, mutation_plan: Mapping[str, Any]) -> Mapping[str, Any]:
        raise self._mutation_disabled("apply_changes")

    def verify_changes(self, mutation_record: Mapping[str, Any]) -> Mapping[str, Any]:
        raise self._mutation_disabled("verify_changes")

    def rollback(self, mutation_record: Mapping[str, Any]) -> Mapping[str, Any]:
        raise self._mutation_disabled("rollback")
