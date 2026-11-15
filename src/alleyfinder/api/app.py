from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from alleyfinder.api.jobs import read_job, start_job
from alleyfinder.api.schemas import CitiesResponse, CityItem, JobStatus, RankingResponse, ShopCard
from alleyfinder.api.store import CITY_CATALOG, city_ready, get_shop, load_ranking
from alleyfinder.city import normalize_city

app = FastAPI(title="巷探", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


def _city_or_400(raw: str) -> str:
    city = normalize_city(raw)
    if not city:
        raise HTTPException(status_code=400, detail="城市名不能为空")
    return city


@app.get("/api/cities", response_model=CitiesResponse)
def list_cities() -> CitiesResponse:
    return CitiesResponse(
        cities=[CityItem(name=name, ready=city_ready(name)) for name in CITY_CATALOG]
    )


@app.get("/api/cities/{city}/ranking", response_model=RankingResponse)
def city_ranking(city: str) -> RankingResponse:
    name = _city_or_400(city)
    shops = load_ranking(name)
    if not shops:
        raise HTTPException(status_code=404, detail="榜单尚未生成")
    return RankingResponse(city=name, count=len(shops), shops=shops)


@app.get("/api/cities/{city}/shops/{poi_id}", response_model=ShopCard)
def shop_detail(city: str, poi_id: str) -> ShopCard:
    name = _city_or_400(city)
    shop = get_shop(name, poi_id)
    if shop is None:
        raise HTTPException(status_code=404, detail="这家店不在榜上")
    return shop


@app.post("/api/cities/{city}/jobs", response_model=JobStatus)
def create_city_job(city: str) -> JobStatus:
    name = _city_or_400(city)
    return JobStatus.model_validate(start_job(name))


@app.get("/api/cities/{city}/jobs", response_model=JobStatus)
def city_job(city: str) -> JobStatus:
    name = _city_or_400(city)
    return JobStatus.model_validate(read_job(name))


def serve() -> None:
    import uvicorn

    uvicorn.run("alleyfinder.api.app:app", host="127.0.0.1", port=8000, reload=True)
