from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers.distance import router as distance_router
from routers.risk import router as risk_router
from routers.ai_vertical import router as ai_router

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

# ==========================
# HEALTH / PING ROUTE
# ==========================
@app.get("/ping", tags=["Health"])
def ping():
    return {
        "status": "ok",
        "service": "GeoRisk API"
    }