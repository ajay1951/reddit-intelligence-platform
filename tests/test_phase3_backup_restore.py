from __future__ import annotations

import json
from pathlib import Path
import pytest

from scripts.backup import create_backup
from scripts.restore import restore_backup


def test_backup_and_dry_run_restore_lifecycle(tmp_path: Path):
    backup_output_dir = tmp_path / "backups"
    created_bundle_path = create_backup(output_base=backup_output_dir)

    assert created_bundle_path.exists()
    manifest_path = created_bundle_path / "metadata.json"
    assert manifest_path.exists()

    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    assert "timestamp_utc" in manifest
    assert "files" in manifest
    assert "database_export" in manifest["files"]

    # Perform dry-run restore validation
    res = restore_backup(created_bundle_path, dry_run=True)
    assert res["status"] == "dry_run_success"
    assert "manifest" in res


def test_restore_detects_tampered_backup(tmp_path: Path):
    backup_output_dir = tmp_path / "backups"
    created_bundle_path = create_backup(output_base=backup_output_dir)

    # Tamper with the database export file
    db_file = created_bundle_path / "database_export.json"
    with open(db_file, "a", encoding="utf-8") as f:
        f.write("\n// tampered extra bytes")

    # Dry-run restore must detect checksum corruption and raise ValueError
    with pytest.raises(ValueError, match="Checksum mismatch"):
        restore_backup(created_bundle_path, dry_run=True)
