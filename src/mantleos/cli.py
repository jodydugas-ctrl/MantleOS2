from __future__ import annotations

import argparse
import json
from pathlib import Path

from . import __version__
from .assimilate import AssimilationError, assimilate_github
from .runtime import MantleBody, MantleError


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="mantle", description="MantleOS 2 Body controls")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("--nest", default=".", help="NEST root (defaults to the current directory)")
    commands = parser.add_subparsers(dest="command", required=True)

    assimilate = commands.add_parser("assimilate", help="Construct an un-born Body around a GitHub NEST")
    assimilate.add_argument("source", help="GitHub owner/repository or URL")
    assimilate.add_argument("--destination", help="Clone destination (defaults to the repository name)")
    assimilate.add_argument("--ref", help="Branch or tag to clone")

    commands.add_parser("status", help="Show construction or organism status")
    birth = commands.add_parser("birth", help="Run the separately approved first Heartbeat")
    birth.add_argument("--name", required=True, help="Confirmed organism identity name")
    birth.add_argument(
        "--approve-birth",
        action="store_true",
        help="Record explicit approval of the birth gate",
    )
    heartbeat = commands.add_parser("heartbeat", help="Run one complete Heartbeat")
    heartbeat.add_argument("--reason", default="manual")
    watch = commands.add_parser("watch", help="Watch COMMUNICATION.TXT and wake on save")
    watch.add_argument("--interval", type=float, default=1.0)
    digest = commands.add_parser("digest", help="Securely store and verify a Food delivery")
    digest.add_argument("path", help="Path to the Food file")
    digest.add_argument("--retry", action="store_true", help="Retry an already recorded delivery")
    commands.add_parser("verify", help="Verify the append-only VCW chains")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "assimilate":
            result = assimilate_github(args.source, destination=args.destination, ref=args.ref)
        else:
            body = MantleBody(Path(args.nest))
            if args.command == "status":
                result = body.status()
            elif args.command == "birth":
                result = body.birth(args.name, approved=args.approve_birth)
            elif args.command == "heartbeat":
                result = body.heartbeat(reason=args.reason)
            elif args.command == "verify":
                result = body.verify()
            elif args.command == "digest":
                result = body.digest_food(args.path, retry=args.retry)
            else:
                body.watch(interval=args.interval)
                return 0
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0
    except (AssimilationError, MantleError, OSError, ValueError) as exc:
        print(f"Mantle stopped: {exc}")
        return 2
