from fastapi import APIRouter
from pydantic import BaseModel
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.vectorstores import FAISS
from langchain_text_splitters import RecursiveCharacterTextSplitter
# preciso ajustar aqui
from langchain.chains import RetrievalQA # type: ignore
from langchain_core.prompts import PromptTemplate
from langchain_core.documents import Document
import os

router = APIRouter()

class Query(BaseModel):
    pergunta: str

# ---- Carrega textos com metadata por fonte ----
with open("data/flood_risk_brazil.txt", encoding="utf-8") as f1:
    txt1 = f1.read()
with open("data/bart_flood_model.txt", encoding="utf-8") as f2:
    txt2 = f2.read()

docs_raw = [
    Document(page_content=txt1, metadata={"source": "flood_risk_brazil.txt"}),
    Document(page_content=txt2, metadata={"source": "bart_flood_model.txt"}),
]

# ---- Split em chunks com metadata preservada ----
splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
docs = splitter.split_documents(docs_raw)

# ---- Embeddings + Chroma (reuso/persistência) ----
# 👉 O FAISS é uma alternativa leve (não precisa compilar nada) e roda 100% em Python.
# Não salva no disco, mas é super rápido e perfeito pra testes.
from langchain_community.vectorstores import FAISS  # precisa langchain-community instalado
embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
vector_db = FAISS.from_documents(docs, embeddings)
retriever = vector_db.as_retriever(search_kwargs={"k": 4})

# ---- PromptTemplate com context + question ----
prompt_template = PromptTemplate(
    input_variables=["context", "question"],
    template=(
        "Você é uma IA especializada em análise/modelagem de risco de alagamentos.\n"
        "Use APENAS as informações do contexto abaixo.\n\n"
        "Contexto:\n{context}\n\n"
        "Instruções:\n"
        "- Considere: distância de rios, altitude, queda relativa, declividade, tipo de solo,\n"
        "  impermeabilização, drenagem e chuva recente; cite classificações (Baixo/Médio/Alto)\n"
        "  conforme parâmetros dos documentos base.\n"
        "- Se pedir comparações, mencione onde BART se mostrou mais eficaz.\n"
        "- Se algo não estiver nos documentos, diga que não consta.\n\n"
        "Pergunta: {question}\n"
        "Resposta técnica (português, objetiva):"
    ),
)

llm = ChatOpenAI(model="gpt-4o", temperature=0.2)

qa_chain = RetrievalQA.from_chain_type(
    llm=llm,
    retriever=retriever,
    chain_type="stuff",
    chain_type_kwargs={"prompt": prompt_template},
    return_source_documents=True,
)

@router.post("/ask-ai")
async def ask_ai(query: Query):
    out = qa_chain.invoke({"query": query.pergunta})
    # ‘result’ é a chave padrão; em versões diferentes pode ser ‘answer’
    answer = out.get("result") or out.get("answer") or ""
    fontes = []
    for d in out.get("source_documents", []):
        fontes.append(d.metadata or {})
    return {"resposta": answer, "fontes": fontes}
