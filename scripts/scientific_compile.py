#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any


def _json_request(url: str, *, method: str = "GET", payload: dict[str, Any] | None = None) -> dict[str, Any]:
    data = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(request) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", "replace")
        raise SystemExit(f"HTTP {exc.code} {url}: {body}") from exc


def _copy_export(path_value: str, destination: Path) -> str:
    source = Path(path_value)
    if source.exists():
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        return str(destination)
    return path_value


def capabilities(api: str) -> int:
    caps = _json_request(f"{api.rstrip('/')}/api/v1/ppt/scientific/capabilities")
    print(json.dumps(caps, ensure_ascii=False, indent=2))
    return 0


def compile_master(args: argparse.Namespace) -> int:
    master = Path(args.master).resolve()
    if not master.exists():
        raise SystemExit(f"master not found: {master}")
    payload = {
        "mode": "strict_materialize",
        "theme": args.theme,
        "master_markdown": master.read_text(encoding="utf-8"),
        "source_file": str(master),
        "slide_ids": args.slide_id or None,
        "dark_slide_ids": args.dark_slide_id or [],
        "title": args.title,
        "language": args.language,
        "persist": not args.no_persist,
    }
    base = args.api.rstrip("/")
    generated = _json_request(f"{base}/api/v1/ppt/scientific/generate", method="POST", payload=payload)
    out = Path(args.out).resolve(); out.mkdir(parents=True, exist_ok=True)
    (out / "generation.json").write_text(json.dumps(generated, ensure_ascii=False, indent=2), encoding="utf-8")
    presentation_id = generated.get("presentation_id")
    print(f"strict materialization: {generated.get('content_lock_status')} slides={len(generated.get('slides', [])) or len(generated.get('source_hashes', {}))}")
    if not presentation_id or args.no_persist:
        return 0
    exports: dict[str, Any] = {}
    for fmt in args.export:
        response = _json_request(
            f"{base}/api/v1/ppt/presentation/{presentation_id}/export",
            method="POST",
            payload={"export_as": fmt},
        )
        basename = f"presentation.{fmt}"
        response["local_copy"] = _copy_export(str(response.get("path", "")), out / basename)
        exports[fmt] = response
        print(f"{fmt}: {response.get('path')}")
    (out / "exports.json").write_text(json.dumps(exports, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Presenton Scientific Slide Engine client")
    parser.add_argument("--api", default="http://127.0.0.1:8000", help="Presenton FastAPI base URL")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("capabilities")
    compile_p = sub.add_parser("compile")
    compile_p.add_argument("master")
    compile_p.add_argument("--theme", default="scientific-editorial")
    compile_p.add_argument("--slide-id", type=int, action="append", default=[])
    compile_p.add_argument("--dark-slide-id", type=int, action="append", default=[])
    compile_p.add_argument("--title")
    compile_p.add_argument("--language", default="it")
    compile_p.add_argument("--out", default="artifacts/scientific-compile")
    compile_p.add_argument("--no-persist", action="store_true")
    compile_p.add_argument("--export", nargs="+", choices=["pptx", "pdf"], default=["pptx", "pdf"])
    return parser


def main() -> int:
    parser = build_parser(); args = parser.parse_args()
    if args.command == "capabilities":
        return capabilities(args.api)
    return compile_master(args)


if __name__ == "__main__":
    raise SystemExit(main())
