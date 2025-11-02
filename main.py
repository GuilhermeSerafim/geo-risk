from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers.distance import router as distance_router
from routers.risk import router as risk_router
from routers.ai_vertical import router as ai_router
from routers.elevation import router as elevation_router
from routers.flood_stats import router as flood_stats_router
from routers.areas_rosa import router as areas_rosa_router

app = FastAPI(title="GeoRisk API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# incluir rotas
app.include_router(distance_router, prefix="/geo")
app.include_router(risk_router, prefix="/geo")
app.include_router(ai_router, prefix="/ai")
app.include_router(elevation_router, prefix="/geo")
app.include_router(flood_stats_router, prefix="/geo")
app.include_router(areas_rosa_router, prefix="/geo")
