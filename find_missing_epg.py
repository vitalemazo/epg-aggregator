#!/usr/bin/env python3
"""
Compare the playlist from the provider against unified_epg.xml
and list any tvg-ids that have no guide data.
"""

from __future__ import annotations

import os
import re
import sys
import xml.etree.ElementTree as ET
from typing import Set

import requests

# ──────────────────────────────────────────────────────────────────────────────
# 1. Load the merged EPG and collect its channel IDs
# ──────────────────────────────────────────────────────────────────────────────
try:
    unified_root = ET.parse("unified_epg.xml").getroot()
except FileNotFoundError:
    print("unified_epg.xml not found. Run merge_epg.py first.", file=sys.stderr)
    sys.exit(1)

unified_ids: Set[str] = {c.get("id") for c in unified_root.findall("channel") if c.get("id")}

# ──────────────────────────────────────────────────────────────────────────────
# 2. Pull USERNAME/PASSWORD from environment (set in the workflow)
# ──────────────────────────────────────────────────────────────────────────────
username = os.getenv("USERNAME")
password = os.getenv("PASSWORD")

if not username or not password:
    print("ERROR: USERNAME or PASSWORD env-vars were not provided.", file=sys.stderr)
    sys.exit(1)

m3u_url = (
    "http://boom38586.cdngold.me/"
    f"xmltv.php?username={username}&password={password}"
)

# ──────────────────────────────────────────────────────────────────────────────
# 3. Download the playlist
# ──────────────────────────────────────────────────────────────────────────────
try:
    resp = requests.get(
        m3u_url,
        timeout=60,
        headers={"User-Agent": "VLC/3.0"},  # many IPTV portals expect this
    )
    resp.raise_for_status()
except requests.RequestException as exc:
    print(f"Failed to fetch playlist: {exc}", file=sys.stderr)
    sys.exit(1)

playlist_text = resp.text

# ──────────────────────────────────────────────────────────────────────────────
# 4. Extract `tvg-id`s and report any that are missing from the EPG
# ──────────────────────────────────────────────────────────────────────────────
playlist_ids = set(re.findall(r'tvg-id="([^"]+)"', playlist_text))
missing = sorted(playlist_ids - unified_ids)

if not missing:
    print("✅ All playlist channels have EPG data.")
else:
    print(f"⚠️ {len(missing)} channel(s) missing EPG:")
    for cid in missing:
        print("  •", cid)