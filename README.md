# Checkpoint Courier

[![Tests](https://github.com/B-jack7/checkpoint-courier/actions/workflows/tests.yml/badge.svg)](https://github.com/B-jack7/checkpoint-courier/actions/workflows/tests.yml)
[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/B-jack7/checkpoint-courier/blob/main/notebooks/quickstart.ipynb)

**Keep verified copies of completed training checkpoints, then restore them without overwriting your files.**

[中文说明](README.zh-CN.md) · [CPU-only demo](examples/demo.py) · [Report a bug](https://github.com/B-jack7/checkpoint-courier/issues/new?template=bug_report.yml)

Training sessions can end before you expect. This small Python tool copies an already-saved checkpoint to a directory you choose, records its SHA-256 digest, and verifies it before considering the backup complete. It uses **only the Python standard library** and never loads model objects.

## Try it in one minute

Requires Python 3.10+. No GPU, account, or dataset is needed for the demo.

```bash
git clone https://github.com/B-jack7/checkpoint-courier.git
cd checkpoint-courier
python -m pip install .
python examples/demo.py
```

The demo creates dummy checkpoint bytes, backs them up, deletes the original, and restores a verified copy. These are synthetic bytes, not model weights or a training benchmark. The Colab button runs the same idea in a temporary directory and needs no Drive authorization.

## Back up a real file

```bash
checkpoint-courier save epoch-15.pt --store ./backups --tag epoch-15
checkpoint-courier list --store ./backups
checkpoint-courier verify SNAPSHOT_ID --store ./backups
checkpoint-courier restore SNAPSHOT_ID recovered.pt --store ./backups
```

Replace `SNAPSHOT_ID` with the `id` returned by `save`. Successful commands print JSON; failures return exit code 1 (`argparse` usage errors return 2). `python -m checkpoint_courier` is equivalent to the installed command.

## Use with a training loop

```python
from checkpoint_courier import Store

store = Store("/content/drive/MyDrive/my-training-backups")

# After your framework has FINISHED writing a checkpoint:
snapshot = store.save("/content/epoch-15.pt", tag="epoch-15")
print(snapshot["id"], snapshot["sha256"])

# In a later session, after mounting the same storage:
store.restore(snapshot["id"], "/content/recovered.pt")
```

In Colab, mount Drive yourself using `from google.colab import drive; drive.mount('/content/drive')` before using a Drive path. In your own epoch loop, a condition such as `if epoch % 15 == 0 or epoch == 50:` can trigger a framework save followed by `store.save(...)`. `epoch` here is one-based. Schedule backups as frequently as your storage and recovery needs allow.

Save the model, optimizer, epoch, scheduler, and random-generator state in your framework checkpoint when needed. This package copies **one file**; it does not reconstruct missing training state or resume the training code for you. See the [PyTorch checkpoint guide](https://docs.pytorch.org/tutorials/beginner/saving_loading_models.html#saving-loading-a-general-checkpoint-for-inference-and-or-resuming-training).

## What is checked?

| Situation | Behavior |
|---|---|
| Repeated saves of the same filename | Each gets a unique snapshot ID; previous versions stay |
| Ordinary source changes during copying | Rejects the save using file identity, size and modification time |
| Interrupted save | Unfinished `.pending-*` directories are ignored by `list` |
| Truncated or corrupted backup | `verify` / `restore` fails the size or SHA-256 check |
| Existing restore destination | Fails without overwriting it |
| Large checkpoint | Reads in 1 MiB chunks; never deserializes the model |

```text
backups/
  20260925T120000Z-<unique-id>/
    checkpoint.bin
    manifest.json
```

`list` reads manifests only. Use `verify` to check the actual bytes. Tags are descriptive, not paths. The manifest stores the source basename, size, tag, time, and digest, not its absolute path.

## Limits to understand

- **v0.1 is an early release.** Automated tests cover local filesystem behavior; live Google Drive durability and large-scale training have not been validated.
- Keep the source unchanged during `save`. Metadata checks are not a substitute for a filesystem snapshot or coordinating with the writer.
- Directory rename publishes a completed backup on local filesystems. A cloud-mounted filesystem may provide different consistency guarantees. Successful local verification is **not proof of remote synchronization**; reconnect and verify the persisted backup before relying on it.
- No background scheduling, retention deletion, encryption, compression, distributed checkpoints, or cloud API is included. Storage use grows with each save. A backup under Colab's temporary `/content` is lost with that runtime.
- Restore destinations must have an existing parent directory. Wait for `restore` to return before reading the file. A hard process termination during restore may leave a partial destination; inspect it and retry to a new path.
- SHA-256 detects corruption relative to the manifest. It does not authenticate a maliciously replaced checkpoint and manifest. Load only model files you trust.

## Development

```bash
python -m pip install -e .
python -m unittest discover -s tests -v
```

CI runs the tests and CPU demo on Windows and Ubuntu with Python 3.10 and 3.12. See [CONTRIBUTING.md](CONTRIBUTING.md) for small, reproducible contributions. The initial implementation was developed with AI assistance and is backed by executable tests; external audits and production adoption are not claimed.

## Roadmap

- [ ] Test mounted-Drive failures and recovery on a real Colab session.
- [ ] Optional dry-run retention planning before any deletion feature.
- [ ] Framework-specific examples driven by actual user needs.

MIT licensed. If you try it, a minimal bug report or tested example is especially useful.
