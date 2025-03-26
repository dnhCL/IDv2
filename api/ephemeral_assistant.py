# ephemeral_assistant.py

import os
from openai import OpenAI
from assistant_instructions import instructions  # Tus instrucciones base, si las tienes
from dotenv import load_dotenv

# Cargamos variables de entorno
load_dotenv()
OPENAI_API_KEY = os.environ['OPEN_AI_API_KEY']

# Creamos el cliente
client = OpenAI(api_key=OPENAI_API_KEY)


def start_ephemeral_conversation():
    """
    1) Crea un nuevo vector store.
    2) Crea un nuevo assistant que use ese vector store.
    3) Crea un nuevo hilo (thread).
    4) Devuelve (thread_id, assistant_id, vector_store_id).
    """
    # (A) Creamos el vector store
    vector_store_response = client.beta.vector_stores.create(name="EphemeralStore")
    vector_store_id = vector_store_response.id

    # (B) Creamos un assistant que use ese vector store para file_search
    new_assistant = client.beta.assistants.create(
        name="EphemeralAssistant",  # Puedes ponerle otro nombre
        instructions=instructions,  # Si tienes un string con tus system prompts
        model="gpt-3.5-turbo-0125",
        tools=[{"type": "file_search"}],
        tool_resources={
            "file_search": {
                "vector_store_ids": [vector_store_id]
            }
        }
    )
    assistant_id = new_assistant.id

    # (C) Creamos el thread
    thread = client.beta.threads.create()
    thread_id = thread.id

    return thread_id, assistant_id, vector_store_id


def end_ephemeral_conversation(assistant_id: str, vector_store_id: str):
    """
    Elimina el assistant y el vector store, para que no quede nada guardado.
    """
    # (1) Borramos el asistente
    client.beta.assistants.delete(assistant_id=assistant_id)

    # (2) Borramos el vector store
    client.beta.vector_stores.delete(vector_store_id=vector_store_id)
