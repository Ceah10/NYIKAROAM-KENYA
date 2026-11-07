from pydantic import BaseModel, Field

class RegisterIn(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    email: str = Field(min_length=5, max_length=160)
    password: str = Field(min_length=8, max_length=128)

class LoginIn(BaseModel):
    email: str
    password: str

class RecommendIn(BaseModel):
    interests: list[str] = []
    budget: int = Field(ge=0, le=1000000)
    travel_style: str = "Any"
    county: str = "Any"

class FeedbackIn(BaseModel):
    destination_id: int
    rating: int = Field(ge=1, le=5)
    comment: str = Field(default="", max_length=1000)

class DestinationIn(BaseModel):
    name: str
    county: str
    category: str
    description: str
    animals: str = ""
    activities: str = ""
    best_time: str = ""
    budget_min: int = Field(ge=0)
    budget_max: int = Field(ge=0)
    latitude: float
    longitude: float
    image_url: str
    featured: bool = False
