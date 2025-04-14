# ephemeral_assistant.py

import os
from openai import OpenAI
from assistant_instructions import instructions  # Tus instrucciones base, si las tienes
from dotenv import load_dotenv
import shutil
import threading


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
    # (A) Creamos vector store
    vs_response = client.beta.vector_stores.create(name="EphemeralStore")
    vector_store_id = vs_response.id
    print(f"[start_ephemeral_conversation] Created vector store: {vector_store_id}")

    # Archivos a subir
    # "path": "E:/Daniel/ID_ICONO/InvestigationDisclosureAI-main/api/invention-disclosure-structure.tex",
    # "path": "E:/Daniel/ID_ICONO/InvestigationDisclosureAI-main/api/invention-disclosure-instructions.md",
    FILES_TO_UPLOAD = [
        {
            "path": "C:/Users/Alienware/Desktop/Proyectos software/IDv2-test-file/api/invention-disclosure-structure.tex",
            "copy_to_local": True  # solo este debe guardarse como .tex para editar en frontend
        },
        {
            "path": "C:/Users/Alienware/Desktop/Proyectos software/IDv2-test-file/api/invention-disclosure-instructions.md",
            "copy_to_local": False
        }
    ]

    # Subimos los archivos al vector store
    for file_info in FILES_TO_UPLOAD:
        path = file_info["path"]
        try:
            with open(path, "rb") as f:
                file_response = client.files.create(file=f, purpose="assistants")
                file_id = file_response.id
                print(f"[start_ephemeral_conversation] Uploaded file {path} with ID: {file_id}")

                client.beta.vector_stores.files.create(
                    vector_store_id=vector_store_id,
                    file_id=file_id
                )
                print(f"[start_ephemeral_conversation] Associated file to vector store")
        except Exception as e:
            print(f"[start_ephemeral_conversation] ERROR uploading file '{path}': {e}")

    # (C) Creamos el assistant
    new_assistant = client.beta.assistants.create(
        name="EphemeralAssistant",
        instructions=instructions,
        model="gpt-4o",
        tools=[
            {"type": "file_search"},
            {
                "type": "function",
                "function": {
                    "name": "modify_document",
                    "description": "Modify a LaTeX document section by replacing placeholder with given content.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "Section": {"type": "string"},
                            "Content": {"type": "string"},
                        },
                        "required": ["Section", "Content"]
                    }
                }
            }
        ]
        ,
        tool_resources={
            "file_search": {
                "vector_store_ids": [vector_store_id]
            }
        }
    )
    assistant_id = new_assistant.id

    # Creamos el thread
    thread = client.beta.threads.create()
    thread_id = thread.id
    print(f"[start_ephemeral_conversation] Created thread: {thread_id}")

    # (E) Programar la eliminación del asistente después de 2 horas (7200 segundos)
    timer = threading.Timer(240, end_ephemeral_conversation, [assistant_id, vector_store_id])
    timer.start()

    # Copiamos localmente SOLO el .tex para edición en frontend
    try:
        tex_file = FILES_TO_UPLOAD[0]["path"]  # asumimos que es el primero
        os.makedirs("generatedDocuments", exist_ok=True)
        local_copy = f"generatedDocuments/{thread_id}.tex"
        shutil.copyfile(tex_file, local_copy)
        print(f"[start_ephemeral_conversation] Copied LaTeX to: {local_copy}")
    except Exception as e:
        print(f"[start_ephemeral_conversation] ERROR copying LaTeX locally: {e}")


    return thread_id, assistant_id, vector_store_id



def end_ephemeral_conversation(assistant_id: str, vector_store_id: str):
    """
    Elimina el assistant y el vector store, para que no quede nada guardado.
    """
    # (1) Borramos el asistente
    client.beta.assistants.delete(assistant_id=assistant_id)

    # (2) Borramos el vector store
    client.beta.vector_stores.delete(vector_store_id=vector_store_id)
