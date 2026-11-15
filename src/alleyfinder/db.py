from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from alleyfinder.city import normalize_city

ROOT = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / "data" / "alleyfinder.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS mentions (
    id INTEGER PRIMARY KEY,
    city TEXT NOT NULL,
    name TEXT NOT NULL,
    evidence_ok INTEGER NOT NULL DEFAULT 0,
    url TEXT,
    payload TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_mentions_city ON mentions(city);

CREATE TABLE IF NOT EXISTS shops (
    id INTEGER PRIMARY KEY,
    city TEXT NOT NULL,
    poi_id TEXT,
    name_raw TEXT NOT NULL,
    payload TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_shops_city ON shops(city);

CREATE TABLE IF NOT EXISTS shortlist (
    id INTEGER PRIMARY KEY,
    city TEXT NOT NULL,
    poi_id TEXT,
    kept INTEGER NOT NULL,
    drop_reason TEXT,
    payload TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_shortlist_city ON shortlist(city);

CREATE TABLE IF NOT EXISTS reviews (
    id INTEGER PRIMARY KEY,
    city TEXT NOT NULL,
    poi_id TEXT,
    kept INTEGER NOT NULL,
    drop_reason TEXT,
    score REAL,
    payload TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_reviews_city ON reviews(city);

CREATE TABLE IF NOT EXISTS rankings (
    city TEXT NOT NULL,
    rank INTEGER NOT NULL,
    poi_id TEXT NOT NULL,
    payload TEXT NOT NULL,
    generated_at TEXT NOT NULL,
    PRIMARY KEY (city, rank)
);
CREATE INDEX IF NOT EXISTS idx_rankings_city_poi ON rankings(city, poi_id);
"""


def _city(raw: str) -> str:
    name = normalize_city(raw)
    if not name:
        raise ValueError("城市名不能为空")
    return name


def _dumps(row: dict) -> str:
    return json.dumps(row, ensure_ascii=False)


def _loads(payload: str) -> dict:
    return json.loads(payload)


@contextmanager
def connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    conn.executescript(SCHEMA)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _payloads(conn: sqlite3.Connection, sql: str, params: tuple) -> list[dict]:
    return [_loads(row["payload"]) for row in conn.execute(sql, params)]


def replace_mentions(city: str, rows: list[dict]) -> None:
    name = _city(city)
    with connect() as conn:
        conn.execute("DELETE FROM mentions WHERE city=?", (name,))
        conn.executemany(
            "INSERT INTO mentions(city, name, evidence_ok, url, payload) VALUES (?,?,?,?,?)",
            [
                (
                    name,
                    str(row.get("name") or "").strip(),
                    1 if row.get("evidence_ok") else 0,
                    row.get("url") or "",
                    _dumps(row),
                )
                for row in rows
            ],
        )


def load_mentions(city: str) -> list[dict]:
    name = _city(city)
    with connect() as conn:
        return _payloads(
            conn,
            "SELECT payload FROM mentions WHERE city=? ORDER BY id",
            (name,),
        )


def replace_shops(city: str, rows: list[dict]) -> None:
    name = _city(city)
    with connect() as conn:
        conn.execute("DELETE FROM shops WHERE city=?", (name,))
        conn.executemany(
            "INSERT INTO shops(city, poi_id, name_raw, payload) VALUES (?,?,?,?)",
            [
                (
                    name,
                    row.get("poi_id") or "",
                    str(row.get("name_raw") or "").strip(),
                    _dumps(row),
                )
                for row in rows
            ],
        )


def load_shops(city: str) -> list[dict]:
    name = _city(city)
    with connect() as conn:
        return _payloads(
            conn,
            "SELECT payload FROM shops WHERE city=? ORDER BY id",
            (name,),
        )


def replace_shortlist(city: str, kept: list[dict], dropped: list[dict]) -> None:
    name = _city(city)
    with connect() as conn:
        conn.execute("DELETE FROM shortlist WHERE city=?", (name,))
        conn.executemany(
            "INSERT INTO shortlist(city, poi_id, kept, drop_reason, payload) VALUES (?,?,?,?,?)",
            [
                *(
                    (name, row.get("poi_id") or "", 1, None, _dumps(row))
                    for row in kept
                ),
                *(
                    (
                        name,
                        row.get("poi_id") or "",
                        0,
                        row.get("drop_reason"),
                        _dumps(row),
                    )
                    for row in dropped
                ),
            ],
        )


def load_shortlist(city: str) -> list[dict]:
    name = _city(city)
    with connect() as conn:
        return _payloads(
            conn,
            "SELECT payload FROM shortlist WHERE city=? AND kept=1 ORDER BY id",
            (name,),
        )


def clear_reviews(city: str) -> None:
    name = _city(city)
    with connect() as conn:
        conn.execute("DELETE FROM reviews WHERE city=?", (name,))


def append_review(city: str, row: dict) -> None:
    name = _city(city)
    with connect() as conn:
        conn.execute(
            "INSERT INTO reviews(city, poi_id, kept, drop_reason, score, payload) VALUES (?,?,?,?,?,?)",
            (
                name,
                row.get("poi_id") or "",
                0 if row.get("drop_reason") else 1,
                row.get("drop_reason"),
                row.get("score"),
                _dumps(row),
            ),
        )


def replace_reviews(city: str, rows: list[dict]) -> None:
    name = _city(city)
    with connect() as conn:
        conn.execute("DELETE FROM reviews WHERE city=?", (name,))
        conn.executemany(
            "INSERT INTO reviews(city, poi_id, kept, drop_reason, score, payload) VALUES (?,?,?,?,?,?)",
            [
                (
                    name,
                    row.get("poi_id") or "",
                    0 if row.get("drop_reason") else 1,
                    row.get("drop_reason"),
                    row.get("score"),
                    _dumps(row),
                )
                for row in rows
            ],
        )


def replace_rankings(city: str, cards: list[dict]) -> None:
    name = _city(city)
    generated_at = datetime.now(timezone.utc).isoformat()
    with connect() as conn:
        conn.execute("DELETE FROM rankings WHERE city=?", (name,))
        conn.executemany(
            "INSERT INTO rankings(city, rank, poi_id, payload, generated_at) VALUES (?,?,?,?,?)",
            [
                (
                    name,
                    index,
                    card.get("poi_id") or "",
                    _dumps({**card, "rank": index}),
                    generated_at,
                )
                for index, card in enumerate(cards, start=1)
            ],
        )


def load_rankings(city: str) -> list[dict]:
    name = _city(city)
    with connect() as conn:
        return _payloads(
            conn,
            "SELECT payload FROM rankings WHERE city=? ORDER BY rank",
            (name,),
        )


def city_has_ranking(city: str) -> bool:
    name = normalize_city(city)
    if not name:
        return False
    with connect() as conn:
        row = conn.execute(
            "SELECT 1 FROM rankings WHERE city=? LIMIT 1",
            (name,),
        ).fetchone()
    return row is not None


def get_ranking_shop(city: str, poi_id: str) -> dict | None:
    name = _city(city)
    with connect() as conn:
        row = conn.execute(
            "SELECT payload FROM rankings WHERE city=? AND poi_id=?",
            (name, poi_id),
        ).fetchone()
    return _loads(row["payload"]) if row else None


def _read_jsonl(path: Path) -> list[dict]:
    rows: list[dict] = []
    if not path.is_file():
        return rows
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def import_jsonl_dir(city: str, src_dir: Path) -> None:
    src = Path(src_dir)
    mentions = _read_jsonl(src / "mentions.jsonl")
    shops = _read_jsonl(src / "shops.jsonl")
    shortlist = _read_jsonl(src / "shortlist.jsonl")
    screen_dropped = _read_jsonl(src / "screen_dropped.jsonl")
    reviews = _read_jsonl(src / "reviews.jsonl")
    ranked = _read_jsonl(src / "ranked.jsonl")
    if mentions:
        replace_mentions(city, mentions)
    if shops:
        replace_shops(city, shops)
    if shortlist or screen_dropped:
        replace_shortlist(city, shortlist, screen_dropped)
    if reviews:
        replace_reviews(city, reviews)
    if ranked:
        replace_rankings(city, ranked)
