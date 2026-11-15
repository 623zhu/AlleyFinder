from __future__ import annotations

from alleyfinder.api.schemas import ShopCard
from alleyfinder.city import normalize_city
from alleyfinder.db import city_has_ranking, get_ranking_shop, load_rankings

CITY_CATALOG = ("成都", "广州", "武汉")


def known_city(city: str) -> bool:
    return bool(normalize_city(city))


def city_ready(city: str) -> bool:
    return city_has_ranking(city)


def _as_card(row: dict, rank: int) -> ShopCard:
    score = row.get("score")
    if isinstance(score, (int, float)):
        row = {**row, "score": round(float(score), 1)}
    row["rank"] = rank
    return ShopCard.model_validate(row)


def load_ranking(city: str) -> list[ShopCard]:
    return [_as_card(row, index) for index, row in enumerate(load_rankings(city), start=1)]


def get_shop(city: str, poi_id: str) -> ShopCard | None:
    row = get_ranking_shop(city, poi_id)
    if row is None:
        return None
    rank = row.get("rank")
    if not isinstance(rank, int):
        rank = 0
    return _as_card(row, rank)
