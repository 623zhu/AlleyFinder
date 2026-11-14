from pathlib import Path
import json
import re
import time
from alleyfinder.clients import search_poi

ROOT = Path(__file__).resolve().parents[1]
MENTIONS = ROOT / "data" / "spike_wuhan" / "mentions.jsonl"
OUT = ROOT / "data" / "spike_wuhan" / "shops.jsonl"
CITY = "武汉"

def normalize(text: str) -> str:
    return re.sub(r"[\W_]+", "", text or "", flags=re.UNICODE).lower()

def main() -> None:
    names: dict[str, str] = {}
    with MENTIONS.open(encoding="utf-8") as f:
        for line in f:
            row = json.loads(line)
            name = str(row.get("name") or "").strip()
            if not name:
                continue
            key = normalize(name)
            # key 存在就写入，不存在就不动
            names.setdefault(key, name)

    print(f"去重后 {len(names)} 个店名")
    matched = 0
    missed = 0

    with OUT.open("w", encoding="utf-8") as out:
        for name in names.values():
            try:
                pois = search_poi(name, CITY)
            except Exception as exc:
                print(f"高德失败 {name}: {exc}")
                pois = []
            time.sleep(0.2)  # 避免 QPS 超限

            if not pois:
                missed += 1
                print(f"[未匹配] {name}")
                continue

            poi = pois[0]
            lng, _, lat = (poi.get("location") or ",").partition(",")
            record = {
                "name_raw": name,
                "poi_id": poi.get("id"),
                "name": poi.get("name"),
                "address": poi.get("address"),
                "district": poi.get("district"),
                "cityname": poi.get("cityname"),
                "type": poi.get("type"),
                "lng": lng,
                "lat": lat,
            }
            out.write(json.dumps(record, ensure_ascii=False) + "\n")
            matched += 1
            print(f"[匹配] {name} → {poi.get('name')} ({poi.get('address')})")

    print(f"匹配 {matched}，未匹配 {missed}")
    print(f"结果：{OUT}")

if __name__ == "__main__":
    main()