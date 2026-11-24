"""Verify the migration inventory after Git clone or ZIP extraction."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    manifest = json.loads((root / "evidence/delivery/migration-inventory.json").read_text(encoding="utf-8"))
    failures = []
    for item in manifest["files"]:
        path = root / item["path"]
        if not path.is_file():
            failures.append({"path": item["path"], "error": "missing"})
        elif hashlib.sha256(path.read_bytes()).hexdigest() != item["sha256"]:
            failures.append({"path": item["path"], "error": "sha256 mismatch"})
    print(json.dumps({"checked": len(manifest["files"]), "failures": failures}, ensure_ascii=False, indent=2))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
