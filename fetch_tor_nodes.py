#!/usr/bin/env python3
"""Fetch running Tor relay nodes from the Onionoo API and write CSV files."""

import csv
import json
import re
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

ONIONOO_URL = "https://onionoo.torproject.org/details?running=true&type=relay"
OUTPUT_DIR = Path(__file__).parent / "torlist-db"
CSV_HEADER = ["fingerprint", "ipaddr", "port"]
MIN_RELAY_COUNT = 100  # sanity check — real network always has thousands

_IPV6_RE = re.compile(r"^\[(.+)\]:(\d+)$")
_IPV4_RE = re.compile(r"^(.+):(\d+)$")


@dataclass
class NodeRow:
    fingerprint: str
    ipaddr: str
    port: int


@dataclass
class Relay:
    fingerprint: str
    or_addresses: list[str] = field(default_factory=list)
    flags: list[str] = field(default_factory=list)

    def rows(self) -> list[NodeRow]:
        result: list[NodeRow] = []
        for addr in self.or_addresses:
            m = _IPV6_RE.match(addr) or _IPV4_RE.match(addr)
            if m:
                result.append(NodeRow(self.fingerprint, m.group(1), int(m.group(2))))
        return result

    def is_guard(self) -> bool:
        return "Guard" in self.flags

    def is_exit(self) -> bool:
        return "Exit" in self.flags


def fetch_relays() -> list[Relay]:
    req = urllib.request.Request(
        ONIONOO_URL,
        headers={"User-Agent": "tornode-database/1.0 (github.com)"},
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            raw = resp.read()
    except urllib.error.HTTPError as exc:
        raise SystemExit(f"ERROR: HTTP {exc.code} {exc.reason}") from exc
    except urllib.error.URLError as exc:
        raise SystemExit(f"ERROR: network — {exc.reason}") from exc

    try:
        data: dict[str, Any] = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"ERROR: invalid JSON from API — {exc}") from exc

    relays: list[Relay] = []
    for i, r in enumerate(data.get("relays", [])):
        try:
            relays.append(
                Relay(
                    fingerprint=r["fingerprint"],
                    or_addresses=r.get("or_addresses", []),
                    flags=r.get("flags", []),
                )
            )
        except KeyError as exc:
            print(f"  WARNING: skipping relay #{i} — missing field {exc}", file=sys.stderr)

    return relays


def write_csv_atomic(path: Path, rows: list[NodeRow]) -> None:
    tmp = path.with_suffix(".tmp")
    try:
        with tmp.open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(CSV_HEADER)
            for row in rows:
                writer.writerow([row.fingerprint, row.ipaddr, row.port])
        tmp.replace(path)  # atomic on POSIX
    except OSError as exc:
        tmp.unlink(missing_ok=True)
        raise SystemExit(f"ERROR: could not write {path.name} — {exc}") from exc
    print(f"  {path.name}: {len(rows)} rows")


def main() -> None:
    OUTPUT_DIR.mkdir(exist_ok=True)

    print("Fetching relay list from Onionoo …")
    relays = fetch_relays()
    print(f"Fetched {len(relays)} relays.")

    if len(relays) < MIN_RELAY_COUNT:
        raise SystemExit(
            f"ERROR: only {len(relays)} relays returned — "
            "looks like an API error; existing files left unchanged."
        )

    print("Writing CSV files …")
    all_rows = [row for r in relays for row in r.rows()]
    guard_rows = [row for r in relays if r.is_guard() for row in r.rows()]
    exit_rows = [row for r in relays if r.is_exit() for row in r.rows()]

    write_csv_atomic(OUTPUT_DIR / "latest.all.csv", all_rows)
    write_csv_atomic(OUTPUT_DIR / "latest.guards.csv", guard_rows)
    write_csv_atomic(OUTPUT_DIR / "latest.exits.csv", exit_rows)

    print("Done.")


if __name__ == "__main__":
    main()
