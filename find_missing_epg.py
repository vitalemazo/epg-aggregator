#!/usr/bin/env python3
"""Compare your IPTV playlist against the unified EPG and list any channels
that are missing guide data.

Credentials (USERNAME, PASSWORD) are supplied at runtime through
GitHub‑Actions environment variables that map to repo secrets.
"""

import os
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import requests  # type: ignore

###############################################################################
# 1. Load unified EPG and collect its channel IDs
###############################################################################

epg_file = Path("unified_epg.xml")

if not epg_file.exists():
    print("unified_epg.xml not found. Run merge_epg.py first.", file=sys.stderr)
    sys.exit(1)

unified_root = ET.parse(epg_file).getroot()
unified_ids = {ch.get("id") for ch in unified_root.findall("channel")}

###############################################################################
# 2. Fetch your playlist M3U (credentials come from GitHub Secrets)
###############################################################################

username = os.getenv("USERNAME")
password = os.getenv("PASSWORD")

if not username or not password:
    print("ERROR: USERNAME or PASSWORD env vars are not set.", file=sys.stderr)
    sys.exit(1)

m3u_url = (
    "http://boom38586.cdngold.me/"
    f"xmltv.php?username={username}&password={password}"
)

try:
    resp = requests.get(m3u_url, timeout=30)
    resp.raise_for_status()
except requests.RequestException as err:
    print(f"Failed to fetch playlist: {err}", file=sys.stderr)
    sys.exit(1)

playlist_text = resp.text

###############################################################################
# 3. Extract all tvg‑id values via regex
###############################################################################

playlist_ids = set(re.findall(r'tvg-id="([^"]+)"', playlist_text))

###############################################################################
# 4. Compute & report missing IDs
###############################################################################

missing = sorted(playlist_ids - unified_ids)

if not missing:
    print("All playlist channels have EPG data.")
else:
    print(f"{len(missing)} channels missing EPG:")
    for cid in missing:
        print("  -", cid)
