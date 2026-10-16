# Architecture

## Contract boundary

`orbit-discovery` resolves remote service names into immutable endpoint candidates. It is distinct
from Core's local service registry, which manages components inside one process. The capability
defines validated `ServiceInstance` values and the async `ServiceDiscovery` protocol; it does not
choose an endpoint, open a socket, check health, balance traffic, or manage retry policy.

```text
application / caller → ServiceDiscovery.resolve(name) → endpoint candidates
       │                         ├── static map for tests/local configuration
       │                         ├── provider adapter with its own SDK and lifecycle
       │                         └── ProcessServiceDiscovery bridge
       │                                      └── Core owns and supervises plugin process
       └── validates egress policy, chooses endpoint, connects and retries
```

`DISCOVERY_DEPENDENCY_KEY` is the Core container registration key for an application-selected
provider. The capability has no Core import or runtime dependency. The optional `process` extra
uses Core's supervised process host but does not start a process itself.

## Endpoint values

`ServiceInstance` has a bounded ASCII service name and instance ID, a normalized DNS hostname or IP
literal, an HTTP(S) scheme, a valid port, a bounded weight, and a copied read-only metadata map.
IPv6 literals are bracketed in the `authority` and `base_url` properties. Metadata and host values
are omitted from normal representations. Metadata is for bounded non-secret labels, not credentials
or bearer tokens.

The map and returned tuples are immutable snapshots. DNS names are IDNA-normalized and lowercased;
IP addresses use canonical compressed form. `StaticServiceDiscovery` validates a bounded map once
at construction and returns the configured candidates as-is. It does not detect duplicate IPs,
refresh registrations, or remove unhealthy endpoints.

## Process contract

`proto/orbit_discovery/v1/service_discovery.proto` defines the versioned `Resolve` RPC and endpoint
fields shared with language-specific process plugins. Generated Python bindings are checked into
this package; `orbit-discovery-go` supplies Go bindings and provider SDK support separately.
`ProcessServiceDiscovery` converts a validated service name to a protobuf request, delegates to
Core's process invoker with a bounded deadline, and validates every returned endpoint through the
same `ServiceInstance` constructor.

Core owns process launch, configuration, one-use authentication, health, and process shutdown. The
bridge closes only its own acceptance of new calls. Shut down the bridge before the Core process
host, and follow the process-host documentation for the trusted local transport boundary.

## Extension boundaries

Provider adapters own registration sources, SDKs, credentials, watch/refresh loops, transport,
timeouts, errors, and client cleanup. Applications own endpoint selection, egress restrictions,
connection pools, health checks, and retries. No Consul, DNS, Kubernetes, or cloud adapter is
included in this Python checkout.
