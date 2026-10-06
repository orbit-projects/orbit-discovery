# Orbit Discovery

`orbit-discovery` defines a provider-neutral async contract for finding remote service instances.
It is separate from Core's local service registry, which manages components inside one application.
This package has no provider SDK or network dependency; it supports Python 3.11 through 3.14 and is
pre-alpha.

```bash
python -m pip install orbit-discovery
```

## Local static discovery

`StaticServiceDiscovery` is an immutable, bounded map for development and deterministic tests. It
normalizes hostnames and IP literals, validates HTTP(S) origins, bounds metadata, and owns no socket
or DNS resources:

```python
from orbit_discovery import ServiceInstance, StaticServiceDiscovery

discovery = StaticServiceDiscovery(
    {
        "catalog": (
            ServiceInstance(
                service="catalog",
                instance_id="catalog-local-1",
                host="127.0.0.1",
                port=8081,
                scheme="http",
            ),
        ),
    },
)


async def find_catalog() -> None:
    candidates = await discovery.resolve("catalog")
    if candidates:
        print(candidates[0].base_url)
    await discovery.aclose()
```

The `ServiceDiscovery` protocol returns immutable endpoint snapshots. An application or adapter that
creates a resolver owns its lifecycle and must call `aclose()` at shutdown. Core-aware provider
plugins register this contract under `DISCOVERY_DEPENDENCY_KEY`; the capability itself has no Core
dependency. Adapters should normalize provider failures as `DiscoveryError` and propagate task
cancellation. Metadata is copied, bounded, immutable, and omitted from representations; never store
credentials or bearer tokens in metadata. Service and instance identifiers should also remain free
of secrets.

## Provider and request behavior

The static implementation does not perform DNS lookups, health checks, load balancing, caching,
watching, or network requests. It returns candidates; the caller owns selection and connection
policy. The package includes no Consul, Kubernetes, DNS, or cloud registry adapter. Future adapters
must own their SDK, credentials, transport, refresh and shutdown behavior, and provider-specific
failures while implementing the same contract. Validate resolved endpoints against application
egress policy before making outbound requests; discovery data alone is not an SSRF defense.

## Process plugins

The versioned `orbit.discovery.v1` Protobuf schema defines the typed Resolve request and endpoint
snapshot shared with process plugins. Install `orbit-discovery[process]` to use
`ProcessServiceDiscovery` as an adapter around Core's supervised process host. Core owns process
startup, one-use authentication, deadlines, and shutdown; the bridge validates provider results
and presents this package's existing `ServiceDiscovery` interface. It never starts a subprocess or
owns Core's process lifecycle itself. Select either a Python provider adapter or an explicitly
configured process plugin in application wiring; do not let runtime selection happen implicitly.

Go providers can implement the same contract with the separately installable `orbit-discovery-go`
SDK, which provides generated client/server bindings and bounded endpoint validation. Kubernetes
is one provider adapter; the SDK itself has no provider or cloud SDK dependency.

```bash
python -m pip install 'orbit-discovery[process]'
```

The process protocol and capability schema use plaintext loopback for trusted local plugins. They
do not sandbox provider code.

## Documentation

The package-specific guides cover [architecture](docs/architecture/overview.md), [operations and security](docs/operations/README.md), and [development](docs/development/README.md), with [security guidance](docs/security/overview.md). The [documentation index](docs/README.md) links to the full package overview and project policies.

## Development

```bash
python -m pip install -e '.[dev]'
pytest
ruff check .
mypy
```

Licensed under Apache-2.0.

