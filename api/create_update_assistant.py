# create_update_assistant.py

from openai import OpenAI
import os
from assistant_instructions import instructions
from dotenv import load_dotenv

load_dotenv()
OPENAI_API_KEY = os.environ['OPEN_AI_API_KEY']
client = OpenAI(api_key=OPENAI_API_KEY)

def create_vector_store_with_files(paths):
    """
    Crea un vector store con archivos 'globales' si te interesa tener 
    una 'base' en file_search. Si no lo necesitas, puedes quitarlo.
    """
    vector_store_response = client.beta.vector_stores.create(name="Invention_files")
    vector_store_id = vector_store_response.id

    for path in paths:
        with open(path, "rb") as f:
            file_response = client.files.create(file=f, purpose="assistants")
            client.beta.vector_stores.files.create(vector_store_id=vector_store_id, file_id=file_response.id)
    with open("vector_store_id.txt", "w", encoding="utf-8") as vf:
        vf.write(vector_store_id)

    return vector_store_id

def create_or_update_assistant(file_paths):
    assistant_name = "ID1"  # nombre del assistant
    # Si deseas un store base, descomenta la línea:
    # vector_store_id = create_vector_store_with_files(file_paths)
    # Si no, pon None y no configures un store:
    vector_store_id = None

    existing_assistants = client.beta.assistants.list().data
    existing_assistant = next((a for a in existing_assistants if a.name == assistant_name), None)

    # Tools: Podrías conservar 'file_search' si quieres, o quitarla si ya no la usarás
    tools = [
        # {"type": "file_search"},
        {
            "type": "function",
            "function": {
                "name": "modify_document",
                "description": "Modify the latex document ...",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "Section": {"type": "string","description": "..."},
                        "Content": {"type": "string","description": "..."},
                    },
                    "required": ["Section", "Content"]
                }
            }
        }
    ]

    if existing_assistant:
        assistant_id = existing_assistant.id
        # Actualizamos
        if vector_store_id:
            updated_assistant = client.beta.assistants.update(
                assistant_id=assistant_id,
                instructions=instructions,
                tools=tools,
                tool_resources={
                    "file_search": {
                        "vector_store_ids": [vector_store_id]
                    }
                }
            )
            print(f"Updated existing assistant: {assistant_name}")
            return updated_assistant
        else:
            updated_assistant = client.beta.assistants.update(
                assistant_id=assistant_id,
                instructions=instructions,
                tools=tools,
            )
            print(f"Updated existing assistant (no file_search store): {assistant_name}")
            return updated_assistant
    else:
        # Creamos
        if vector_store_id:
            new_assistant = client.beta.assistants.create(
                name=assistant_name,
                instructions=instructions,
                model="gpt-3.5-turbo-0125",
                tools=tools,
                tool_resources={
                    "file_search": {"vector_store_ids": [vector_store_id]}
                }
            )
            print(f"Created new assistant with store: {assistant_name}")
            return new_assistant
        else:
            new_assistant = client.beta.assistants.create(
                name=assistant_name,
                instructions=instructions,
                model="gpt-3.5-turbo-0125",
                tools=tools
            )
            print(f"Created new assistant without store: {assistant_name}")
            return new_assistant
