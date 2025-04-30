#!/usr/bin/env python3
import os
import re
import requests  # type: ignore
import gzip
import shutil
from xml.etree import ElementTree as ET

# ──────────────────────────────────────────────────────────────────────────────
# Configuration: EPG chunks and M3U URL from secrets
# ──────────────────────────────────────────────────────────────────────────────
EPG_URLS = [
    "https://www.open-epg.com/files/unitedstates1.xml.gz",
    "https://www.open-epg.com/files/unitedstates2.xml.gz",
    "https://www.open-epg.com/files/unitedstates3.xml.gz",
    "https://www.open-epg.com/files/unitedstates4.xml.gz",
    "https://www.open-epg.com/files/unitedstates5.xml.gz",
    "https://www.open-epg.com/files/unitedstates6.xml.gz",
    "https://www.open-epg.com/files/unitedstates7.xml.gz",
    "https://www.open-epg.com/files/unitedstates8.xml.gz",
]

# Read IPTV credentials from environment (set via GitHub Secrets)
USER = os.getenv("USERNAME")
PASSWORD = os.getenv("PASSWORD")
if not USER or not PASSWORD:
    raise RuntimeError("Environment variables USERNAME and PASSWORD must be set")

M3U_URL = f"http://boom38586.cdngold.me/xmltv.php?username={USER}&password={PASSWORD}"

def main():
    # Step 1: Fetch and parse M3U playlist
    print(f"Fetching playlist from {M3U_URL}...")
    resp = requests.get(M3U_URL, timeout=30)
    resp.raise_for_status()
    aliases = {}
    for line in resp.text.splitlines():
        if line.startswith("#EXTINF"):
            m_id = re.search(r'tvg-id="([^"]+)"', line)
            m_name = re.search(r'tvg-name="([^"]+)"', line)
            if m_id:
                vid = m_id.group(1).strip()
                vname = m_name.group(1).strip() if m_name else line.split(",", 1)[1].strip()
                aliases[vid] = vname
    print(f"Found {len(aliases)} playlist entries")

    # Step 2: Download and decompress EPG chunks
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

    # Step 3: Merge into a single <tv> root
    tv = ET.Element("tv", {"generator-info-name": "Unified EPG"})
    for xml_fn in xml_files:
        tree = ET.parse(xml_fn)
        for elem in tree.getroot():
            tv.append(elem)

    # Step 4: Inject missing channels based on playlist
    existing = {ch.get("id") for ch in tv.findall("channel")}
    added = 0
    for vid, vname in aliases.items():
        if vid not in existing:
            ch = ET.SubElement(tv, "channel", {"id": vid})
            dn = ET.SubElement(ch, "display-name")
            dn.text = vname
            added += 1
    print(f"Added {added} missing channel aliases")

    # Step 5: Write out unified_epg.xml with DOCTYPE
    out = "unified_epg.xml"
    with open(out, "w", encoding="utf-8") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        f.write('<!DOCTYPE tv SYSTEM "xmltv.dtd">\n')
        f.write(ET.tostring(tv, encoding="unicode"))
    print("Unified EPG created:", out)

    # Cleanup
    for fn in xml_files + [f.replace(".xml", ".xml.gz") for f in xml_files]:
        try:
            os.remove(fn)
        except OSError:
            pass

if __name__ == "__main__":
    main()
