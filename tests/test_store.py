import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from checkpoint_courier import Store
from checkpoint_courier import core


class StoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.source = self.root / "train.pt"
        self.data = bytes(range(256)) * 9000
        self.source.write_bytes(self.data)
        self.store = Store(self.root / "store")

    def test_round_trip_after_source_lost(self):
        saved = self.store.save(self.source, tag="epoch-15")
        self.source.unlink()
        restored = self.store.restore(saved["id"], self.root / "restored.pt")
        self.assertEqual(restored.read_bytes(), self.data)
        self.assertEqual(self.store.verify(saved["id"]), saved)

    def test_versions_do_not_overwrite(self):
        first = self.store.save(self.source)
        self.source.write_bytes(b"next")
        second = self.store.save(self.source)
        self.assertNotEqual(first["id"], second["id"])
        self.assertEqual(len(self.store.list()), 2)
        self.store.verify(first["id"])

    def test_empty_checkpoint(self):
        self.source.write_bytes(b"")
        saved = self.store.save(self.source)
        self.assertEqual(self.store.verify(saved["id"])["size_bytes"], 0)

    def test_corruption_rejected_and_partial_restore_removed(self):
        saved = self.store.save(self.source)
        payload = self.store.root / saved["id"] / "checkpoint.bin"
        with payload.open("r+b") as stream:
            stream.write(b"corrupt")
        with self.assertRaisesRegex(ValueError, "Checksum"):
            self.store.verify(saved["id"])
        target = self.root / "target.pt"
        with self.assertRaisesRegex(ValueError, "Checksum"):
            self.store.restore(saved["id"], target)
        self.assertFalse(target.exists())

    def test_existing_destination_untouched(self):
        saved = self.store.save(self.source)
        with self.assertRaises(FileExistsError):
            self.store.restore(saved["id"], self.source)
        self.assertEqual(self.source.read_bytes(), self.data)

    def test_unfinished_snapshot_not_listed(self):
        self.store.root.mkdir()
        (self.store.root / ".pending-interrupted").mkdir()
        self.assertEqual(self.store.list(), [])

    def test_interrupted_copy_not_published(self):
        with patch.object(core, "_copy_hash", side_effect=OSError("disk full")):
            with self.assertRaisesRegex(OSError, "disk full"):
                self.store.save(self.source)
        self.assertEqual(list(self.store.root.iterdir()), [])

    def test_concurrent_source_mutation_not_published(self):
        original = core._copy_hash

        def changing_copy(reader, writer=None):
            result = original(reader, writer)
            if writer is not None:
                with self.source.open("ab") as source:
                    source.write(b"changed")
            return result

        with patch.object(core, "_copy_hash", side_effect=changing_copy):
            with self.assertRaisesRegex(ValueError, "Source changed"):
                self.store.save(self.source)
        self.assertEqual(self.store.list(), [])

    def test_snapshot_path_traversal_rejected(self):
        for snapshot in ("../outside", "", "/tmp/file"):
            with self.subTest(snapshot=snapshot), self.assertRaises(ValueError):
                self.store.verify(snapshot)

    def test_invalid_manifest_reported(self):
        saved = self.store.save(self.source)
        manifest = self.store.root / saved["id"] / "manifest.json"
        manifest.write_text('[]', encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "manifest"):
            self.store.list()

    def test_cli_save_and_verify(self):
        args = [sys.executable, "-m", "checkpoint_courier"]
        result = subprocess.run(args + ["save", str(self.source), "--store", str(self.store.root)],
                                capture_output=True, text=True, check=True)
        saved = json.loads(result.stdout)
        result = subprocess.run(args + ["verify", saved["id"], "--store", str(self.store.root)],
                                capture_output=True, text=True, check=True)
        self.assertEqual(json.loads(result.stdout)["size_bytes"], len(self.data))


if __name__ == "__main__":
    unittest.main()
