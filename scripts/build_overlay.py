#!/usr/bin/env python3
"""Builds the map overlay: Slovakia's outline and place names, shown on top of every era.

Writes public/overlay/slovakia.geojson (outline, from OpenStreetMap via Nominatim) and
public/overlay/places.geojson (settlements from GeoNames, CC BY 4.0). Run once; the output is committed.

Usage: python3 scripts/build_overlay.py
"""
import io
import json
import urllib.request
import zipfile
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / 'public' / 'overlay'
UA = {'User-Agent': 'kedysi-a-dnes overlay build'}


def get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=120) as r:
        return r.read()


def rank(code, pop):
    """1: capital and regional seats, 2: district seats and towns over 10k, 3: over 1k, 4: the rest."""
    if code in ('PPLC', 'PPLA'):
        return 1
    if code == 'PPLA2' or pop >= 10000:
        return 2
    if pop >= 1000:
        return 3
    return 4


def main():
    OUT.mkdir(parents=True, exist_ok=True)

    outline = json.loads(get('https://nominatim.openstreetmap.org/search?country=Slovakia&format=geojson'
                             '&polygon_geojson=1&polygon_threshold=0.002&limit=1'))
    geometry = outline['features'][0]['geometry']
    (OUT / 'slovakia.geojson').write_text(json.dumps(
        {'type': 'Feature', 'properties': {}, 'geometry': geometry}, separators=(',', ':')))

    rows = zipfile.ZipFile(io.BytesIO(get('https://download.geonames.org/export/dump/SK.zip'))).read('SK.txt')
    features = []
    for line in rows.decode().splitlines():
        f = line.split('\t')
        name, lat, lng, fclass, code, pop = f[1], float(f[4]), float(f[5]), f[6], f[7], int(f[14] or 0)
        # Populated places, without city quarters (PPLX), abandoned or historical places.
        if fclass != 'P' or code in ('PPLX', 'PPLH', 'PPLQ', 'PPLW', 'PPLCH'):
            continue
        features.append({'type': 'Feature', 'properties': {'n': name, 'r': rank(code, pop)},
                         'geometry': {'type': 'Point', 'coordinates': [round(lng, 4), round(lat, 4)]}})
    features.sort(key=lambda x: x['properties']['r'])
    (OUT / 'places.geojson').write_text(json.dumps(
        {'type': 'FeatureCollection', 'features': features}, ensure_ascii=False, separators=(',', ':')))
    print(f"outline: {geometry['type']}, places: {len(features)}")


if __name__ == '__main__':
    main()
