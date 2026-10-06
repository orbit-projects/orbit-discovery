# Copyright 2026-present Orbit Contributors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Provider-neutral remote service discovery types and a static local implementation."""

from __future__ import annotations

import ipaddress
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Protocol, runtime_checkable

_IDENTIFIER = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9._-]{0,126}[A-Za-z0-9])?\Z")
_METADATA_KEY = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9_.-]{0,63}\Z")
_DNS_LABEL = re.compile(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\Z")
_MAX_SERVICES = 1_024
_MAX_INSTANCES_PER_SERVICE = 4_096
_MAX_METADATA_ENTRIES = 16
_MAX_METADATA_VALUE_LENGTH = 256
_MAX_METADATA_BYTES = 4_096
DISCOVERY_DEPENDENCY_KEY = "orbit.discovery"


class DiscoveryError(RuntimeError):
    """Raised when an adapter cannot resolve or close a discovery resource safely."""


@dataclass(frozen=True, slots=True)
class ServiceInstance:
    """Validated network location and bounded metadata for one remote service instance.

    ``metadata`` is excluded from the representation because adapters may attach values that
    operators consider sensitive. Do not put credentials or bearer tokens in metadata.
    """

    service: str
    instance_id: str
    host: str = field(repr=False)
    port: int
    scheme: str = "http"
    weight: int = 1
    metadata: Mapping[str, str] = field(default_factory=dict, repr=False)

    def __post_init__(self) -> None:
        """Normalize identifiers, host literals, and metadata into immutable bounded values."""
        object.__setattr__(self, "service", _validate_identifier(self.service, "service"))
        object.__setattr__(
            self, "instance_id", _validate_identifier(self.instance_id, "instance_id")
        )
        object.__setattr__(self, "host", _normalize_host(self.host))
        if (
            isinstance(self.port, bool)
            or not isinstance(self.port, int)
            or not 1 <= self.port <= 65_535
        ):
            raise ValueError("port must be an integer between 1 and 65535.")
        if not isinstance(self.scheme, str) or self.scheme.lower() not in {"http", "https"}:
            raise ValueError("scheme must be http or https.")
        object.__setattr__(self, "scheme", self.scheme.lower())
        if (
            isinstance(self.weight, bool)
            or not isinstance(self.weight, int)
            or not 1 <= self.weight <= 1_000
        ):
            raise ValueError("weight must be an integer between 1 and 1000.")
        object.__setattr__(self, "metadata", _freeze_metadata(self.metadata))

    @property
    def authority(self) -> str:
        """Return a URL authority with IPv6 literals safely bracketed."""
        address = f"[{self.host}]" if ":" in self.host else self.host
        return f"{address}:{self.port}"

    @property
    def base_url(self) -> str:
        """Return a credential-free HTTP(S) origin for the instance."""
        return f"{self.scheme}://{self.authority}"


@runtime_checkable
class ServiceDiscovery(Protocol):
    """Async contract for resolving remote service names to immutable endpoint snapshots.

    Provider adapters register an implementation with Core's container under
    ``DISCOVERY_DEPENDENCY_KEY``. Expected provider failures use :class:`DiscoveryError`; adapter
    calls must propagate task cancellation unchanged.
    """

    async def resolve(self, service: str) -> tuple[ServiceInstance, ...]:
        """Return the current candidate endpoints, or an empty tuple when none are known."""

    async def aclose(self) -> None:
        """Close owned provider resources and reject later operations."""


class StaticServiceDiscovery:
    """Immutable, process-local service map for development and deterministic tests.

    It performs no DNS lookup, network request, health check, load balancing, or automatic refresh.
    Provider adapters should implement :class:`ServiceDiscovery` and own their transport lifecycle.
    """

    def __init__(
        self,
        services: Mapping[str, Sequence[ServiceInstance]],
        *,
        max_services: int = 128,
        max_instances_per_service: int = 128,
    ) -> None:
        """Validate and freeze a bounded map; never retain caller-owned mutable collections."""
        _validate_bound(max_services, "max_services", _MAX_SERVICES)
        _validate_bound(
            max_instances_per_service,
            "max_instances_per_service",
            _MAX_INSTANCES_PER_SERVICE,
        )
        if not isinstance(services, Mapping):
            raise TypeError("services must be a mapping of service names to endpoint sequences.")
        result: dict[str, tuple[ServiceInstance, ...]] = {}
        for name, candidates in services.items():
            if len(result) >= max_services:
                raise ValueError("service map exceeds max_services.")
            service = _validate_identifier(name, "service")
            if service in result:
                raise ValueError("service map contains a duplicate normalized name.")
            if isinstance(candidates, (str, bytes)) or not isinstance(candidates, Sequence):
                raise TypeError("each service value must be an endpoint sequence.")
            instances: list[ServiceInstance] = []
            seen_ids: set[str] = set()
            for candidate in candidates:
                if len(instances) >= max_instances_per_service:
                    raise ValueError("service map exceeds max_instances_per_service.")
                if not isinstance(candidate, ServiceInstance) or candidate.service != service:
                    raise ValueError("each endpoint must be a ServiceInstance for its map key.")
                if candidate.instance_id in seen_ids:
                    raise ValueError("service map contains a duplicate instance_id.")
                seen_ids.add(candidate.instance_id)
                instances.append(candidate)
            result[service] = tuple(instances)
        self._services = MappingProxyType(result)
        self._closed = False

    @property
    def service_names(self) -> tuple[str, ...]:
        """Return configured service names without exposing endpoint metadata."""
        return tuple(self._services)

    async def resolve(self, service: str) -> tuple[ServiceInstance, ...]:
        """Return an immutable configured snapshot; unknown names resolve to no endpoints."""
        self._ensure_open()
        normalized = _validate_identifier(service, "service")
        return self._services.get(normalized, ())

    async def aclose(self) -> None:
        """Close the static resolver idempotently; it owns no external resources."""
        self._closed = True

    async def __aenter__(self) -> StaticServiceDiscovery:
        """Enter an already-configured resolver context."""
        self._ensure_open()
        return self

    async def __aexit__(self, *exc: object) -> None:
        """Close the resolver when leaving its async context."""
        await self.aclose()

    def __repr__(self) -> str:
        """Describe configured capacity without exposing hosts or metadata."""
        total = sum(len(items) for items in self._services.values())
        return (
            f"StaticServiceDiscovery(services={len(self._services)}, "
            f"instances={total}, closed={self._closed})"
        )

    def _ensure_open(self) -> None:
        """Reject resolution after lifecycle shutdown."""
        if self._closed:
            raise DiscoveryError("Service discovery resolver is closed.")


def _validate_identifier(value: object, field_name: str) -> str:
    """Require a bounded identifier safe for diagnostics and provider key composition."""
    if not isinstance(value, str) or _IDENTIFIER.fullmatch(value) is None:
        raise ValueError(f"{field_name} must be a bounded ASCII service identifier.")
    return value


def _normalize_host(value: object) -> str:
    """Canonicalize a DNS hostname or IP literal without accepting URL syntax or userinfo."""
    if not isinstance(value, str) or not value or len(value) > 253 or value != value.strip():
        raise ValueError("host must be a DNS hostname or IP address.")
    if any(character in value for character in "/\\@?#%") or any(ord(c) < 33 for c in value):
        raise ValueError("host must not contain URL syntax, credentials, or whitespace.")
    try:
        address = ipaddress.ip_address(value)
    except ValueError:
        hostname = value[:-1] if value.endswith(".") else value
        if not hostname:
            raise ValueError("host must be a DNS hostname or IP address.") from None
        try:
            normalized = hostname.encode("idna").decode("ascii").lower()
        except UnicodeError:
            raise ValueError("host must be a valid DNS hostname or IP address.") from None
        labels = normalized.split(".")
        if len(normalized) > 253 or any(_DNS_LABEL.fullmatch(label) is None for label in labels):
            raise ValueError("host must be a valid DNS hostname or IP address.") from None
        return normalized
    if isinstance(address, ipaddress.IPv6Address) and address.scope_id is not None:
        raise ValueError("scoped IPv6 addresses are not supported.")
    return address.compressed


def _freeze_metadata(value: object) -> Mapping[str, str]:
    """Copy bounded string metadata into a read-only mapping, ignoring dishonest len reports."""
    if not isinstance(value, Mapping):
        raise TypeError("metadata must be a mapping of string keys and values.")
    result: dict[str, str] = {}
    size = 0
    for key, item in value.items():
        if len(result) >= _MAX_METADATA_ENTRIES:
            raise ValueError("metadata exceeds the entry limit.")
        if not isinstance(key, str) or _METADATA_KEY.fullmatch(key) is None:
            raise ValueError("metadata keys must be bounded safe ASCII identifiers.")
        if (
            not isinstance(item, str)
            or len(item) > _MAX_METADATA_VALUE_LENGTH
            or any(ord(character) < 32 or ord(character) == 127 for character in item)
        ):
            raise ValueError("metadata values must be bounded control-free strings.")
        size += len(key.encode("ascii")) + len(item.encode("utf-8"))
        if size > _MAX_METADATA_BYTES:
            raise ValueError("metadata exceeds the encoded size limit.")
        result[key] = item
    return MappingProxyType(result)


def _validate_bound(value: object, field_name: str, maximum: int) -> None:
    """Validate a positive integer capacity with a hard package limit."""
    if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= maximum:
        raise ValueError(f"{field_name} must be an integer between 1 and {maximum}.")


__all__ = [
    "DISCOVERY_DEPENDENCY_KEY",
    "DiscoveryError",
    "ServiceDiscovery",
    "ServiceInstance",
    "StaticServiceDiscovery",
]
