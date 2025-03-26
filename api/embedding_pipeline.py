# embedding_pipeline.py

import os
import shutil
import uuid
from langchain.document_loaders import PyPDFLoader
from langchain.text_splitter import CharacterTextSplitter
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.vectorstores import FAISS
from typing import Dict

# Diccionario en memoria -> { conversation_id: FAISS }
# En producción, podrías usar Pinecone u otra DB en vez de FAISS.
vectorstores: Dict[str, FAISS] = {}

def ingest_file(conversation_id: str, file_path: str) -> None:
    """
    Lee un PDF o texto, lo parte en trozos, genera embeddings y lo agrega
    al vectorstore de la conversación 'conversation_id'.
    """
    # Si la conv aún no tiene un store, la creamos vacía
    if conversation_id not in vectorstores or vectorstores[conversation_id] is None:
        vectorstores[conversation_id] = None  # temporal

    # Usamos PyPDFLoader como ejemplo. Si no es PDF, deberías
    # usar un loader distinto. O hacer autodetección.
    loader = PyPDFLoader(file_path)
    documents = loader.load()

    # Split
    text_splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
    docs_split = text_splitter.split_documents(documents)

    # Embeddings
    embeddings = OpenAIEmbeddings(openai_api_key=os.environ["OPENAI_API_KEY"])

    if vectorstores[conversation_id] is None:
        # Creamos un store FAISS desde cero
        db = FAISS.from_documents(docs_split, embeddings)
    else:
        # Agregamos a uno ya existente
        db = vectorstores[conversation_id]
        db.add_documents(docs_split)

    vectorstores[conversation_id] = db

def retrieve_relevant_chunks(conversation_id: str, user_query: str, k: int = 3):
    """
    Retorna los k chunks más relevantes para la query, 
    usando el vector store de 'conversation_id'.
    """
    if conversation_id not in vectorstores or vectorstores[conversation_id] is None:
        return []  # sin docs
    db = vectorstores[conversation_id]
    return db.similarity_search(user_query, k=k)
