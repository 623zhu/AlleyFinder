from pydantic import BaseModel, ConfigDict, Field


class Evidence(BaseModel):
    model_config = ConfigDict(extra="ignore")

    quote: str = ""
    url: str = ""


class ShopCard(BaseModel):
    model_config = ConfigDict(extra="ignore")

    rank: int
    name: str = ""
    name_raw: str = ""
    poi_id: str = ""
    address: str = ""
    district: str = ""
    cityname: str = ""
    type: str = ""
    lng: str = ""
    lat: str = ""
    score: float | None = None
    reason: str = ""
    dishes: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)
    taste: str | None = None
    environment: str | None = None
    price: str | None = None
    price_hint: str | None = None
    is_old_shop: bool | None = None
    n_pages: int | None = None
    n_body: int | None = None
    n_summary: int | None = None
    urls: list[str] = Field(default_factory=list)


class CityItem(BaseModel):
    name: str
    ready: bool


class CitiesResponse(BaseModel):
    cities: list[CityItem]


class RankingResponse(BaseModel):
    city: str
    count: int
    shops: list[ShopCard]
