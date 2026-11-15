from __future__ import annotations

import time

from alleyfinder.clients import search_poi
from alleyfinder.db import DB_PATH, load_mentions, replace_shops
from alleyfinder.pipeline.common import ProgressFn, emit, normalize, normalize_city


def match_pois(
    city: str,
    *,
    progress: ProgressFn = None,
) -> list[dict]:
    name = normalize_city(city)
    mentions = load_mentions(name)
    if not mentions:
        raise RuntimeError(f"缺少 {name} 的提及数据，请先跑搜索抽取")

    names: dict[str, str] = {}
    for row in mentions:
        shop_name = str(row.get("name") or "").strip()
        if not shop_name:
            continue
        names.setdefault(normalize(shop_name), shop_name)

    print(f"去重后 {len(names)} 个店名")
    emit(progress, "matching", f"匹配 {len(names)} 个店名")
    records: list[dict] = []
    matched = 0
    missed = 0

    for shop_name in names.values():
        try:
            pois = search_poi(shop_name, name)
        except Exception as exc:
            print(f"高德失败 {shop_name}: {exc}")
            pois = []
        time.sleep(0.2)

        if not pois:
            missed += 1
            print(f"[未匹配] {shop_name}")
            continue

        poi = pois[0]
        lng, _, lat = (poi.get("location") or ",").partition(",")
        record = {
            "name_raw": shop_name,
            "poi_id": poi.get("id"),
            "name": poi.get("name"),
            "address": poi.get("address"),
            "district": poi.get("district"),
            "cityname": poi.get("cityname"),
            "type": poi.get("type"),
            "lng": lng,
            "lat": lat,
        }
        records.append(record)
        matched += 1
        print(f"[匹配] {shop_name} → {poi.get('name')} ({poi.get('address')})")

    replace_shops(name, records)
    print(f"匹配 {matched}，未匹配 {missed}")
    print(f"结果：{DB_PATH} shops/{name}")
    return records
