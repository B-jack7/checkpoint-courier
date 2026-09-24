"""Command-line interface; successful output is JSON."""

import argparse
import json
import sys

from .core import Store


def main(argv=None):
    parser = argparse.ArgumentParser(description="Copy, verify, and restore completed checkpoints")
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("save", "list", "verify", "restore"):
        command = sub.add_parser(name)
        command.add_argument("--store", required=True)
        if name == "save":
            command.add_argument("source")
            command.add_argument("--tag", default="")
        if name in ("verify", "restore"):
            command.add_argument("snapshot_id")
        if name == "restore":
            command.add_argument("destination")
    args = parser.parse_args(argv)
    store = Store(args.store)
    try:
        if args.command == "save":
            result = store.save(args.source, tag=args.tag)
        elif args.command == "list":
            result = store.list()
        elif args.command == "verify":
            result = store.verify(args.snapshot_id)
        else:
            result = {"restored": str(store.restore(args.snapshot_id, args.destination))}
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0
    except (OSError, ValueError) as error:
        print(f"checkpoint-courier: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
