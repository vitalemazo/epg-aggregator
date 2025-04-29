import requests
import gzip
import shutil
import os
from xml.etree import ElementTree as ET

# URLs to download
urls = [
    "https://www.open-epg.com/files/unitedstates1.xml.gz",
    "https://www.open-epg.com/files/unitedstates2.xml.gz",
    "https://www.open-epg.com/files/unitedstates3.xml.gz",
    "https://www.open-epg.com/files/unitedstates4.xml.gz",
    "https://www.open-epg.com/files/unitedstates5.xml.gz",
    "https://www.open-epg.com/files/unitedstates6.xml.gz",
    "https://www.open-epg.com/files/unitedstates7.xml.gz",
    "https://www.open-epg.com/files/unitedstates8.xml.gz",
]

# Download and decompress
xml_files = []
for idx, url in enumerate(urls):
    gz_filename = f"file{idx}.xml.gz"
    xml_filename = f"file{idx}.xml"

    print(f"Downloading {url}...")
    r = requests.get(url, timeout=30)
    with open(gz_filename, 'wb') as f:
        f.write(r.content)

    # Decompress
    with gzip.open(gz_filename, 'rb') as f_in:
        with open(xml_filename, 'wb') as f_out:
            shutil.copyfileobj(f_in, f_out)

    xml_files.append(xml_filename)

# Merge
merged_root = ET.Element('tv')

for xml_file in xml_files:
    tree = ET.parse(xml_file)
    root = tree.getroot()

    for child in root:
        merged_root.append(child)

# Save merged file
tree = ET.ElementTree(merged_root)
tree.write('unified_epg.xml', encoding='utf-8', xml_declaration=True)

print("Unified EPG created: unified_epg.xml")

# Clean up
for file in xml_files + [f.replace('.xml', '.xml.gz') for f in xml_files]:
    os.remove(file)
