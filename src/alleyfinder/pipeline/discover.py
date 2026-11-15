from __future__ import annotations

import json

from alleyfinder.clients import chat, search_web
from alleyfinder.db import DB_PATH, replace_mentions
from alleyfinder.pipeline.common import (
    ProgressFn,
    default_queries,
    emit,
    normalize,
    normalize_city,
)
from alleyfinder.prompts.extract import SYSTEM_PROMPT, user_prompt


def extract_shops(city: str, title: str, url: str, text: str) -> list[dict]:
    raw = chat([
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt(city, title, url, text)},
    ])
    payload = json.loads(raw)
    shops = payload.get("shops") or []
    return shops if isinstance(shops, list) else []


def discover_mentions(
    city: str,
    *,
    extract_n: int = 20,
    progress: ProgressFn = None,
) -> list[dict]:
    name = normalize_city(city)
    if not name:
        raise ValueError("城市名不能为空")

    pages: list[dict] = []
    seen: set[str] = set()
    for query in default_queries(name):
        print(f"搜索：{query}")
        emit(progress, "searching", f"搜索 {query}")
        for page in search_web(query, count=5):
            url = page["url"]
            if url in seen:
                continue
            seen.add(url)
            pages.append(page)
    print(f"去重后 {len(pages)} 篇")

    batch = pages if extract_n <= 0 else pages[:extract_n]
    emit(progress, "extracting", f"抽取 {len(batch)} 篇")
    rows: list[dict] = []
    ok = 0
    bad = 0

    for page in batch:
        text = page.get("summary") or page.get("snippet") or ""
        source = normalize(page["title"] + text)
        try:
            shops = extract_shops(name, page["title"], page["url"], text)
        except Exception as exc:
            print(f"抽取失败 {page['url']}: {exc}")
            continue

        for shop in shops:
            shop_name = str(shop.get("name") or "").strip()
            evidence = str(shop.get("evidence") or "").strip()
            if not shop_name:
                continue
            evidence_ok = bool(
                evidence
                and normalize(evidence) in source
                and normalize(shop_name) in source
            )
            if evidence_ok:
                ok += 1
            else:
                bad += 1
            rows.append({
                "name": shop_name,
                "evidence": evidence,
                "evidence_ok": evidence_ok,
                "title": page["title"],
                "url": page["url"],
                "shop": shop,
            })

    replace_mentions(name, rows)
    print(f"证据通过 {ok} 条，失败 {bad} 条")
    print(f"明细：{DB_PATH} mentions/{name}")
    return rows
