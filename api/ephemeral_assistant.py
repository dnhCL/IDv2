import os
from openai import OpenAI
from assistant_instructions import instructions  # Tus instrucciones base, si las tienes
from dotenv import load_dotenv
import shutil
import threading

# Cargamos las variables de entorno desde el archivo .env
load_dotenv()

# Accedemos a las variables de entorno
OPENAI_API_KEY = os.environ['OPEN_AI_API_KEY']
UPLOADS_PATH = os.environ['UPLOADS_PATH']
FILES_TO_UPLOAD_STRUCTURE_PATH = os.environ['FILES_TO_UPLOAD_STRUCTURE_PATH']
FILES_TO_UPLOAD_STRUCTURE_COPY_TO_LOCAL = os.environ['FILES_TO_UPLOAD_STRUCTURE_COPY_TO_LOCAL'] == 'True'
FILES_TO_UPLOAD_INSTRUCTIONS_PATH = os.environ['FILES_TO_UPLOAD_INSTRUCTIONS_PATH']
FILES_TO_UPLOAD_INSTRUCTIONS_COPY_TO_LOCAL = os.environ['FILES_TO_UPLOAD_INSTRUCTIONS_COPY_TO_LOCAL'] == 'True'
ASSISTANT_DURATION = os.environ['ASSISTANT_DURATION']

# Creamos el cliente OpenAI
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

    # Archivos a subir, ahora con las rutas y copias basadas en las variables de entorno
    FILES_TO_UPLOAD = [
        {
            "path": FILES_TO_UPLOAD_STRUCTURE_PATH,
            "copy_to_local": FILES_TO_UPLOAD_STRUCTURE_COPY_TO_LOCAL
        },
        {
            "path": FILES_TO_UPLOAD_INSTRUCTIONS_PATH,
            "copy_to_local": FILES_TO_UPLOAD_INSTRUCTIONS_COPY_TO_LOCAL
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
        tools=[{"type": "file_search"},
               {"type": "function", "function": {
                   "name": "modify_document",
                   "description": "Modify a LaTeX document section by replacing placeholder with given content.",
                   "parameters": {
                       "type": "object",
                       "properties": {
                           "Section": {"type": "string"},
                           "Content": {"type": "string"}
                       },
                       "required": ["Section", "Content"]
                   }
               }}],
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
    timer = threading.Timer(int(ASSISTANT_DURATION), end_ephemeral_conversation, [assistant_id, vector_store_id])
    timer.start()

    # Copiamos localmente SOLO el .tex para edición en frontend
    try:
        if FILES_TO_UPLOAD[0]["copy_to_local"]:  # Solo copiamos si se indica
            tex_file = FILES_TO_UPLOAD[0]["path"]  # Asumimos que el .tex es el primero
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
