#!/usr/bin/env python3
"""
List any playlist channels whose tvg-id either
  • is absent from unified_epg.xml, or
  • has no programme entries in the next 7 days.
"""

from __future__ import annotations
import os, re, sys, datetime as dt, xml.etree.ElementTree as ET, requests

# ── 1.  Load unified EPG ─────────────────────────────────────────────────────
try:
    tree = ET.parse("unified_epg.xml")
except FileNotFoundError:
    sys.exit("unified_epg.xml not found – run merge_epg.py first.")

root = tree.getroot()

# Map channel-id → list of <programme start=…>
programmes: dict[str, list[str]] = {}
for p in root.findall("programme"):
    cid = p.get("channel")
    if cid:
        programmes.setdefault(cid, []).append(p.get("start", "")[:14])  # yyyymmddHHMMSS tz

# ── 2.  Get the playlist ------------------------------------------------------
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

# ── 3.  Check each id for upcoming shows -------------------------------------
now = dt.datetime.utcnow()
limit = now + dt.timedelta(days=7)

def has_future_show(ch_id: str) -> bool:
    for start in programmes.get(ch_id, []):
        try:
            start_dt = dt.datetime.strptime(start, "%Y%m%d%H%M%S")
        except ValueError:
            continue
        if now <= start_dt <= limit:
            return True
    return False

missing = [
    cid for cid in sorted(ids_in_playlist)
    if cid not in programmes or not has_future_show(cid)
]

# ── 4.  Report ----------------------------------------------------------------
if missing:
    print(f"{len(missing)} channel(s) missing useful EPG:")
    for cid in missing:
        print("  •", cid)
else:
    print("Every playlist channel has at least one programme in the next 7 days.")
