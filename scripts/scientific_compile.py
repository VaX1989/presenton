#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Sequence


def _json_request(
    url: str,
    *,
    method: str = "GET",
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    data = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=900) as response:
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


def _strict_generate(
    *,
    api: str,
    master: Path,
    theme: str,
    slide_ids: Sequence[int],
    dark_slide_ids: Sequence[int],
    title: str | None,
    language: str,
    persist: bool,
) -> dict[str, Any]:
    payload = {
        "mode": "strict_materialize",
        "theme": theme,
        "master_markdown": master.read_text(encoding="utf-8"),
        "source_file": str(master),
        "slide_ids": list(slide_ids) or None,
        "dark_slide_ids": list(dark_slide_ids),
        "title": title,
        "language": language,
        "persist": persist,
    }
    return _json_request(
        f"{api.rstrip('/')}/api/v1/ppt/scientific/generate",
        method="POST",
        payload=payload,
    )


def _compile_one(
    args: argparse.Namespace,
    master: Path,
    out: Path,
) -> dict[str, Any]:
    generated = _strict_generate(
        api=args.api,
        master=master,
        theme=args.theme,
        slide_ids=args.slide_id,
        dark_slide_ids=args.dark_slide_id,
        title=args.title,
        language=args.language,
        persist=not args.no_persist,
    )
    out.mkdir(parents=True, exist_ok=True)
    (out / "generation.json").write_text(
        json.dumps(generated, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    slide_count = len(generated.get("slides", [])) or len(
        generated.get("source_hashes", {})
    )
    if generated.get("content_lock_status") != "PASS":
        raise SystemExit(f"strict materialization failed for {master}")

    presentation_id = generated.get("presentation_id")
    result: dict[str, Any] = {
        "master": str(master),
        "slides": slide_count,
        "presentation_id": presentation_id,
        "content_lock_status": generated.get("content_lock_status"),
        "render_contract": generated.get("render_contract"),
        "exports": {},
    }
    print(f"strict materialization: PASS master={master.name} slides={slide_count}")
    if not presentation_id or args.no_persist:
        return result

    exports: dict[str, Any] = {}
    for fmt in args.export:
        response = _json_request(
            f"{args.api.rstrip('/')}/api/v1/ppt/presentation/{presentation_id}/export",
            method="POST",
            payload={"export_as": fmt},
        )
        basename = f"presentation.{fmt}"
        response["local_copy"] = _copy_export(
            str(response.get("path", "")),
            out / basename,
        )
        exports[fmt] = response
        print(f"{master.name} {fmt}: {response.get('path')}")
    (out / "exports.json").write_text(
        json.dumps(exports, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    result["exports"] = exports
    return result


def _discover_all(args: argparse.Namespace) -> list[Path]:
    root = Path(args.masters_root).resolve()
    if not root.exists():
        raise SystemExit(f"masters root not found: {root}")
    masters = sorted(path.resolve() for path in root.glob(args.master_glob) if path.is_file())
    if not masters:
        raise SystemExit(
            f"no masters matched {args.master_glob!r} under {root}"
        )
    return masters


def compile_command(args: argparse.Namespace) -> int:
    if args.all:
        if args.master:
            raise SystemExit("do not provide a positional master together with --all")
        masters = _discover_all(args)
    else:
        if not args.master:
            raise SystemExit("compile requires MASTER or --all")
        master = Path(args.master).resolve()
        if not master.exists():
            raise SystemExit(f"master not found: {master}")
        masters = [master]

    root_out = Path(args.out).resolve()
    results: list[dict[str, Any]] = []
    for index, master in enumerate(masters, 1):
        target = root_out if len(masters) == 1 else root_out / f"{index:02d}_{master.stem}"
        results.append(_compile_one(args, master, target))

    total_slides = sum(int(result["slides"]) for result in results)
    if args.expect_total is not None and total_slides != args.expect_total:
        raise SystemExit(
            f"compiled slide total {total_slides} != expected {args.expect_total}"
        )
    summary = {
        "status": "PASS",
        "masters": len(results),
        "slides": total_slides,
        "results": results,
    }
    root_out.mkdir(parents=True, exist_ok=True)
    (root_out / "scientific_compile_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps({"status": "PASS", "masters": len(results), "slides": total_slides}, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Presenton Scientific Slide Engine client")
    parser.add_argument(
        "--api",
        default="http://127.0.0.1:8000",
        help="Presenton FastAPI base URL",
    )
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("capabilities")
    compile_p = sub.add_parser("compile")
    compile_p.add_argument("master", nargs="?")
    compile_p.add_argument(
        "--all",
        action="store_true",
        help="compile every master matched under --masters-root",
    )
    compile_p.add_argument("--masters-root", default=".")
    compile_p.add_argument(
        "--master-glob",
        default="**/DECK_*_SLIDE_SPEC_MASTER_FINAL.md",
    )
    compile_p.add_argument(
        "--expect-total",
        type=int,
        help="fail unless all compiled masters contain exactly this many slides",
    )
    compile_p.add_argument("--theme", default="scientific-editorial")
    compile_p.add_argument("--slide-id", type=int, action="append", default=[])
    compile_p.add_argument("--dark-slide-id", type=int, action="append", default=[])
    compile_p.add_argument("--title")
    compile_p.add_argument("--language", default="it")
    compile_p.add_argument("--out", default="artifacts/scientific-compile")
    compile_p.add_argument("--no-persist", action="store_true")
    compile_p.add_argument(
        "--export",
        nargs="+",
        choices=["pptx", "pdf"],
        default=["pptx", "pdf"],
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if args.command == "capabilities":
        return capabilities(args.api)
    return compile_command(args)


if __name__ == "__main__":
    raise SystemExit(main())
