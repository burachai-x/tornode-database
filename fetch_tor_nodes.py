#!/usr/bin/env python3
"""Fetch running Tor relay nodes from the Onionoo API and write CSV files."""

import csv
import re
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:
    import json
except ImportError:
    import simplejson as json  # type: ignore[no-redef]

ONIONOO_URL = "https://onionoo.torproject.org/details?running=true&type=relay"
OUTPUT_DIR = Path(__file__).parent / "torlist-db"
CSV_HEADER = ["fingerprint", "ipaddr", "port"]

# Matches "[ipv6]:port" or "ipv4:port"
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
    with urllib.request.urlopen(req, timeout=60) as resp:
        data: dict[str, Any] = json.loads(resp.read())

    relays: list[Relay] = []
    for r in data.get("relays", []):
        relays.append(
            Relay(
                fingerprint=r["fingerprint"],
                or_addresses=r.get("or_addresses", []),
                flags=r.get("flags", []),
            )
        )
    return relays


def write_csv(path: Path, rows: list[NodeRow]) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(CSV_HEADER)
        for row in rows:
            writer.writerow([row.fingerprint, row.ipaddr, row.port])
    print(f"  {path.name}: {len(rows)} rows")


def main() -> None:
    OUTPUT_DIR.mkdir(exist_ok=True)

    print("Fetching relay list from Onionoo …")
    try:
        relays = fetch_relays()
    except urllib.error.URLError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)

    print(f"Fetched {len(relays)} relays. Writing CSV files …")

    all_rows = [row for r in relays for row in r.rows()]
    guard_rows = [row for r in relays if r.is_guard() for row in r.rows()]
    exit_rows = [row for r in relays if r.is_exit() for row in r.rows()]

    write_csv(OUTPUT_DIR / "latest.all.csv", all_rows)
    write_csv(OUTPUT_DIR / "latest.guards.csv", guard_rows)
    write_csv(OUTPUT_DIR / "latest.exits.csv", exit_rows)

    print("Done.")


if __name__ == "__main__":
    main()
