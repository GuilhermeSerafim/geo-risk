from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough, RunnableLambda
from dotenv import load_dotenv
import numpy as np
import os

load_dotenv()

def get_ai_answer(question: str, latitude: float | None = None, longitude: float | None = None, radius_m: float = 200.0) -> str:
    # Carrega textos
    with open("data/flood_risk_brazil.txt", encoding="utf-8") as f1:
        txt1 = f1.read()
    with open("data/bart_flood_model.txt", encoding="utf-8") as f2:
        txt2 = f2.read()

    # Se foram passadas coordenadas, compute estatísticas locais
    obs_lines = []
    if latitude is not None and longitude is not None:
        try:
            from services import flood_stats, water_service

            # fixed data paths (same as routers)
            hand_path = "data/2024_urban_height_above_nearest_drainage_1-1-1_08814634-6bf1-40b4-a3f1-ca3f1dc98400.tif"
            coverage_path = "data/2023_coverage_coverage_10m_1-91-51_8884c309-3a9c-4619-8054-8cf1432fcf06.tif"
            coverage_value = 24

            mean_hand = flood_stats.mean_within_radius(hand_path, latitude, longitude, radius_m, band=1)
            pct_cov = flood_stats.percentage_equal_value_within_radius(coverage_path, latitude, longitude, radius_m, target_value=coverage_value, band=1)
            try:
                dist_m, idx, (rio_lon, rio_lat) = water_service.distance_to_water_info(longitude, latitude)
            except Exception:
                dist_m = None

            obs_lines.append(f"mean_hand_m: {mean_hand}")
            obs_lines.append(f"coverage_pct: {pct_cov}")
            obs_lines.append(f"distance_to_water_m: {dist_m}")
        except Exception as e:
            obs_lines.append(f"(erro ao calcular observações locais: {e})")

    obs_text = "\n".join(obs_lines)

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

    llm = ChatOpenAI(model="gpt-4o", temperature=0.2)
    # Inclui as observações locais (se houver) diretamente na pergunta para o LLM
    if obs_text:
        question_with_obs = f"Observações locais:\n{obs_text}\n\nPergunta original: {question}\n\nConsidere os textos fornecidos e responda de forma técnica, enfatizando se é uma boa ideia construir um modelo usando distância e altura como principais métricas e proponha um farol de risco (Baixo/Verde, Médio/Amarelo, Alto/Vermelho) com base nos limites mencionados em `flood_risk_brazil.txt`."
    else:
        question_with_obs = question

    prompt = PromptTemplate(
        input_variables=["context", "question"],
        template="Contexto:\n{context}\n\nPergunta: {question}\nResposta técnica:"
    )

    chain = ({"context": RunnableLambda(retrieve_context), "question": RunnablePassthrough()} |
             prompt | llm | StrOutputParser())

    return chain.invoke(question_with_obs)
