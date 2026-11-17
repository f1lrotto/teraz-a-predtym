#!/usr/bin/env python3
"""Weekly catalog check. Updates catalog/layers.json in place and writes a Markdown report.

- Checks one sample tile per layer and sets or clears "broken" (the site hides broken layers).
- Points the Esri ("esri") capture-date lookup at the newest Esri Wayback metadata release.
- Lists the MŽP, EOX and city services and reports names it has not seen before
  (remembered in the catalog's "watch" lists, so each is reported once).

Usage: python3 scripts/refresh_catalog.py [report.md]
"""
import json
import math
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

CATALOG = Path(__file__).resolve().parent.parent / 'catalog' / 'layers.json'
UA = {'User-Agent': 'kedysi-a-dnes catalog check'}
R = 20037508.342789244


def get(url, timeout=40):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=timeout) as r:
        return r.status, r.headers.get('Content-Type', ''), r.read()


def tile_at(lng, lat, z):
    n = 2**z
    x = int((lng + 180) / 360 * n)
    y = int((1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2 * n)
    return x, y


def sample_url(layer):
    w, s, e, n = layer['bounds']
    lng, lat = (w + e) / 2, (s + n) / 2
    z = min(layer['maxzoom'], 14)
    x, y = tile_at(lng, lat, z)
    if layer['kind'] == 'xyz':
        return layer['url'].format(z=z, x=x, y=y)
    size = (2 * R) / 2**z
    bbox = ','.join(f'{v:.2f}' for v in (-R + x * size, R - (y + 1) * size, -R + (x + 1) * size, R - y * size))
    return (f"{layer['url']}?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetMap&LAYERS={layer['layers']}&STYLES="
            f"&CRS=EPSG:3857&WIDTH=512&HEIGHT=512&FORMAT={layer['format']}&TRANSPARENT=true&BBOX={bbox}")


def check_tile(layer):
    for _ in range(2):
        try:
            status, ctype, body = get(sample_url(layer))
            # An empty (fully transparent) 512 px PNG is about 1.5 KB; real tiles are far bigger.
            if status == 200 and ctype.startswith(('image/', 'application/octet-stream')) and len(body) > 2500:
                return None
            problem = f'{status} {ctype} {len(body)} B'
        except Exception as e:  # noqa: BLE001 - any failure counts as broken
            problem = str(e)[:120]
    return problem


def wms_layer_names(url):
    _, _, body = get(f'{url}?SERVICE=WMS&REQUEST=GetCapabilities&VERSION=1.3.0')
    root = ET.fromstring(body)
    return sorted({el.text for el in root.iter() if el.tag.endswith('}Name') and el.text and el.text.lower() != 'wms'})


def arcgis_services(url):
    _, _, body = get(f'{url}?f=json')
    return sorted(s['name'] for s in json.loads(body).get('services', []))


SOURCES = {
    'mzp': lambda: wms_layer_names('https://gis.geocloud.gov.sk/geoserver/mzpsr/ows'),
    'eox': lambda: sorted(set(re.findall(rb'<ows:Identifier>(s2cloudless[^<]*)</ows:Identifier>',
                                         get('https://tiles.maps.eox.at/wmts/1.0.0/WMTSCapabilities.xml')[2]))),
    'bratislava': lambda: arcgis_services('https://geoportal.bratislava.sk/hsite/rest/services/Hosted')
    + arcgis_services('https://geoportal.bratislava.sk/hsite/rest/services/historicke'),
    'trencin': lambda: arcgis_services('https://tiles.arcgis.com/tiles/goZLUACRDSDrf4xu/arcgis/rest/services'),
    'kosice': lambda: wms_layer_names('https://gisplan.kosice.sk/services/mapserver/common/of/gservice')
    + wms_layer_names('https://gisplan.kosice.sk/services/mapserver/local/hstmp/gservice'),
    'banska-bystrica': lambda: wms_layer_names('https://mapy.banskabystrica.sk/services/mapserver/common/of/gservice'),
    'zilina': lambda: wms_layer_names('https://gis.zilina.sk/services/mapserver/common/of/gservice'),
}


def main():
    report_path = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    catalog = json.loads(CATALOG.read_text())
    lines = []

    broken = []
    for layer in catalog['layers']:
        if layer.get('euOnly'):
            # Its server refuses connections from outside Europe, where the runner is; never hide it for that.
            broken.append(f"- `{layer['id']}` ({layer['title']}): not checked, EU only")
            continue
        problem = check_tile(layer)
        if problem:
            layer['broken'] = True
            broken.append(f"- `{layer['id']}` ({layer['title']}): {problem}")
        else:
            layer.pop('broken', None)
    lines += ['## Tile check', *(broken or ['All checked layers returned tiles.']), '']

    try:
        _, _, body = get('https://s3-us-west-2.amazonaws.com/config.maptiles.arcgis.com/waybackconfig.json')
        releases = json.loads(body).values()
        newest = max(releases, key=lambda r: r['itemTitle'])
        esri = next(l for l in catalog['layers'] if l['id'] == 'esri')
        if esri.get('metadata') != newest['metadataLayerUrl']:
            esri['metadata'] = newest['metadataLayerUrl']
            lines += ['## Esri Wayback', f"- Capture dates now use {newest['itemTitle']}.", '']
    except Exception as e:  # noqa: BLE001
        lines += ['## Esri Wayback', f'- Release list unavailable: {e}', '']

    watch = catalog.setdefault('watch', {})
    found = []
    for name, fetch in SOURCES.items():
        try:
            names = [n.decode() if isinstance(n, bytes) else n for n in fetch()]
        except Exception as e:  # noqa: BLE001
            found.append(f'- {name}: service unavailable ({str(e)[:100]})')
            continue
        known = set(watch.get(name, []))
        new = [n for n in names if n not in known]
        if name in watch and new:
            found.append(f"- {name}: {', '.join(f'`{n}`' for n in new)}")
        watch[name] = sorted(known | set(names))
    lines += ['## New layers at the sources', *(found or ['Nothing new.']), '']

    CATALOG.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + '\n')
    report = '\n'.join(lines)
    print(report)
    if report_path:
        report_path.write_text(report)


if __name__ == '__main__':
    main()
