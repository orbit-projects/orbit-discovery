# Operations

`ServiceDiscovery.resolve(name)` returns candidates. The application owns endpoint selection,
connection creation, retries, health checks, and the decision to refresh or replace a candidate.
The contract does not say that an endpoint is reachable, healthy, or still registered when used.

## Static development resolver

`StaticServiceDiscovery` is an immutable bounded map intended for deterministic development and
tests. It performs no DNS lookup, registration refresh, health probe, or load balancing. Configure
it from trusted application settings, and close it with `aclose()` or its async context manager.
Unknown service names return an empty tuple. Invalid names fail validation.

## Provider adapters

A live provider adapter should define its source of truth, update/refresh behavior, staleness,
consistency, timeouts, retry/backoff rules, health semantics, and lifecycle. It must bound returned
instance counts and metadata and translate expected provider failures to `DiscoveryError` without
including credentials or raw provider responses. Propagate `asyncio.CancelledError` unchanged.

Register the selected implementation in the application's Core dependency container under
`DISCOVERY_DEPENDENCY_KEY` when using Core integration. Do not rely on implicit provider discovery
or install multiple competing implementations under the same key.

## Process providers

Install `orbit-discovery[process]` to use `ProcessServiceDiscovery` with a Core-supervised process
host. The bridge uses the versioned `orbit.discovery.v1.ServiceDiscovery/Resolve` method and
enforces a per-call request deadline. Core owns process startup, configuration, authentication,
health, and process shutdown. Close the bridge before its process host; the bridge does not close
the host. The documented local process protocol is for trusted local plugins and does not sandbox
provider code.

The protobuf response is validated into bounded `ServiceInstance` objects. Invalid fields or
provider errors fail the resolution instead of returning partially trusted endpoint data.

## Endpoint selection and egress

Do not connect to a resolved host solely because discovery returned it. Apply application egress
policy, allowed scheme/port rules, destination network restrictions, and any DNS resolution policy
before making outbound requests. Re-check policy after DNS resolution and redirects where
appropriate; discovery data is not an SSRF defense. A weight is provider metadata for the caller's
selection algorithm and the capability does not prescribe weighted round robin.

## Validation before rollout

Test empty results, duplicate IDs, stale registrations, provider outages, timeout and cancellation,
host normalization, DNS changes, endpoint policy rejection, connection retry behavior, and
shutdown ordering. Use non-production provider scopes and credentials. Static map and fake-process
tests do not establish live registry or network behavior.
