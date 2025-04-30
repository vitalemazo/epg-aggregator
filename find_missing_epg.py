#!/usr/bin/env python3
"""
Report any playlist channels whose tvg-id

  • is absent from unified_epg.xml, or
  • has no programme entries in the next 7 days.

If everything looks good, also print the 10 busiest channels
(counted by programmes within that 7-day window).
"""

from __future__ import annotations

import os
import re
import sys
import datetime as dt
import xml.etree.ElementTree as ET
from typing import Dict, List

import requests

# ──────────────────────────────────────────────────────────────────────────────
# 1.  Load unified EPG and index programmes by channel id
# ──────────────────────────────────────────────────────────────────────────────
try:
    tree = ET.parse("unified_epg.xml")
except FileNotFoundError:
    sys.exit("unified_epg.xml not found – run merge_epg.py first.")

root = tree.getroot()

programmes: Dict[str, List[str]] = {}
for p in root.findall("programme"):
    cid = p.get("channel")
    if cid:
        programmes.setdefault(cid, []).append(p.get("start", "")[:14])  # yyyymmddHHMMSS

# ──────────────────────────────────────────────────────────────────────────────
# 2.  Download the playlist with creds from repo secrets
# ──────────────────────────────────────────────────────────────────────────────
user, pw = os.getenv("USERNAME"), os.getenv("PASSWORD")
if not user or not pw:
    sys.exit("USERNAME / PASSWORD env-vars are missing.")

url = f"http://boom38586.cdngold.me/xmltv.php?username={user}&password={pw}"
try:
    resp = requests.get(url, timeout=60, headers={"User-Agent": "VLC/3.0"})
    resp.raise_for_status()
except requests.RequestException as e:
    sys.exit(f"Failed to fetch playlist: {e}")

ids_in_playlist = set(re.findall(r'tvg-id="([^"]+)"', resp.text))

# ──────────────────────────────────────────────────────────────────────────────
# 3.  Check each tvg-id for at least one show in the next 7 days
# ──────────────────────────────────────────────────────────────────────────────
now   = dt.datetime.now(dt.timezone.utc)
limit = now + dt.timedelta(days=7)

def has_future_show(ch_id: str) -> bool:
    for start in programmes.get(ch_id, []):
        try:
            start_dt = dt.datetime.strptime(start, "%Y%m%d%H%M%S").replace(tzinfo=dt.timezone.utc)
        except ValueError:
            continue
        if now <= start_dt <= limit:
            return True
    return False

missing = [
    cid for cid in sorted(ids_in_playlist)
    if cid not in programmes or not has_future_show(cid)
]

# ──────────────────────────────────────────────────────────────────────────────
# 4.  Report results
# ──────────────────────────────────────────────────────────────────────────────
if missing:
    print(f"{len(missing)} channel(s) missing useful EPG:")
    for cid in missing:
        print("  •", cid)
    sys.exit(0)              # do not fail the workflow, just inform
else:
    print("Every playlist channel has at least one programme in the next 7 days.")

    # Optional stats
    print("\nTop 10 channels by programme count in next 7 days:")
    tallies = sorted(
        ((cid, sum(has_future_show(cid) for _ in programmes.get(cid, [])))
         for cid in ids_in_playlist),
        key=lambda x: x[1],
        reverse=True
    )[:10]
    for cid, count in tallies:
        print(f"{cid:35} {count}")
