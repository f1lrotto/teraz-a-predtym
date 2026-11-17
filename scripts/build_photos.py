#!/usr/bin/env python3
"""Builds the historical photo layer: old photos of Slovakia that we can reuse freely, placed where they were taken.

Sources, all public domain or openly licensed (CC0, CC BY, CC BY-SA):
  - Ajapaik photos inside Slovakia whose original is on Wikimedia Commons.
  - Old photos on Commons with a camera location inside Slovakia (found through public-domain licence templates
    and the Fortepan category), dated before 1990, without paintings and portraits.

Each photo gets a tier:
  - confirmed: someone retook it on the spot (an Ajapaik rephoto), at least two people placed it on the map
    independently, or the camera location on Commons is within 100 m of the Ajapaik point;
  - approximate: one person placed it on Ajapaik, Ajapaik took the place over from its source, or only the camera
    location on Commons says where it is.
Rephotos are added as the "now" picture when their own licence is open (Ajapaik shows it on each photo page).

Writes public/overlay/photos.geojson. Run once; the output is committed.

Usage: python3 scripts/build_photos.py
"""
import html
import json
import math
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'public' / 'overlay' / 'photos.geojson'
UA = {'User-Agent': 'kedysi-a-dnes/0.1 (https://github.com/f1lrotto/teraz-a-predtym)'}
AJAPAIK = 'https://ajapaik.ee'
COMMONS = 'https://commons.wikimedia.org/w/api.php'
OPEN = re.compile(r'^(public domain|pd\b|cc0|cc[ -]by(-sa)?[ -]\d)', re.I)


def get(url, data=None):
    for attempt in range(6):
        try:
            req = urllib.request.Request(url, data=data and urllib.parse.urlencode(data).encode(), headers=UA)
            with urllib.request.urlopen(req, timeout=120) as r:
                return r.read()
        except urllib.error.HTTPError as e:
            if e.code != 429:
                raise
            time.sleep(int(e.headers.get('Retry-After') or 5 * (attempt + 1)))
    raise RuntimeError(f'rate limited: {url}')


def inside(lng, lat, ring):
    hit = False
    for (x1, y1), (x2, y2) in zip(ring, ring[1:]):
        if (y1 > lat) != (y2 > lat) and lng < (x2 - x1) * (lat - y1) / (y2 - y1) + x1:
            hit = not hit
    return hit


def metres(a, b):
    lat = math.radians((a[1] + b[1]) / 2)
    return 6371000 * math.hypot(math.radians(a[0] - b[0]) * math.cos(lat), math.radians(a[1] - b[1]))


def text(value):
    """Commons metadata is HTML; keep the visible text (dates hide a Wikidata copy in a display:none div)."""
    value = re.sub(r'<div style="display: ?none;?">.*?</div>', '', value or '', flags=re.S)
    return html.unescape(re.sub(r'<[^>]+>', '', value)).strip()


def page_facts(photo_id):
    """From an Ajapaik photo page: how many people geotagged it, and its licence link."""
    page = get(f'{AJAPAIK}/photo/{photo_id}/').decode()
    count = re.search(r'GeotaggingUserCount = (\d+)', page)
    licence = re.search(r'class="ajp-licence"[^>]*href="(https?://creativecommons[^"]+)"', page)
    time.sleep(0.5)
    return int(count.group(1)) if count else 0, licence and licence.group(1)


