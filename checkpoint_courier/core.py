"""A small, append-only store for opaque checkpoint files."""

import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import tempfile
from datetime import datetime, timezone
from uuid import uuid4

CHUNK_SIZE = 1024 * 1024
SNAPSHOT_ID = re.compile(r"\d{8}T\d{6}Z-[0-9a-f]{32}\Z")


def _copy_hash(source, target=None):
    digest = hashlib.sha256()
    size = 0
    while chunk := source.read(CHUNK_SIZE):
        if target is not None:
            target.write(chunk)
        digest.update(chunk)
        size += len(chunk)
    return size, digest.hexdigest()


def _signature(stat):
    # Windows stat/fstat may expose different ctime semantics. Use identity,
    # length and modification time consistently on both platforms.
    return stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns


class Store:
    """Save completed files; call from your training loop after torch.save returns.

    A completed local copy does not guarantee remote cloud synchronization.
    """

    def __init__(self, root):
        self.root = Path(root)

    def save(self, source, *, tag=""):
        """Copy and verify a stable file, then publish its unique snapshot ID.

        Do not modify source during this call. Metadata checks detect ordinary
        concurrent writes, but cannot provide a filesystem snapshot of a writer.
        """
        source = Path(source)
        if not source.is_file():
            raise ValueError(f"Not a regular file: {source}")
        if not isinstance(tag, str):
            raise ValueError("tag must be a string")
        self.root.mkdir(parents=True, exist_ok=True)
        now = datetime.now(timezone.utc)
        snapshot_id = now.strftime("%Y%m%dT%H%M%SZ-") + uuid4().hex
        staging = Path(tempfile.mkdtemp(prefix=".pending-", dir=self.root))
        try:
            with source.open("rb") as reader, (staging / "checkpoint.bin").open("xb") as writer:
                before = _signature(os.fstat(reader.fileno()))
                size, digest = _copy_hash(reader, writer)
                writer.flush()
                os.fsync(writer.fileno())
                after = _signature(os.fstat(reader.fileno()))
            if before != after or before != _signature(source.stat()):
                raise ValueError("Source changed while copying; save a completed checkpoint first")
            with (staging / "checkpoint.bin").open("rb") as reader:
                if _copy_hash(reader) != (size, digest):
                    raise ValueError("Backup verification failed")
            manifest = {
                "schema_version": 1,
                "id": snapshot_id,
                "created_at": now.isoformat(),
                "source_name": source.name,
                "tag": tag,
                "size_bytes": size,
                "sha256": digest,
            }
            with (staging / "manifest.json").open("x", encoding="utf-8") as writer:
                json.dump(manifest, writer, indent=2, ensure_ascii=False)
                writer.write("\n")
                writer.flush()
                os.fsync(writer.fileno())
            staging.rename(self.root / snapshot_id)
            return manifest
        finally:
            if staging.exists():
                shutil.rmtree(staging)

    def _manifest(self, snapshot_id):
        if not isinstance(snapshot_id, str) or not SNAPSHOT_ID.fullmatch(snapshot_id):
            raise ValueError("Invalid snapshot ID")
        folder = self.root / snapshot_id
        if folder.is_symlink():
            raise ValueError("Snapshot directories must not be symbolic links")
        manifest_path = folder / "manifest.json"
        payload = folder / "checkpoint.bin"
        if manifest_path.is_symlink() or payload.is_symlink():
            raise ValueError("Snapshot files must not be symbolic links")
        with manifest_path.open(encoding="utf-8") as reader:
            manifest = json.load(reader)
        if (not isinstance(manifest, dict)
                or manifest.get("schema_version") != 1
                or manifest.get("id") != snapshot_id
                or type(manifest.get("size_bytes")) is not int
                or manifest["size_bytes"] < 0
                or not isinstance(manifest.get("sha256"), str)
                or not re.fullmatch(r"[0-9a-f]{64}", manifest["sha256"])):
            raise ValueError(f"Invalid manifest: {snapshot_id}")
        return manifest, payload

    def list(self):
        """List manifests, not verified payloads. Ignore unfinished staging dirs.

        Malformed published snapshots raise instead of disappearing silently.
        """
        if not self.root.exists():
            return []
        return [self._manifest(p.name)[0] for p in sorted(self.root.iterdir())
                if SNAPSHOT_ID.fullmatch(p.name)]

    def verify(self, snapshot_id):
        """Read the full backup and check its size and SHA-256 digest."""
        manifest, payload = self._manifest(snapshot_id)
        with payload.open("rb") as reader:
            actual = _copy_hash(reader)
        if actual != (manifest["size_bytes"], manifest["sha256"]):
            raise ValueError(f"Checksum mismatch: {snapshot_id}")
        return manifest

    def restore(self, snapshot_id, destination):
        """Copy to a NEW path, verify the result, and never overwrite a file.

        Consumers must wait for this call to return. A hard process termination
        may leave a partial destination; retry with a new path after checking it.
        """
        manifest, payload = self._manifest(snapshot_id)
        destination = Path(destination)
        # Open exclusively outside the cleanup block: an existing file is never removed.
        writer = destination.open("xb")
        try:
            with writer, payload.open("rb") as reader:
                actual = _copy_hash(reader, writer)
                writer.flush()
                os.fsync(writer.fileno())
            if actual != (manifest["size_bytes"], manifest["sha256"]):
                raise ValueError(f"Checksum mismatch: {snapshot_id}")
            with destination.open("rb") as reader:
                if _copy_hash(reader) != actual:
                    raise ValueError("Restored file verification failed")
        except BaseException:
            writer.close()
            destination.unlink(missing_ok=True)
            raise
        return destination
