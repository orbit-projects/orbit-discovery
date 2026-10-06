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
"""Bridge the discovery contract to a Core-hosted process capability."""

from __future__ import annotations

import asyncio
from typing import Protocol

from orbit_discovery.discovery import (
    DiscoveryError,
    ServiceInstance,
    _validate_identifier,
)


class _ProcessInvoker(Protocol):
    """Minimal Core process-host operation required by this capability bridge."""

    async def invoke(
        self,
        method: str,
        request: object,
        response: object,
        *,
        timeout: float | None = None,
    ) -> object:
        """Invoke one protobuf capability request on the supervised plugin process."""


class ProcessServiceDiscovery:
    """Expose a Core-supervised process plugin as ``ServiceDiscovery``.

    The process host owns executable startup, authentication, configuration delivery, health,
    and shutdown. This adapter validates typed discovery results and owns only its closed state.
    Install ``orbit-discovery[process]`` to use this optional bridge.
    """

    def __init__(self, process: _ProcessInvoker, *, request_timeout: float = 5.0) -> None:
        """Bind one active Core process host and bound each discovery request deadline."""
        if isinstance(request_timeout, bool) or not isinstance(request_timeout, (int, float)):
            raise TypeError("request_timeout must be a number.")
        if not 0.05 <= request_timeout <= 60.0:
            raise ValueError("request_timeout must be between 0.05 and 60 seconds.")
        self._process = process
        self._request_timeout = float(request_timeout)
        self._closed = False

    async def resolve(self, service: str) -> tuple[ServiceInstance, ...]:
        """Resolve a bounded immutable snapshot over the versioned discovery Protobuf contract."""
        from orbit_discovery.v1 import service_discovery_pb2

        if self._closed:
            raise DiscoveryError("Service discovery resolver is closed.")
        name = _validate_identifier(service, "service")
        request = service_discovery_pb2.ResolveRequest(service=name)
        response = service_discovery_pb2.ResolveResponse()
        try:
            await self._process.invoke(
                "/orbit.discovery.v1.ServiceDiscovery/Resolve",
                request,
                response,
                timeout=self._request_timeout,
            )
        except asyncio.CancelledError:
            raise
        except Exception:
            raise DiscoveryError("Could not resolve service through the process adapter.") from None
        try:
            if len(response.instances) > 4_096:
                raise ValueError("response endpoint limit exceeded")
            return tuple(
                ServiceInstance(
                    service=item.service,
                    instance_id=item.instance_id,
                    host=item.host,
                    port=item.port,
                    scheme=item.scheme,
                    weight=item.weight,
                    metadata=dict(item.metadata),
                )
                for item in response.instances
            )
        except (TypeError, ValueError):
            raise DiscoveryError(
                "Process adapter returned an invalid discovery response."
            ) from None

    async def aclose(self) -> None:
        """Stop new discovery calls without closing the externally owned process host."""
        self._closed = True