def commons_files(titles):
    """Licence, credit, camera location and a thumbnail for each Commons file title."""
    out = {}
    for i in range(0, len(titles), 40):
        batch = titles[i:i + 40]
        d = json.loads(get(COMMONS + '?' + urllib.parse.urlencode({
            'action': 'query', 'format': 'json', 'formatversion': 2, 'titles': '|'.join(batch),
            'prop': 'imageinfo|coordinates', 'iiprop': 'url|extmetadata|mime', 'iiurlwidth': 960,
            # colimit counts coordinates across the whole batch; the default of 10 drops most of them.
            'coprop': 'type', 'coprimary': 'primary', 'colimit': 'max'})))
        norm = {n['to']: n['from'] for n in d['query'].get('normalized', [])}
        for p in d['query']['pages']:
            if 'imageinfo' not in p:
                continue
            info = p['imageinfo'][0]
            meta = {k: v.get('value') for k, v in info.get('extmetadata', {}).items()}
            camera = (p.get('coordinates') or [None])[0]
            out[norm.get(p['title'], p['title'])] = {
                'page': info['descriptionurl'], 'thumb': info.get('thumburl') or info['url'],
                'licence': text(meta.get('LicenseShortName')), 'licenceUrl': meta.get('LicenseUrl') or '',
                'artist': text(meta.get('Artist')), 'credit': text(meta.get('Credit')),
                'date': text(meta.get('DateTimeOriginal')), 'name': text(meta.get('ObjectName')),
                'camera': camera and camera.get('type') == 'camera' and (camera['lon'], camera['lat']),
                'mime': info.get('mime') or '', 'categories': text(meta.get('Categories')),
            }
        time.sleep(0.5)
    return out


def commons_search(query):
    """Every file title a Commons search returns."""
    titles, offset = [], 0
    while offset is not None:
        d = json.loads(get(COMMONS + '?' + urllib.parse.urlencode({
            'action': 'query', 'format': 'json', 'formatversion': 2, 'list': 'search', 'srsearch': query,
            'srnamespace': 6, 'srlimit': 500, 'sroffset': offset})))
        titles += [x['title'] for x in d['query']['search']]
        offset = d.get('continue', {}).get('sroffset')
        time.sleep(0.5)
    return titles


def year(*dates):
    """The first plausible year in any of the date texts, or None."""
    for d in dates:
        m = re.search(r'\b(18[3-9]\d|19\d\d|20[0-2]\d)\b', d or '')
        if m:
            return int(m.group(1))
    return None


# Licence templates of old public-domain photos, and the Fortepan category; nearcoord covers all of Slovakia.
OLD_PHOTO_SEARCHES = [f'nearcoord:250km,48.7,19.5 {q}' for q in (
    'hastemplate:"PD-old"', 'hastemplate:"PD-old-70"', 'hastemplate:"PD-old-100"', 'hastemplate:"PD-anon-70-EU"',
    'hastemplate:"PD-old-auto"', 'hastemplate:"PD-old-auto-expired"', 'hastemplate:"PD-1923"',
    'incategory:"Images_from_Fortepan"')]
NOT_A_PLACE = re.compile(r'painting|portrait|drawing|engraving|lithograph|map of|maps of', re.I)
# Portraits whose categories only name the person.
NOT_PLACES = {'File:Viola Valachova (1928 1944) A.jpg'}


def drop_piles(features):
    """Drops approximate photos that lie within 5 m of four or more other approximate photos.

    Such a pile is a placeholder (Ajapaik has 80 different Bratislava views on one spot), not a real placement.
    """
    approx = [x['geometry']['coordinates'] for x in features if x['properties']['approx']]
    def piled(x):
        here = x['geometry']['coordinates']
        return x['properties']['approx'] and sum(metres(here, o) <= 5 for o in approx) >= 5
    return [x for x in features if not piled(x)]


def feature(lng, lat, f, title, **props):
    return {'type': 'Feature', 'geometry': {'type': 'Point', 'coordinates': [round(lng, 6), round(lat, 6)]},
            'properties': {'title': title, 'img': f['thumb'], 'page': f['page'], 'author': f['artist'] or f['credit'],
                           'licence': f['licence'], 'licenceUrl': f['licenceUrl'], **props}}


