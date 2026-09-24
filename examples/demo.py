"""A deterministic CPU-only demonstration using dummy checkpoint bytes."""

from pathlib import Path
from tempfile import TemporaryDirectory

from checkpoint_courier import Store

with TemporaryDirectory() as directory:
    root = Path(directory)
    source = root / "epoch-15.ckpt"
    source.write_bytes(b"example checkpoint bytes\n" * 4096)
    store = Store(root / "backups")
    saved = store.save(source, tag="epoch-15")
    source.unlink()  # Simulate losing the original local checkpoint.
    restored = store.restore(saved["id"], root / "recovered.ckpt")
    print("Saved:", saved["id"])
    print("SHA-256:", store.verify(saved["id"])["sha256"])
    print("Recovered bytes:", restored.stat().st_size)
