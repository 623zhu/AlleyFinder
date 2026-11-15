from __future__ import annotations

import json
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

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

EXTRACT_WORKERS = 12

_log_lock = threading.Lock()


def _log(message: str) -> None:
    with _log_lock:
        print(message)


def extract_shops(city: str, title: str, url: str, text: str) -> list[dict]:
    raw = chat([
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt(city, title, url, text)},
    ])
    payload = json.loads(raw)
    shops = payload.get("shops") or []
    return shops if isinstance(shops, list) else []


def _extract_page(city: str, page: dict) -> tuple[list[dict], int, int]:
    text = page.get("summary") or page.get("snippet") or ""
    source = normalize(page["title"] + text)
    try:
        shops = extract_shops(city, page["title"], page["url"], text)
    except Exception as exc:
        _log(f"抽取失败 {page['url']}: {exc}")
        return [], 0, 0

    rows: list[dict] = []
    ok = 0
    bad = 0
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
    return rows, ok, bad


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
    done = 0
    workers = max(1, min(EXTRACT_WORKERS, len(batch)))
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(_extract_page, name, page) for page in batch]
        for future in as_completed(futures):
            page_rows, page_ok, page_bad = future.result()
            rows.extend(page_rows)
            ok += page_ok
            bad += page_bad
            done += 1
            emit(progress, "extracting", f"抽取 {done}/{len(batch)}")

    replace_mentions(name, rows)
    print(f"证据通过 {ok} 条，失败 {bad} 条")
    print(f"明细：{DB_PATH} mentions/{name}")
    return rows
