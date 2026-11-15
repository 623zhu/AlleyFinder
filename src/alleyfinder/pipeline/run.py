from __future__ import annotations

from alleyfinder.pipeline.common import ProgressFn, emit, normalize_city
from alleyfinder.pipeline.deep import deep_rank
from alleyfinder.pipeline.discover import discover_mentions
from alleyfinder.pipeline.match import match_pois
from alleyfinder.pipeline.screen import screen_shops


def run_pipeline(
    city: str,
    *,
    extract_n: int = 20,
    deep_limit: int = 0,
    progress: ProgressFn = None,
) -> list[dict]:
    name = normalize_city(city)
    if not name:
        raise ValueError("城市名不能为空")

    emit(progress, "searching", f"搜索 {name} 口碑")
    discover_mentions(name, extract_n=extract_n, progress=progress)

    emit(progress, "matching", "匹配地图位置")
    match_pois(name, progress=progress)

    emit(progress, "screening", "初筛短名单")
    screen_shops(name, progress=progress)

    emit(progress, "reviewing", "深筛口碑")
    ranked = deep_rank(name, limit=deep_limit, progress=progress)

    emit(progress, "done", "榜单已生成")
    return ranked
