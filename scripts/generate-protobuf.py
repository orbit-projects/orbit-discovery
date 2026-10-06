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
"""Regenerate checked-in Python message and typing bindings."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROTO = ROOT / "proto/orbit_discovery/v1/service_discovery.proto"
SOURCE = ROOT / "src"
OUTPUTS = (
    SOURCE / "orbit_discovery/v1/service_discovery_pb2.py",
    SOURCE / "orbit_discovery/v1/service_discovery_pb2.pyi",
)
LICENSE = """# Copyright 2026-present Orbit Contributors.
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
"""


def main() -> int:
    """Compile Python Protobuf bindings and type stubs from the public capability schema."""
    subprocess.run(
        [
            sys.executable,
            "-m",
            "grpc_tools.protoc",
            "-I",
            str(ROOT / "proto"),
            "--python_out=" + str(SOURCE),
            "--mypy_out=" + str(SOURCE),
            str(PROTO),
        ],
        cwd=ROOT,
        env={
            **os.environ,
            "PATH": os.pathsep.join((str(Path(sys.executable).parent), os.environ.get("PATH", ""))),
        },
        check=True,
    )
    for path in OUTPUTS:
        text = path.read_text(encoding="utf-8")
        if "Licensed under the Apache License" not in text[:1024]:
            path.write_text(LICENSE + text, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
