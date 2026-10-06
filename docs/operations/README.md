# Orbit Discovery: operations and security

This guide organizes runtime behavior documented by the package. It does not certify production readiness. Verify provider/client versions, permissions, transport security, limits, and failure behavior in the target environment before release.

## Configuration surface

Environment names found in the package README:

The package README does not name `ORBIT_*` variables. Use its typed constructors and application configuration, and confirm exact runtime inputs in the implementation before deployment.

Use the package README's constructor and deployment examples. Store credentials in a secret manager and avoid logging credentials, raw provider errors, request data, or opaque cursors.

## Lifecycle, failure behavior, and limits

`orbit-discovery` defines a provider-neutral async contract for finding remote service instances.
It is separate from Core's local service registry, which manages components inside one application.
This package has no provider SDK or network dependency; it supports Python 3.11 through 3.14 and is
pre-alpha.

```bash
python -m pip install orbit-discovery
```

## Provider and request behavior

The static implementation does not perform DNS lookups, health checks, load balancing, caching,
watching, or network requests. It returns candidates; the caller owns selection and connection
policy. The package includes no Consul, Kubernetes, DNS, or cloud registry adapter. Future adapters
must own their SDK, credentials, transport, refresh and shutdown behavior, and provider-specific
failures while implementing the same contract. Validate resolved endpoints against application
egress policy before making outbound requests; discovery data alone is not an SSRF defense.

## Production validation

Validate startup/shutdown cleanup, timeout and cancellation behavior, concurrency and payload bounds where applicable, secret rotation and least-privilege access, data durability, backup/restore, and failover against the selected provider. Do not infer distributed or durable guarantees from an in-process API or fake-client tests.
