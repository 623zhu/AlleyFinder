from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from alleyfinder.api.schemas import CitiesResponse, CityItem, RankingResponse, ShopCard
from alleyfinder.api.store import CITY_CATALOG, city_ready, get_shop, known_city, load_ranking
from alleyfinder.city import normalize_city

app = FastAPI(title="巷探", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_methods=["GET"],
    allow_headers=["*"],
)


def _city_or_404(raw: str) -> str:
    city = normalize_city(raw)
    if not city or not known_city(city):
        raise HTTPException(status_code=404, detail="这座城市还没探到")
    return city


@app.get("/api/cities", response_model=CitiesResponse)
def list_cities() -> CitiesResponse:
    return CitiesResponse(
        cities=[CityItem(name=name, ready=city_ready(name)) for name in CITY_CATALOG]
    )


@app.get("/api/cities/{city}/ranking", response_model=RankingResponse)
def city_ranking(city: str) -> RankingResponse:
    name = _city_or_404(city)
    shops = load_ranking(name)
    if not shops:
        raise HTTPException(status_code=404, detail="榜单尚未生成")
    return RankingResponse(city=name, count=len(shops), shops=shops)


@app.get("/api/cities/{city}/shops/{poi_id}", response_model=ShopCard)
def shop_detail(city: str, poi_id: str) -> ShopCard:
    name = _city_or_404(city)
    shop = get_shop(name, poi_id)
    if shop is None:
        raise HTTPException(status_code=404, detail="这家店不在榜上")
    return shop


def serve() -> None:
    import uvicorn

    uvicorn.run("alleyfinder.api.app:app", host="127.0.0.1", port=8000, reload=True)
