"""Attempt to download public datasets for GraphIntel.

Public support/incident/postmortem corpora are frequently gated, unstable, or
licensed in ways that forbid redistribution. This script therefore *attempts*
best-effort downloads, logs each source outcome, and NEVER fails the pipeline:
any source that cannot be fetched is recorded and the synthetic fallback covers
it (see generate_synthetic_demo_data.py).

Run: python scripts/download_datasets.py
"""
from __future__ import annotations

import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _dataset_common import RAW_DIR, days_ago, ensure_dirs, write_json  # noqa: E402

# Candidate public sources. These are best-effort; licensing/availability vary.
CANDIDATE_SOURCES = [
    {
        "name": "github_public_incidents_sample",
        "kind": "incidents",
        "url": "https://raw.githubusercontent.com/dastergon/postmortem-templates/master/README.md",
        "note": "Public postmortem template reference (structure only).",
    },
    {
        "name": "status_page_incident_feed",
        "kind": "incidents",
        "url": "https://www.githubstatus.com/history.json",
        "note": "Public status page incident history (schema reference).",
    },
]

TIMEOUT_SECONDS = 8


def attempt_download(source: dict) -> dict:
    dest = RAW_DIR / f"{source['name']}"
    try:
        req = urllib.request.Request(source["url"], headers={"User-Agent": "GraphIntel/0.1"})
        with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as resp:  # noqa: S310
            data = resp.read()
        suffix = ".json" if source["url"].endswith(".json") else ".txt"
        out_path = dest.with_suffix(suffix)
        out_path.write_bytes(data)
        return {
            "name": source["name"], "kind": source["kind"], "url": source["url"],
            "status": "downloaded", "bytes": len(data), "path": str(out_path.relative_to(RAW_DIR.parent.parent)),
            "note": source["note"],
        }
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError) as exc:
        return {
            "name": source["name"], "kind": source["kind"], "url": source["url"],
            "status": "failed", "error": str(exc), "note": source["note"],
        }


def main() -> int:
    ensure_dirs()
    results = [attempt_download(s) for s in CANDIDATE_SOURCES]
    manifest = {
        "attempted_at": days_ago(0),
        "sources": results,
        "downloaded": sum(1 for r in results if r["status"] == "downloaded"),
        "failed": sum(1 for r in results if r["status"] == "failed"),
        "policy": "Failed sources are expected; synthetic fallback provides complete demo data.",
    }
    write_json(RAW_DIR / "download_manifest.json", manifest)

    print("Public dataset download attempt complete.")
    for r in results:
        if r["status"] == "downloaded":
            print(f"  [ok]   {r['name']} ({r['bytes']} bytes)")
        else:
            print(f"  [fail] {r['name']} -> {r.get('error', 'unknown')} (using synthetic fallback)")
    print(f"Manifest: {RAW_DIR / 'download_manifest.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
