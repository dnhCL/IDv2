from openai import OpenAI
import os
from dotenv import load_dotenv
import document_manipulation
from flask import Flask, request, jsonify
import requests
import json
from flask_cors import CORS
from ephemeral_assistant import start_ephemeral_conversation, end_ephemeral_conversation



# Carga variables de entorno
load_dotenv('.env')
OPENAI_API_KEY = os.environ['OPEN_AI_API_KEY']

# Creamos cliente
client = OpenAI(api_key=OPENAI_API_KEY)

app = Flask(__name__)
CORS(app)



# --------------------------------------------------------------------------------
# 2) Endpoints
# --------------------------------------------------------------------------------

@app.route('/start', methods=['GET'])
def start_conversation():
    """
    - Crea un vector store, un assistant y un thread EFÍMEROS (desde módulo externo).
    - Devuelve: thread_id, assistant_id, vector_store_id
    """
    print("[/start] Starting new ephemeral conversation...")
    thread_id, assistant_id, vector_store_id = start_ephemeral_conversation()
    print(f"[/start] ephemeral conversation: thread_id={thread_id}, assistant_id={assistant_id}, vector_store_id={vector_store_id}")

    return jsonify({
        "thread_id": thread_id,
        "assistant_id": assistant_id,
        "vector_store_id": vector_store_id
    })



@app.route('/end', methods=['POST'])
def end_conversation():
    """
    - Recibe assistant_id, vector_store_id
    - Elimina assistant y vector store, para que no quede nada guardado
    """
    assistant_id = request.form.get('assistant_id')
    vector_store_id = request.form.get('vector_store_id')

    if not assistant_id or not vector_store_id:
        print("[/end] Missing IDs")
        return jsonify({"error": "Missing assistant_id or vector_store_id"}), 400

    print(f"[/end] Ending ephemeral conversation for assistant_id={assistant_id}, vector_store_id={vector_store_id}")
    end_ephemeral_conversation(assistant_id, vector_store_id)
    return jsonify({"success": True, "message": "Conversation ended. Assistant & vector store deleted."})


@app.route('/chat', methods=['POST'])
def chat():
    """
    Endpoint principal para enviar mensajes de usuario a la IA.
    Requiere:
      - thread_id
      - assistant_id
      - vector_store_id
      - message (texto del usuario)
      - (Opcional) files
    Subimos archivos a la API, los indexamos en 'vector_store_id',
    y enviamos el mensaje. Hacemos poll hasta obtener respuesta.
    """
    thread_id = request.form.get('thread_id')
    assistant_id = request.form.get('assistant_id')
    vector_store_id = request.form.get('vector_store_id')
    user_input = request.form.get('message', '')

    if not thread_id or not assistant_id or not vector_store_id:
        print("[/chat] Error: missing one of thread_id, assistant_id, vector_store_id")
        return jsonify({"error": "Missing required IDs"}), 400

    uploaded_files = request.files.getlist('files')
    files_info = []

    # Subimos cada archivo y lo asociamos al vector store
    for file in uploaded_files:
        file_path = os.path.join('uploads', file.filename)
        file.save(file_path)
        print(f"[/chat] Saved file: {file_path}")

        # 1) Subir a OpenAI
        my_file = client.files.create(file=open(file_path, "rb"), purpose="assistants")
        file_id = my_file.id
        files_info.append(file_id)
        print(f"[/chat] Created file in OpenAI: {file_id}")

        # 2) Asociar al vector store
        client.beta.vector_stores.files.create(
            vector_store_id=vector_store_id,
            file_id=file_id
        )
        print(f"[/chat] Added file {file_id} to vector store {vector_store_id}")

    print(f"[/chat] Received message: '{user_input}' for thread ID: {thread_id}, assistant ID: {assistant_id}")

    # Creamos el mensaje del usuario
    client.beta.threads.messages.create(
        thread_id=thread_id,
        role="user",
        content=user_input,
        attachments=[
            {"file_id": fid, "tools": [{"type": "file_search"}]}
            for fid in files_info
        ]
    )

    # Iniciamos un 'run'
    run = client.beta.threads.runs.create_and_poll(
        thread_id=thread_id,
        assistant_id=assistant_id,
    )

    # Si la IA requiere function calls
    if run.status == 'requires_action':
        print("[/chat] Run requires_action -> function calls")
        tool_outputs = []
        for tool_call in run.required_action.submit_tool_outputs.tool_calls:
            if tool_call.function.name == 'modify_document':
                arguments = json.loads(tool_call.function.arguments)
                section = arguments['Section']
                content = arguments['Content']
                print(f"[modify_document] Called with section='{section}', content='{content}'")

                response = modify_latex_document(section, content, thread_id)
                if "error" in response:
                    print(f"[modify_document] Error in section={section}")
                    tool_outputs.append({
                        "tool_call_id": tool_call.id,
                        "output": json.dumps({"error": f"Failed for section {section}"})
                    })
                else:
                    tool_outputs.append({
                        "tool_call_id": tool_call.id,
                        "output": json.dumps(response)
                    })

        # Enviamos resultados de las tool calls
        if tool_outputs:
            try:
                run = client.beta.threads.runs.submit_tool_outputs_and_poll(
                    thread_id=thread_id,
                    run_id=run.id,
                    tool_outputs=tool_outputs
                )
                print("[/chat] Tool outputs submitted successfully.")
            except Exception as e:
                print(f"[/chat] Failed to submit tool outputs: {e}")

    if run.status == 'completed':
        print("[/chat] Run completed, retrieving final assistant response...")
        messages = client.beta.threads.messages.list(thread_id=thread_id)
        response_text = None
        for message in messages.data:
            if message.role == 'assistant' and 'text' in message.content[0].type:
                response_text = message.content[0].text.value
                break

        if response_text is None:
            response_text = "[No assistant response found]"
        print(f"[/chat] Assistant response: {response_text}")
        return jsonify({"response": response_text})

    else:
        print(f"[/chat] Run did NOT complete, status = {run.status}")
        return jsonify({"error": "Run did not complete successfully"}), 500