def main():
    ring = json.loads((ROOT / 'public' / 'overlay' / 'slovakia.geojson').read_text())['geometry']['coordinates'][0]
    # "nearest" returns Ajapaik's photos ordered by distance; 3000 around the middle of Slovakia covers all of them.
    photos = json.loads(get(f'{AJAPAIK}/api/v1/album/nearest/',
                            {'latitude': 48.7, 'longitude': 19.5, 'limit': 3000}))['photos']
    photos = [p for p in photos if p['latitude'] and inside(p['longitude'], p['latitude'], ring)]
    on_commons = {}
    for p in photos:
        m = re.match(r'https://commons\.wikimedia\.org/wiki/(File:.+)', (p.get('source') or {}).get('url') or '')
        if m:
            on_commons[p['id']] = urllib.parse.unquote(m.group(1)).replace('_', ' ')
    files = commons_files(sorted(set(on_commons.values())))
    print(f'Ajapaik in Slovakia: {len(photos)}, from Commons: {len(on_commons)}, found on Commons: {len(files)}')

    features, skipped = [], {'licence': 0}
    for p in photos:
        f = files.get(on_commons.get(p['id']))
        if not f:
            continue
        if not OPEN.match(f['licence']):
            skipped['licence'] += 1
            continue
        here = (p['longitude'], p['latitude'])
        geotaggers, _ = page_facts(p['id'])
        camera_m = f['camera'] and metres(here, f['camera'])
        proof = ('rephoto' if p['rephotos'] else 'geotags' if geotaggers >= 2
                 else 'commons' if camera_m is not None and camera_m <= 100
                 else 'single' if geotaggers == 1 else 'import')
        now = None
        for r in p['rephotos']:
            rid = re.search(r'/photo-thumb/(\d+)/', r['image']).group(1)
            _, licence = page_facts(rid)
            if licence:
                now = {'img': r['image'].replace('[DIM]', '800'), 'by': r.get('user_name') or '',
                       'date': r.get('date_text') or '', 'licenceUrl': licence, 'url': f'{AJAPAIK}/photo/{rid}/'}
                break
        title = f['name'] or re.sub(r'\.\w+$', '', on_commons[p['id']][5:])
        features.append(feature(
            *here, f, title, date=p.get('date') or f['date'], azimuth=p['azimuth'], proof=proof,
            approx=proof in ('single', 'import'), geotaggers=geotaggers, ajapaik=f'{AJAPAIK}/photo/{p["id"]}/', now=now))

    # Old photos on Commons that only Commons places, by their camera location.
    found = sorted({t for q in OLD_PHOTO_SEARCHES for t in commons_search(q)} - set(on_commons.values()))
    extra = commons_files(found)
    for name, f in extra.items():
        when = year(f['date'])
        if name in NOT_PLACES or not (f['camera'] and inside(*f['camera'], ring) and OPEN.match(f['licence'])
                and f['mime'].startswith('image/') and when and when < 1990
                and not NOT_A_PLACE.search(f'{name} {f["categories"]}')):
            continue
        title = f['name'] or re.sub(r'\.\w+$', '', name[5:])
        features.append(feature(*f['camera'], f, title, date=f['date'], azimuth=None, proof='camera', approx=True,
                                geotaggers=0, ajapaik=None, now=None))
    print(f'Commons: {len(found)} old photos near Slovakia, kept {sum(x["properties"]["proof"] == "camera" for x in features)}')

    before = len(features)
    features = drop_piles(features)
    print(f'dropped {before - len(features)} approximate photos piled on one spot')
    OUT.write_text(json.dumps({'type': 'FeatureCollection', 'features': features}, ensure_ascii=False, separators=(',', ':')))
    proofs = {k: sum(x['properties']['proof'] == k for x in features)
              for k in ('rephoto', 'geotags', 'commons', 'single', 'import', 'camera')}
    print(f'kept {len(features)} {proofs}, with a "now" photo {sum(bool(x["properties"]["now"]) for x in features)}, skipped {skipped}')


if __name__ == '__main__':
    main()
