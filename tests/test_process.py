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

from __future__ import annotations

import asyncio

import pytest

from orbit_discovery import DiscoveryError, ProcessServiceDiscovery
from orbit_discovery.v1 import service_discovery_pb2


class FakeProcess:
    def __init__(self) -> None:
        self.method = ""
        self.request: object | None = None
        self.timeout: float | None = None
        self.failure: Exception | None = None

    async def invoke(
        self,
        method: str,
        request: object,
        response: object,
        *,
        timeout: float | None = None,
    ) -> object:
        self.method = method
        self.request = request
        self.timeout = timeout
        if self.failure is not None:
            raise self.failure
        assert isinstance(response, service_discovery_pb2.ResolveResponse)
        response.instances.add(
            service="catalog",
            instance_id="catalog-1",
            host="2001:db8::1",
            port=8080,
            scheme="https",
            weight=2,
            metadata={"zone": "west"},
        )
        return response


@pytest.mark.asyncio
async def test_process_bridge_maps_typed_endpoint_and_uses_bounded_deadline() -> None:
    process = FakeProcess()
    discovery = ProcessServiceDiscovery(process, request_timeout=1.5)

    instances = await discovery.resolve("catalog")

    assert process.method == "/orbit.discovery.v1.ServiceDiscovery/Resolve"
    assert isinstance(process.request, service_discovery_pb2.ResolveRequest)
    assert process.request.service == "catalog"
    assert process.timeout == 1.5
    assert instances[0].host == "2001:db8::1"
    assert instances[0].base_url == "https://[2001:db8::1]:8080"
    assert instances[0].metadata["zone"] == "west"


@pytest.mark.asyncio
async def test_process_bridge_sanitizes_remote_failures_and_honors_cancellation() -> None:
    process = FakeProcess()
    discovery = ProcessServiceDiscovery(process)
    process.failure = RuntimeError("secret kubeconfig content")
    with pytest.raises(DiscoveryError, match="Could not resolve") as raised:
        await discovery.resolve("catalog")
    assert "secret" not in str(raised.value)

    async def cancelled(*_args: object, **_kwargs: object) -> object:
        raise asyncio.CancelledError

    process.invoke = cancelled  # type: ignore[method-assign]
    with pytest.raises(asyncio.CancelledError):
        await discovery.resolve("catalog")


@pytest.mark.asyncio
async def test_process_bridge_validates_response_and_closed_state() -> None:
    process = FakeProcess()
    discovery = ProcessServiceDiscovery(process)
    with pytest.raises(ValueError):
        await discovery.resolve("bad/service")

    process.failure = None
    await discovery.aclose()
    with pytest.raises(DiscoveryError, match="closed"):
        await discovery.resolve("catalog")