@app.route('/readTextFile', methods=['GET'])
def read_text_file():
    """
    Lee un archivo .tex (por ejemplo, cuando la IA modifica secciones),
    y devuelve su contenido al frontend.
    """
    thread_id = request.args.get('thread_id')
    try:
        with open(f"generatedDocuments/{thread_id}.tex", 'r', encoding='utf-8') as file:
            content = file.read()
        return jsonify({"response": content})
    except FileNotFoundError:
        print("[readTextFile] No .tex file found for this thread")
        return jsonify({"response": ""})
    except Exception as e:
        print(f"[readTextFile] Error reading file: {e}")
        return jsonify({"error": str(e), "response": ""})


@app.route('/threadHistory', methods=['GET'])
def get_thread_history():
    """
    Devuelve el historial de mensajes para un thread dado.
    """
    thread_id = request.args.get('thread_id')
    url = f"https://api.openai.com/v1/threads/{thread_id}/messages"

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "OpenAI-Beta": "assistants=v2",
    }

    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        data = response.json()
        if isinstance(data.get('data'), list):
            data['data'] = data['data'][::-1]  # invertir para ver más recientes arriba
        return jsonify(data), 200
    else:
        print("[threadHistory] Error fetching thread history: ", response.text)
        return jsonify({
            "error": "Failed to fetch thread history",
            "details": response.text,
        }), response.status_code


@app.route('/listAssistants', methods=['GET'])
def list_available_assistants():
    """
    Lista todos los asistentes creados en tu cuenta, para debugging.
    """
    try:
        assistants = client.beta.assistants.list().data
        for asst in assistants:
            print(f"Assistant Name: {asst.name}, ID: {asst.id}")
        # Devolvemos la lista de IDs
        return jsonify([asst.id for asst in assistants])
    except Exception as e:
        print(f"[listAssistants] Error retrieving assistants: {e}")
        return jsonify({"error": str(e)}), 500


SECTION_MAP = {
    "AUTHORS": "RESEARCHER",
    "AUTHOR": "RESEARCHER",
    "RESEARCHERS": "RESEARCHER",
    "INVESTIGADORES": "RESEARCHER",
    "TITULO": "TITLE",
    "TÍTULO": "TITLE",
    "PROPÓSITO": "PURPOSE"
    
}

def modify_latex_document(section, new_content, thread_id):

    std_section = section.upper().replace(" ", "_").replace("<<", "").replace(">>", "")
    std_section = SECTION_MAP.get(std_section, std_section)

    print(f"[modify_latex_document] Modifying section: {std_section}")
    document_manipulation.update_latex_section(std_section, new_content, thread_id)
    return {"success": True}




if __name__ == '__main__':
    print("[main] Starting Flask server...")
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))

