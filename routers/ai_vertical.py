from fastapi import APIRouter
from services.ai_service import get_ai_assessment
from pydantic import BaseModel

router = APIRouter()

class Query(BaseModel):
    pergunta: str

@router.post("/ask-ai")
async def ask_ai(query: Query):
    resposta = get_ai_assessment(query.pergunta)
    return {"resposta": resposta}
