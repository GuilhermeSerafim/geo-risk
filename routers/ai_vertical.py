from fastapi import APIRouter
from services.ai_service import get_ai_answer
from services import session as session_store
from pydantic import BaseModel
from typing import Optional

router = APIRouter()


class AIQuery(BaseModel):
    pergunta: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    radius_m: float = 200.0
    session_id: Optional[str] = None
    create_session: Optional[bool] = False


@router.post("/ask-ai")
async def ask_ai(query: AIQuery):
    # session handling
    sid = query.session_id
    if query.create_session and not sid:
        # create a simple session id
        sid = f"s-{int(__import__('time').time())}"
        session_store.create_session(sid)

    # append user question to session if exists
    if sid:
        session_store.append_interaction(sid, "user", {"question": query.pergunta, "latitude": query.latitude, "longitude": query.longitude, "radius_m": query.radius_m})

    # call AI service with coordinates
    ai_resp = get_ai_answer(query.pergunta, latitude=query.latitude, longitude=query.longitude, radius_m=query.radius_m)

    # persist AI response in session
    if sid:
        session_store.append_interaction(sid, "ai", {"response": ai_resp})

    return {"session_id": sid, "response": ai_resp}
