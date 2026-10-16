# Orbit Discovery: development

This package declares support for `>=3.11,<3.15` in `pyproject.toml`. That declaration is distinct from evidence that hosted CI ran.

The full test suite covers the optional Core process bridge. From the package directory in the
Projects workspace, install Core's declared process extra and this package's development and
process extras before running the checks:

### Python package

```bash
python -m pip install -e '../orbit-core[process-plugins]' -e '.[dev,process]' build
python -m pytest -q
python -m ruff check src tests
python -m ruff format --check src tests
python -m mypy
python -m build
```

The development extra includes Protobuf typing stubs for the generated contract bindings. The
process extra installs the Protobuf runtime and Core bridge dependency; provider-neutral static
discovery does not require Core at runtime.

Optional SDKs and live-service tests are described by the package README. Do not run an opt-in live test against a shared or production service unless its own documentation explicitly supports that use.

## Contribution expectations

Add focused regression coverage for behavior changes. Update the README and relevant guide when a contract, configuration option, security property, lifecycle rule, or operational assumption changes. Report the exact versions and services exercised; local checks do not imply hosted CI or release validation.
