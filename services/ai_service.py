# services/ai_service.py
from typing import Literal
import numpy as np
from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnablePassthrough, RunnableLambda
from pydantic import BaseModel, Field

load_dotenv()

class RiskAssessment(BaseModel):
    # use 'medio' sem acento para evitar problemas de encoding
    risk_level: Literal["baixo", "medio", "alto"] = Field(
        description="Escolha EXATAMENTE UM: 'baixo', 'medio' ou 'alto'."
    )
    explanation: str = Field(
        description="Resumo técnico conciso (3-6 frases) em PT-BR justificando a classificação final."
    )

def get_ai_assessment(question: str) -> RiskAssessment:
    # ===== RAG básico (igual ao seu get_ai_answer) =====
    with open("data/flood_risk_brazil.txt", encoding="utf-8") as f1:
        txt1 = f1.read()
    with open("data/bart_flood_model.txt", encoding="utf-8") as f2:
        txt2 = f2.read()

    from langchain_core.documents import Document
    docs = [Document(page_content=txt1), Document(page_content=txt2)]
    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    docs = splitter.split_documents(docs)
    doc_texts = [d.page_content for d in docs]

    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
    vectors = np.array(embeddings.embed_documents(doc_texts), dtype=np.float32)

    def retrieve_context(q):
        qvec = np.array(embeddings.embed_query(q))
        sims = np.dot(vectors, qvec) / (np.linalg.norm(vectors, axis=1) * np.linalg.norm(qvec))
        top_k = np.argsort(-sims)[:3]
        return "\n\n".join([doc_texts[i] for i in top_k])
    # ===================================================

    llm = ChatOpenAI(model="gpt-4o", temperature=0.1)

    # Enforce JSON estruturado com o schema do Pydantic
    structured_llm = llm.with_structured_output(RiskAssessment)

    prompt = PromptTemplate(
        input_variables=["context", "question"],
        template=(
            "Você é um hidrólogo. Use o contexto para decidir um NÍVEL ÚNICO de risco final.\n\n"
            "Regras:\n"
            "- No campo 'risk_level', escolha EXATAMENTE UM entre: 'baixo', 'medio', 'alto'.\n"
            "- A decisão final deve considerar a distância ao rio, queda relativa e o contexto técnico.\n"
            "- No campo 'explanation', explique de forma técnica e objetiva (3-6 frases), em PT-BR.\n"
            "- Não inclua nenhum texto fora do JSON.\n\n"
            "Contexto técnico:\n{context}\n\n"
            "Pergunta:\n{question}\n"
        )
    )

    chain = (
        {"context": RunnableLambda(retrieve_context), "question": RunnablePassthrough()}
        | prompt
        | structured_llm
    )

    return chain.invoke(question)
