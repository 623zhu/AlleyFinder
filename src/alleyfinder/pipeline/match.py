from __future__ import annotations

import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from alleyfinder.clients import search_poi
from alleyfinder.db import DB_PATH, load_mentions, replace_shops
from alleyfinder.pipeline.common import ProgressFn, emit, normalize, normalize_city

GAODE_WORKERS = 8

_log_lock = threading.Lock()


def _log(message: str) -> None:
    with _log_lock:
        print(message)


def _pois_for(shop_name: str, city: str) -> list[dict]:
    last: Exception | None = None
    for attempt in range(3):
        try:
            return search_poi(shop_name, city)
        except Exception as exc:
            last = exc
            msg = str(exc)
            if attempt < 2 and ("CUQPS" in msg or "10021" in msg):
                time.sleep(0.4 * (attempt + 1))
                continue
            _log(f"高德失败 {shop_name}: {exc}")
            return []
    _log(f"高德失败 {shop_name}: {last}")
    return []


def _match_one(shop_name: str, city: str) -> dict | None:
    pois = _pois_for(shop_name, city)
    if not pois:
        _log(f"[未匹配] {shop_name}")
        return None

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
    _log(f"[匹配] {shop_name} → {poi.get('name')} ({poi.get('address')})")
    return record


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
    done = 0
    shop_names = list(names.values())
    workers = max(1, min(GAODE_WORKERS, len(shop_names)))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(_match_one, shop_name, name) for shop_name in shop_names]
        for future in as_completed(futures):
            record = future.result()
            done += 1
            emit(progress, "matching", f"匹配 {done}/{len(shop_names)}")
            if record is None:
                missed += 1
                continue
            records.append(record)
            matched += 1

    replace_shops(name, records)
    print(f"匹配 {matched}，未匹配 {missed}")
    print(f"结果：{DB_PATH} shops/{name}")
    return records
