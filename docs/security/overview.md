# Security

## Endpoints are untrusted input

Service discovery provides candidate network locations, not authorization to connect. A malicious
or compromised registry can return loopback, link-local, private, metadata-service, or otherwise
restricted destinations. Apply explicit egress rules before connecting, resolve and validate DNS
answers according to application policy, and re-check destinations across redirects. Do not use
discovery results alone to authorize outbound requests or as an SSRF defense.

The value model accepts HTTP and HTTPS origins and normalizes hostnames and IP literals. It does
not define an application's allowed networks, ports, DNS resolution rules, certificate policy, or
redirect behavior.

## Metadata and identifiers

Host, metadata, service IDs, and instance IDs are omitted from the normal endpoint representation
where they can disclose internal topology. This reduces accidental exposure but does not sanitize
explicit serialization, logs, traces, memory dumps, or provider diagnostics. Never put credentials,
bearer tokens, private keys, or secret query values in endpoint metadata. Restrict who can write
registrations and who can resolve them.

Metadata has bounded entry count, text length, and encoded size. These are resource limits, not a
confidentiality guarantee. Avoid storing personal or sensitive application data there.

## Process boundary

The optional process bridge relies on Core's supervised process host for process authentication,
configuration, health, and shutdown. The protocol's local plaintext transport assumes trusted local
plugins and is not a sandbox. Do not run untrusted plugin code in the same trust boundary; isolate
it with operating-system or container controls and restrict its network and filesystem access.

## Vulnerability reporting

Follow the repository [security policy](../../SECURITY.md) for private vulnerability reports.
