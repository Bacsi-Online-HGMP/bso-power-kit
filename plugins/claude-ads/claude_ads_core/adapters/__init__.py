"""Capability-led adapters for normalized Claude Ads inputs."""

from .base import (
    Adapter,
    AdapterCapabilities,
    AdapterError,
    BaseAdapter,
    Capability,
    MutationDisabledError,
)
from .csv_export import CSVExportError, GenericCSVExportAdapter
from .mappings_v1 import (
    NativeDateCheck,
    NativeExportProfile,
    NativeFieldMapping,
    NativeValueGuard,
    get_native_profile,
)
from .native_export import NativeCSVExportAdapter, NativeExportError

__all__ = [
    "Adapter",
    "AdapterCapabilities",
    "AdapterError",
    "BaseAdapter",
    "CSVExportError",
    "Capability",
    "GenericCSVExportAdapter",
    "MutationDisabledError",
    "NativeCSVExportAdapter",
    "NativeDateCheck",
    "NativeExportError",
    "NativeExportProfile",
    "NativeFieldMapping",
    "NativeValueGuard",
    "get_native_profile",
]
