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
    r.raise_for_status()
    with open(gz_filename, 'wb') as f:
        f.write(r.content)

    # Decompress
    with gzip.open(gz_filename, 'rb') as f_in, open(xml_filename, 'wb') as f_out:
        shutil.copyfileobj(f_in, f_out)

    xml_files.append(xml_filename)

# Merge
# Create <tv> root with generator-info-name
merged_root = ET.Element('tv', {'generator-info-name': 'Unified EPG'})

for xml_file in xml_files:
    tree = ET.parse(xml_file)
    root = tree.getroot()

    for child in root:
        merged_root.append(child)

# Prepare final XML string
final_xml = ET.tostring(merged_root, encoding='utf-8').decode('utf-8')

# Write out with declaration and DOCTYPE
with open('unified_epg.xml', 'w', encoding='utf-8') as f:
    f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
    f.write('<!DOCTYPE tv SYSTEM "xmltv.dtd">\n')
    f.write(final_xml)

print("Unified EPG created: unified_epg.xml")

# Clean up temp files
for f in xml_files + [fn.replace('.xml', '.xml.gz') for fn in xml_files]:
    try:
        os.remove(f)
    except OSError:
        pass