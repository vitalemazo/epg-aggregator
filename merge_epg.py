#!/usr/bin/env python3
import os
import re
import requests
import gzip
import shutil
from xml.etree import ElementTree as ET

# ──────────────────────────────────────────────────────────────────────────────
# Configuration: EPG chunks and optional M3U URL from secrets
# ──────────────────────────────────────────────────────────────────────────────
EPG_URLS = [
    "https://www.open-epg.com/files/unitedstates1.xml.gz",
    "https://www.open-epg.com/files/unitedstates2.xml.gz",
    "https://www.open-epg.com/files/unitedstates3.xml.gz",
    "https://www.open-epg.com/files/unitedstates4.xml.gz",
    "https://www.open-epg.com/files/unitedstates5.xml.gz",
    "https://www.open-epg.com/files/unitedstates6.xml.gz",
    "https://www.open-epg.com/files/unitedstates7.xml.gz",
    # "https://www.open-epg.com/generate/E5rVFNmdxZ.xml.gz",
    "https://www.open-epg.com/files/unitedstates8.xml.gz",
    # "https://epgshare01.online/epgshare01/epg_ripper_ALL_SOURCES1.xml.gz",
]

# Try to build the M3U URL from GitHub Secrets
USER = os.getenv("USERNAME")
PASSWORD = os.getenv("PASSWORD")
if USER and PASSWORD:
    # Download the M3U+ playlist (use get.php?type=m3u_plus)
    M3U_URL = (
        f"http://boom38586.cdngold.me/get.php?"
        f"username={USER}&password={PASSWORD}&type=m3u_plus"
    )
    try:
        print(f"Fetching playlist from {M3U_URL}…")
        # bump timeout to 90s in case the feed is large
        resp = requests.get(M3U_URL, timeout=90, headers={"User-Agent": "VLC/3.0"})
        resp.raise_for_status()

        # pull out all the tvg-id attributes (may include empty strings)
        raw_ids = re.findall(r'tvg-id="([^"]*)"', resp.text)
        # drop empty ones
        ids_in_playlist = {tid for tid in raw_ids if tid.strip()}

        aliases = {}
        for line in resp.text.splitlines():
            if not line.startswith("#EXTINF"):
                continue
            # extract possibly‐empty tvg-id
            id_match = re.search(r'tvg-id="([^"]*)"', line)
            if not id_match:
                continue
            vid = id_match.group(1).strip()
            # skip the empty‐id entries
            if not vid:
                continue

            # pull the display name (fallback to the text after the comma)
            name_match = re.search(r'tvg-name="([^"]+)"', line)
            vname = name_match.group(1).strip() if name_match else line.split(",", 1)[1].strip()

            # only keep ones that actually appeared in the playlist
            if vid in ids_in_playlist:
                aliases[vid] = vname

        print(f"Found {len(aliases)} playlist entries")
    except Exception as e:
        print(f"Warning: failed to fetch playlist ({e}), skipping alias injection")
        aliases = {}
else:
    print("USERNAME/PASSWORD not set, skipping alias injection")
    aliases = {}

def main():
    # Step 1: Download and decompress EPG chunks
    xml_files = []
    for idx, url in enumerate(EPG_URLS):
        gz_fn = f"chunk{idx}.xml.gz"
        xml_fn = f"chunk{idx}.xml"
        print(f"Downloading {url}...")
        r = requests.get(url, timeout=30)
        r.raise_for_status()
        with open(gz_fn, "wb") as f:
            f.write(r.content)
        with gzip.open(gz_fn, "rb") as fi, open(xml_fn, "wb") as fo:
            shutil.copyfileobj(fi, fo)
        xml_files.append(xml_fn)
    
    # Step 2: Merge into a single <tv> root
    tv = ET.Element("tv", {"generator-info-name": "Unified EPG"})
    for xml_fn in xml_files:
        tree = ET.parse(xml_fn)
        for elem in tree.getroot():
            tv.append(elem)
    
    # Step 3: Inject missing channels based on playlist aliases
    existing = {ch.get("id") for ch in tv.findall("channel")}
    added = 0
    for vid, vname in aliases.items():
        if vid not in existing:
            ch = ET.SubElement(tv, "channel", {"id": vid})
            dn = ET.SubElement(ch, "display-name")
            dn.text = vname
            added += 1
    print(f"Added {added} missing channel aliases")
    
    # Step 4: Write out unified_epg.xml with DOCTYPE
    out = "unified_epg.xml"
    with open(out, "w", encoding="utf-8") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        f.write('<!DOCTYPE tv SYSTEM "xmltv.dtd">\n')
        f.write(ET.tostring(tv, encoding="unicode"))
    print("Unified EPG created:", out)
    
    # Step 5: Cleanup
    for fn in xml_files + [fn.replace(".xml", ".xml.gz") for fn in xml_files]:
        try:
            os.remove(fn)
        except OSError:
            pass

if __name__ == "__main__":
    main()
