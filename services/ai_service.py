from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough, RunnableLambda
from dotenv import load_dotenv
import numpy as np
import os

load_dotenv()

def get_ai_answer(question: str) -> str:
    # Carrega textos
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

    llm = ChatOpenAI(model="gpt-4o", temperature=0.2)
    prompt = PromptTemplate(
        input_variables=["context", "question"],
        template="Contexto:\n{context}\n\nPergunta: {question}\nResposta técnica:"
    )

    chain = ({"context": RunnableLambda(retrieve_context), "question": RunnablePassthrough()} |
             prompt | llm | StrOutputParser())

    return chain.invoke(question)
