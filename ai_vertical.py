from fastapi import APIRouter
from pydantic import BaseModel
from dotenv import load_dotenv
load_dotenv()  # carrega OPENAI_API_KEY do .env se existir

from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.prompts import PromptTemplate
from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough, RunnableLambda

import numpy as np
import os

router = APIRouter()

class Query(BaseModel):
    pergunta: str

# --------- Carrega textos base ----------
with open("data/flood_risk_brazil.txt", encoding="utf-8") as f1:
    txt1 = f1.read()
with open("data/bart_flood_model.txt", encoding="utf-8") as f2:
    txt2 = f2.read()

docs_raw = [
    Document(page_content=txt1, metadata={"source": "flood_risk_brazil.txt"}),
    Document(page_content=txt2, metadata={"source": "bart_flood_model.txt"}),
]

# --------- Split em chunks ----------
splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
docs = splitter.split_documents(docs_raw)
doc_texts = [d.page_content for d in docs]

# --------- Embeddings + index em memória ----------
embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

def _l2norm(v):
    v = np.asarray(v, dtype=np.float32)
    n = np.linalg.norm(v)
    return v if n == 0 else v / n

# gera vetores normalizados (uma vez no startup)
_doc_vecs = np.asarray([_l2norm(vec) for vec in embeddings.embed_documents(doc_texts)], dtype=np.float32)

def retrieve_context(question: str, k: int = 4) -> str:
    """Retorna um contexto concatenado dos k trechos mais similares ao question."""
    qvec = _l2norm(embeddings.embed_query(question))
    # cosine sim = dot( doc_vec, qvec ) porque ambos estão normalizados
    sims = _doc_vecs @ qvec
    idxs = np.argsort(-sims)[:k]
    selected = [docs[i].page_content for i in idxs]
    # você pode anexar metadata aqui se quiser (ex.: fonte)
    return "\n\n---\n\n".join(selected)

# --------- Prompt ----------
prompt_template = PromptTemplate(
    input_variables=["context", "question"],
    template=(
        "Você é uma IA especializada em análise e modelagem de risco de alagamentos.\n"
        "Use APENAS as informações do contexto abaixo.\n\n"
        "Contexto:\n{context}\n\n"
        "Instruções:\n"
        "- Considere fatores como: distância de rios, altitude, queda relativa, declividade, tipo de solo,\n"
        "  impermeabilização, drenagem e chuva recente.\n"
        "- Classifique o risco como Baixo, Médio ou Alto conforme os parâmetros dos documentos base.\n"
        "- Se pedir comparações, mencione onde o modelo BART se mostrou mais eficaz.\n"
        "- Se algo não estiver nos documentos, diga que não consta.\n\n"
        "Pergunta: {question}\n"
        "Resposta técnica e objetiva (em português):"
    ),
)

# --------- LLM + pipeline (runnables) ----------
llm = ChatOpenAI(model="gpt-4o", temperature=0.2)
output_parser = StrOutputParser()

qa_chain = (
    {"context": RunnableLambda(retrieve_context), "question": RunnablePassthrough()}
    | prompt_template
    | llm
    | output_parser
)

# --------- Endpoint ----------
@router.post("/ask-ai")
async def ask_ai(query: Query):
    resposta = qa_chain.invoke(query.pergunta)
    return {"resposta": resposta}



from fastapi import FastAPI

app = FastAPI(title="GeoRisk AI")
app.include_router(router)
