"""Preparation/verification only: no command executes queries or model calls."""

from __future__ import annotations

import argparse
from pathlib import Path

from evaluation.artifacts import write_new_json
from evaluation.dataset import FrozenCollection
from evaluation.snapshot import ExperimentPreparer


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    subcommands = parser.add_subparsers(dest="command", required=True)
    prepare = subcommands.add_parser("prepare")
    prepare.add_argument("--root", type=Path, required=True)
    prepare.add_argument("--candidate", type=Path, required=True)
    prepare.add_argument("--output", type=Path, required=True)
    verify = subcommands.add_parser("verify")
    verify.add_argument("manifest", type=Path)
    arguments = parser.parse_args()
    if arguments.command == "verify":
        ExperimentPreparer.verify(arguments.manifest)
        print(
            "Offline snapshot, universe and input identities verified; no execution authorized."
        )
        return
    root = arguments.root.resolve()
    collection = FrozenCollection(
        root, root / "docs/evaluation/golden_set/frozen/v1/manifest.json"
    )
    manifest = ExperimentPreparer(collection, arguments.candidate.resolve()).prepare()
    write_new_json(arguments.output, manifest)
    print(
        f"Prepared {manifest['retrieval_plan']['queries']} retrieval jobs; zero executed. Fingerprint: {manifest['fingerprint_sha256']}"
    )


if __name__ == "__main__":
    main()
