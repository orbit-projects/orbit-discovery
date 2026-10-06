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
"""Service discovery contract and static resolver validation tests."""

from __future__ import annotations

from types import MappingProxyType

import pytest

from orbit_discovery import (
    DISCOVERY_DEPENDENCY_KEY,
    DiscoveryError,
    ServiceDiscovery,
    ServiceInstance,
    StaticServiceDiscovery,
)


def make_instance(
    *,
    service: str = "catalog",
    instance_id: str = "catalog-1",
    host: str = "API.Example.COM.",
    port: int = 443,
    scheme: str = "https",
    metadata: dict[str, str] | None = None,
) -> ServiceInstance:
    return ServiceInstance(
        service=service,
        instance_id=instance_id,
        host=host,
        port=port,
        scheme=scheme,
        metadata=metadata or {},
    )


@pytest.mark.parametrize(
    "value", ["", "https://host", "user@host", "host/path", "bad host", "-bad.host", "host_"]
)
def test_host_rejects_url_syntax_and_invalid_dns_names(value: str) -> None:
    with pytest.raises(ValueError, match="host"):
        make_instance(host=value)


def test_dns_host_is_normalized_and_metadata_is_immutable() -> None:
    source = {"region": "west", "token_hint": "never a credential"}
    instance = make_instance(metadata=source)
    source["region"] = "changed"

    assert instance.host == "api.example.com"
    assert instance.base_url == "https://api.example.com:443"
    assert instance.metadata == {"region": "west", "token_hint": "never a credential"}
    assert isinstance(instance.metadata, MappingProxyType)
    with pytest.raises(TypeError):
        instance.metadata["region"] = "changed"  # type: ignore[index]


def test_ipv4_and_ipv6_origins_are_rendered_safely() -> None:
    ipv4 = make_instance(host="192.0.2.1", port=8080, scheme="http")
    ipv6 = make_instance(host="2001:db8::1", port=8443)

    assert ipv4.base_url == "http://192.0.2.1:8080"
    assert ipv6.base_url == "https://[2001:db8::1]:8443"


@pytest.mark.parametrize("port", [0, -1, 65_536, True, 1.5])
def test_port_must_be_an_integer_network_port(port: object) -> None:
    with pytest.raises(ValueError, match="port"):
        make_instance(port=port)  # type: ignore[arg-type]


@pytest.mark.parametrize("scheme", ["ftp", "", "https://", "http ", "HTTP:foo"])
def test_only_http_schemes_are_accepted(scheme: str) -> None:
    with pytest.raises(ValueError, match="scheme"):
        make_instance(scheme=scheme)


@pytest.mark.parametrize(
    "metadata",
    [
        {"bad key": "value"},
        {"key": "line\nbreak"},
        {"key": "x" * 257},
        {f"key-{index}": "value" for index in range(17)},
        {f"key{index:02d}": "x" * 256 for index in range(16)},
    ],
)
def test_metadata_is_bounded_and_rejects_invalid_values(metadata: dict[str, str]) -> None:
    with pytest.raises(ValueError, match="metadata"):
        make_instance(metadata=metadata)


def test_service_instance_repr_does_not_expose_host_or_metadata() -> None:
    instance = make_instance(
        host="internal-secret.example", metadata={"credential": "secret-value"}
    )

    assert "internal-secret.example" not in repr(instance)
    assert "secret-value" not in repr(instance)


async def test_static_discovery_implements_contract_and_returns_immutable_snapshots() -> None:
    first = make_instance()
    source = {"catalog": [first]}
    discovery = StaticServiceDiscovery(source)
    source["catalog"].clear()
    assert isinstance(discovery, ServiceDiscovery)
    assert DISCOVERY_DEPENDENCY_KEY == "orbit.discovery"

    resolved = await discovery.resolve("catalog")

    assert resolved == (first,)
    assert isinstance(resolved, tuple)
    assert await discovery.resolve("missing") == ()
    assert discovery.service_names == ("catalog",)
    assert "api.example.com" not in repr(discovery)


async def test_static_discovery_validates_matching_service_and_duplicate_instances() -> None:
    with pytest.raises(ValueError, match="for its map key"):
        StaticServiceDiscovery({"catalog": (make_instance(service="payments"),)})
    with pytest.raises(ValueError, match="duplicate instance_id"):
        StaticServiceDiscovery(
            {"catalog": (make_instance(), make_instance(host="other.example.com"))}
        )


async def test_static_discovery_enforces_service_and_endpoint_bounds() -> None:
    instance = make_instance()
    with pytest.raises(ValueError, match="max_services"):
        StaticServiceDiscovery({"catalog": (instance,)}, max_services=0)
    with pytest.raises(ValueError, match="max_instances_per_service"):
        StaticServiceDiscovery({"catalog": (instance,)}, max_instances_per_service=0)
    with pytest.raises(ValueError, match="max_services"):
        StaticServiceDiscovery({"one": (), "two": ()}, max_services=1)
    with pytest.raises(ValueError, match="max_instances_per_service"):
        StaticServiceDiscovery(
            {
                "catalog": (
                    instance,
                    make_instance(instance_id="catalog-2"),
                )
            },
            max_instances_per_service=1,
        )


async def test_close_is_idempotent_and_blocks_future_resolution() -> None:
    discovery = StaticServiceDiscovery({"catalog": (make_instance(),)})
    await discovery.aclose()
    await discovery.aclose()

    with pytest.raises(DiscoveryError, match="closed"):
        await discovery.resolve("catalog")
    with pytest.raises(DiscoveryError, match="closed"):
        await discovery.__aenter__()
