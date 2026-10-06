# Orbit Discovery: architecture and boundaries

## Responsibility

`orbit-discovery` defines a provider-neutral async contract for finding remote service instances.
It is separate from Core's local service registry, which manages components inside one application.
This package has no provider SDK or network dependency; it supports Python 3.11 through 3.14 and is
pre-alpha.

```bash
python -m pip install orbit-discovery
```

## Declared dependencies

The following dependency declarations come from the checked-in manifests. Optional groups and development dependencies are called out separately.

### `pyproject.toml`
- No dependencies declared.
- Optional `process` group: `orbit-core[process-plugins]>=0.1.0a1,<0.2`, `protobuf>=7.35.1,<8`.
- Optional `dev` group: `pytest>=8,<10`, `pytest-asyncio>=0.24,<2`, `ruff>=0.8,<1`, `mypy>=1.13,<2`.

Declared dependencies do not mean that optional providers or services are bundled with this package.

## Implementation layout

Representative implementation files in this checkout:

- `src/orbit_discovery/__init__.py`
- `src/orbit_discovery/discovery.py`
- `src/orbit_discovery/process.py`
- `src/orbit_discovery/v1/service_discovery_pb2.py`

## Public contract and scope

## Provider and request behavior

The static implementation does not perform DNS lookups, health checks, load balancing, caching,
watching, or network requests. It returns candidates; the caller owns selection and connection
policy. The package includes no Consul, Kubernetes, DNS, or cloud registry adapter. Future adapters
must own their SDK, credentials, transport, refresh and shutdown behavior, and provider-specific
failures while implementing the same contract. Validate resolved endpoints against application
egress policy before making outbound requests; discovery data alone is not an SSRF defense.

## Boundary rules

Keep provider SDKs, credentials, transports, and provider-specific error translation in provider adapters. Keep reusable capability contracts in the matching capability package and lifecycle orchestration in Core. Apply the relevant layer for this repository and preserve the dependency direction shown above.
