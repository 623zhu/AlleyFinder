from __future__ import annotations

import re
from collections.abc import Callable

from alleyfinder.city import normalize_city

ProgressFn = Callable[[str, str], None] | None

__all__ = ["ProgressFn", "default_queries", "emit", "normalize", "normalize_city"]


def emit(progress: ProgressFn, stage: str, message: str = "") -> None:
    if progress:
        progress(stage, message)


def normalize(text: str) -> str:
    return re.sub(r"[\W_]+", "", text or "", flags=re.UNICODE).lower()


def default_queries(city: str) -> list[str]:
    name = normalize_city(city)
    return [
        f"{name} 苍蝇馆子",
        f"{name} 老店 小吃",
        f"{name} 本地人 推荐 小吃",
        f"{name} 巷子 美食",
        f"{name} 开了十几年 餐馆",
    ]
