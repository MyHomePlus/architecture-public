#!/usr/bin/env python3
"""Render MyHomePlus PlantUML diagrams.

Two backends:

* ``kroki`` (default) — POST the PlantUML source to a Kroki server.  Local
  ``!include`` directives are flattened first because Kroki cannot see this
  checkout.  No Java required.
* ``local`` — call a PlantUML jar / binary.  Requires Java and a jar.

Examples::

    python3 scripts/render.py                 # render SVG + PNG into build/
    python3 scripts/render.py --check         # render SVG only, no build output
    python3 scripts/render.py --only 02      # diagram filename substring filter
    PLANTUML_JAR=/path/plantuml.jar python3 scripts/render.py --backend local

The source of truth is always the ``.puml`` file; ``build/`` is disposable.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIAGRAM_DIR = ROOT / "diagrams"
BUILD_DIR = ROOT / "build"

INCLUDE_RE = re.compile(r"^\s*!include\s+(.+?)\s*$")
REMOTE_INCLUDE_RE = re.compile(r"^<.+>$")


@dataclass(frozen=True)
class Diagram:
    source: Path
    name: str


class RenderError(RuntimeError):
    pass


def discover(only: str | None) -> list[Diagram]:
    files = sorted(p for p in DIAGRAM_DIR.glob("*.puml") if p.is_file())
    if only:
        files = [p for p in files if only in p.name]
    if not files:
        raise RenderError(f"no .puml files found under {DIAGRAM_DIR}")
    return [Diagram(source=p, name=p.stem) for p in files]


def flatten_includes(path: Path, seen: tuple[Path, ...] = ()) -> str:
    """Expand local !include directives recursively.

    Only relative/absolute file includes are supported.  Remote includes are
    rejected on purpose: architecture sources must render offline and must not
    depend on a Git branch moving under our feet.
    """
    resolved = path.resolve()
    if resolved in seen:
        chain = " -> ".join(str(p) for p in (*seen, resolved))
        raise RenderError(f"circular !include: {chain}")

    lines: list[str] = []
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        match = INCLUDE_RE.match(line)
        if not match:
            lines.append(line)
            continue

        target = match.group(1).strip().strip('"')
        if REMOTE_INCLUDE_RE.match(target) or "://" in target:
            raise RenderError(
                f"{path}:{lineno}: remote includes are not allowed: {target}"
            )
        include_path = (path.parent / target).resolve()
        if not include_path.is_file():
            raise RenderError(f"{path}:{lineno}: include not found: {include_path}")
        lines.append(f"' >>> include: {target}")
        lines.append(flatten_includes(include_path, (*seen, resolved)))
        lines.append(f"' <<< include: {target}")
    return "\n".join(lines)


def post_kroki(source: str, fmt: str, base_url: str, timeout: float) -> bytes:
    url = f"{base_url.rstrip('/')}/plantuml/{fmt}"
    request = urllib.request.Request(
        url,
        data=source.encode("utf-8"),
        headers={
            "Content-Type": "text/plain; charset=utf-8",
            "User-Agent": "myhomeplus-architecture-render/1.0",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.read()
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace").strip()
        raise RenderError(f"Kroki HTTP {exc.code}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise RenderError(f"Kroki request failed: {exc.reason}") from exc


def render_with_kroki(
    diagrams: list[Diagram], base_url: str, timeout: float, check: bool
) -> list[dict[str, object]]:
    results: list[dict[str, object]] = []
    jobs: list[tuple[Diagram, str]] = []
    for diagram in diagrams:
        formats = ("svg",) if check else ("svg", "png")
        jobs.extend((diagram, fmt) for fmt in formats)

    def run(job: tuple[Diagram, str]) -> tuple[Diagram, str, bytes]:
        diagram, fmt = job
        flattened = flatten_includes(diagram.source)
        if "@startuml" not in flattened or "@enduml" not in flattened:
            raise RenderError(f"{diagram.source.name}: missing @startuml/@enduml")
        return diagram, fmt, post_kroki(flattened, fmt, base_url, timeout)

    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        futures = {pool.submit(run, job): job for job in jobs}
        for future in concurrent.futures.as_completed(futures):
            diagram, fmt, payload = future.result()
            if check:
                results.append({"name": diagram.name, "format": fmt, "bytes": len(payload)})
                continue
            target = BUILD_DIR / f"{diagram.name}.{fmt}"
            target.write_bytes(payload)
            results.append(
                {
                    "name": diagram.name,
                    "format": fmt,
                    "bytes": len(payload),
                    "path": str(target.relative_to(ROOT)),
                }
            )
    return results


def render_with_local(
    diagrams: list[Diagram], jar: str, check: bool
) -> list[dict[str, object]]:
    java = shutil.which("java")
    if not java:
        raise RenderError("--backend local requires a Java runtime on PATH")
    results: list[dict[str, object]] = []
    out_dir = Path(tempfile.mkdtemp(prefix="myhomeplus-puml-")) if check else BUILD_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    try:
        for diagram in diagrams:
            formats = ("svg",) if check else ("svg", "png")
            for fmt in formats:
                command = [
                    java,
                    "-Djava.awt.headless=true",
                    "-jar",
                    jar,
                    "-charset",
                    "UTF-8",
                    f"-t{fmt}",
                    "-o",
                    str(out_dir),
                    str(diagram.source),
                ]
                completed = subprocess.run(command, capture_output=True, text=True)
                if completed.returncode != 0:
                    raise RenderError(
                        f"{diagram.source.name} ({fmt}): {completed.stderr.strip()}"
                    )
                target = out_dir / f"{diagram.name}.{fmt}"
                if not target.is_file():
                    raise RenderError(f"{diagram.source.name}: output not produced")
                results.append(
                    {
                        "name": diagram.name,
                        "format": fmt,
                        "bytes": target.stat().st_size,
                        **({} if check else {"path": str(target.relative_to(ROOT))}),
                    }
                )
    finally:
        if check:
            shutil.rmtree(out_dir, ignore_errors=True)
    return results


def write_manifest(diagrams: list[Diagram], results: list[dict[str, object]]) -> None:
    rendered = {
        (item["name"], item["format"]): item for item in results if "path" in item
    }
    entries = []
    for diagram in diagrams:
        source_bytes = diagram.source.read_bytes()
        entries.append(
            {
                "name": diagram.name,
                "source": str(diagram.source.relative_to(ROOT)),
                "sha256": hashlib.sha256(source_bytes).hexdigest(),
                "svg": rendered.get((diagram.name, "svg"), {}).get("path"),
                "png": rendered.get((diagram.name, "png"), {}).get("path"),
            }
        )
    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "count": len(entries),
        "diagrams": entries,
    }
    (BUILD_DIR / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--backend",
        choices=("kroki", "local"),
        default=os.environ.get("PLANTUML_BACKEND", "kroki"),
        help="render backend (default: kroki)",
    )
    parser.add_argument(
        "--kroki-url",
        default=os.environ.get("KROKI_URL", "https://kroki.io"),
        help="Kroki base URL",
    )
    parser.add_argument(
        "--jar",
        default=os.environ.get("PLANTUML_JAR", ""),
        help="PlantUML jar for --backend local",
    )
    parser.add_argument("--only", default=None, help="substring filter on filename")
    parser.add_argument("--check", action="store_true", help="validate only, no output")
    parser.add_argument("--timeout", type=float, default=45.0, help="HTTP timeout seconds")
    args = parser.parse_args()

    try:
        diagrams = discover(args.only)
        if not args.check:
            BUILD_DIR.mkdir(parents=True, exist_ok=True)
        if args.backend == "local":
            jar = args.jar or str(ROOT.parent / "tools" / "plantuml.jar")
            if not Path(jar).is_file():
                raise RenderError(
                    "local backend needs --jar or PLANTUML_JAR pointing at plantuml.jar"
                )
            results = render_with_local(diagrams, jar, args.check)
        else:
            results = render_with_kroki(
                diagrams, args.kroki_url, args.timeout, args.check
            )
        if not args.check:
            write_manifest(diagrams, results)
    except RenderError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    verb = "validated" if args.check else "rendered"
    print(f"{verb} {len(diagrams)} diagram(s) via {args.backend}")
    for diagram in diagrams:
        print(f"  - {diagram.name}")
    if not args.check:
        print(f"output: {BUILD_DIR.relative_to(ROOT.parent)}/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
