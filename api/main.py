from openai import OpenAI
import os
from dotenv import load_dotenv
from create_update_assistant import create_or_update_assistant
import document_manipulation
from flask import Flask, request, jsonify
import requests
import json
from flask_cors import CORS

# Load environment variables
load_dotenv('.env')
OPENAI_API_KEY = os.environ['OPEN_AI_API_KEY']
assistant_id = os.environ['ASSISTANT_ID']
file_paths = ["invention-disclosure-instructions.md", "invention-disclosure-structure.tex"]
client = OpenAI(api_key=OPENAI_API_KEY)

# Create or update the assistant
assistant = create_or_update_assistant(file_paths)

app = Flask(__name__)
CORS(app)


@app.route('/start', methods=['GET'])
def start_conversation():
    print("Starting a new conversation...")
    thread = client.beta.threads.create()
    print(f"New thread created with ID: {thread.id}")
    return jsonify({"thread_id": thread.id})

@app.route('/readTextFile', methods=['GET'])
def read_text_file():
    thread_id = request.args.get('thread_id')
    try:
        with open(f"generatedDocuments/{thread_id}.tex", 'r', encoding='utf-8') as file:
            content = file.read()
        return jsonify({"response": content}) 
    except FileNotFoundError:
        return jsonify({"response": ""})
    except Exception as e:
        return jsonify({f"error": e, "response": ""})
    
@app.route('/chat', methods=['POST'])
def chat():
    thread_id = request.form.get('thread_id')
    user_input = request.form.get('message', '')
    uploaded_files = request.files.getlist('files')
    files_info = []

    for file in uploaded_files:
        file_path = os.path.join('uploads', file.filename)
        file.save(file_path)

        # Leer el contenido antes de enviarlo
        with open(file_path, "r", encoding="utf-8") as f:
            file_content = f.read()
        print(f"📂 Contenido del archivo {file.filename}:\n{file_content[:500]}")

        # Subir el archivo a OpenAI correctamente
        with open(file_path, "rb") as f:
            my_file = client.files.create(file=f, purpose="assistants")
            files_info.append(my_file.id)
        print(f"✅ Archivo subido con éxito a OpenAI: {my_file.id}")

        os.remove(file_path)  # Eliminar archivo después de subirlo

    if not thread_id:
        print("Error: Missing thread_id")
        return jsonify({"error": "Missing thread_id"}), 400

    print(f"📨 Recibido mensaje: {user_input} para el thread ID: {thread_id}")

    # Verificar si hay archivos antes de agregarlos al mensaje
    attachments = [{"file_id": x, "tools": [{"type": "file_search"}]} for x in files_info] if files_info else []

    # Enviar el mensaje del usuario al asistente
    client.beta.threads.messages.create(
        thread_id=thread_id,
        role="user",
        content=user_input,
        attachments=attachments
    )

    # Crear y esperar la respuesta del asistente
    run = client.beta.threads.runs.create_and_poll(
        thread_id=thread_id,
        assistant_id=assistant.id,
    )

    if run.status == 'requires_action':
        tool_outputs = []
        for tool in run.required_action.submit_tool_outputs.tool_calls:
            if hasattr(tool, "function") and hasattr(tool.function, "name") and tool.function.name == 'modify_document':
                arguments = json.loads(tool.function.arguments)
                section = arguments['Section']
                content = arguments['Content']
                print(f"🔧 Function call modify_document: sección={section}, contenido={content}")
                response = modify_latex_document(section, content, thread_id)
                tool_outputs.append({
                    "tool_call_id": tool.id,
                    "output": json.dumps(response)
                })
        if tool_outputs:
            try:
                run = client.beta.threads.runs.submit_tool_outputs_and_poll(
                    thread_id=thread_id,
                    run_id=run.id,
                    tool_outputs=tool_outputs
                )
                print("✅ Tool outputs enviados correctamente.")
            except Exception as e:
                print(f"❌ Error al enviar tool outputs: {e}")

    # Manejo de la respuesta del asistente
    if run.status == 'completed':
        messages = client.beta.threads.messages.list(thread_id=thread_id)
        response_text = next(
            (msg.content[0].text.value for msg in messages.data
             if msg.role == 'assistant' and getattr(msg.content[0], "type", None) == "text"),
            "No assistant response found."
        )

        print(f"🤖 Respuesta del asistente: {response_text}")
        return jsonify({"response": response_text})
    else:
        print(f"⚠️ Error en la ejecución: {run.status}")
        return jsonify({"error": "Run did not complete successfully"}), 500


@app.route('/threadHistory', methods=['GET'])
def get_thread_history():
    thread_id = request.args.get('thread_id')
    url = f"https://api.openai.com/v1/threads/{thread_id}/messages"

    # Encabezados
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "OpenAI-Beta": "assistants=v2",
    }

    # Hacer la solicitud GET
    response = requests.get(url, headers=headers)

    # Manejo de la respuesta
    if response.status_code == 200:
        data = response.json()
        if isinstance(data.get('data'), list):
            data['data'] = data['data'][::-1] 

        return jsonify(data), 200

    else:
        return jsonify({
            "error": "Failed to fetch thread history",
            "details": response.text,
        }), response.status_code

@app.route('/listAssistants', methods=['GET'])
def list_available_assistants():
    try:
        assistants = client.beta.assistants.list().data
        for assistant in assistants:
            print(f"Assistant Name: {assistant.name}, ID: {assistant.id}")
        return [assistant.id for assistant in assistants]

    except Exception as e:
        print(f"Error retrieving assistants: {e}")
        return None

def modify_latex_document(section, new_content, thread_id):
    file_path = f"generatedDocuments/{thread_id}.tex"

    # Si el archivo no existe, crear uno vacío
    if not os.path.exists(file_path):
        with open(file_path, "w", encoding="utf-8") as f:
            f.write("% Documento LaTeX generado automáticamente\n\n")
        print(f"📄 Archivo {file_path} creado.")

    # 🔥 Normalizar el nombre de la sección
    normalized_section = normalize_section_name(section)

    if normalized_section == "UNDEFINED":
        print(f"⚠️ Sección desconocida: {section}")
        return {"error": f"Sección '{section}' no reconocida."}

    # Modificar documento
    document_manipulation.update_latex_section(normalized_section, new_content, thread_id)
    
    return {"success": f"Sección {normalized_section} actualizada correctamente"}

def normalize_section_name(input_text):
    prompt = f"""
    Actúa como un normalizador de palabras. Si te proporcionan una palabra o frase que significa "título", "propósito", "descripción detallada", "estado del arte", "concepción", "divulgación previa", "desarrollo", "programa o contrato", "testigos", "información relevante", devuélvela normalizada como "PURPOSE", "DETAILED_DESCRIPTION", "TECHNOLOGY_STATUS", "CONCEPTION", "PREPARING_DISCLOSURE", "DEVELOPMENT", "PROGRAM_CONTRACT", "WITNESSES", "RELEVANT_INFORMATION" respectivamente. Si no corresponde a ninguna de estas, responde "UNDEFINED".

    Ejemplo:
    Entrada: Title
    Respuesta: TITLE

    Entrada: Título
    Respuesta: TITLE

    Entrada: testigos
    Respuesta: WITNESSES

    Entrada: algo desconocido
    Respuesta: UNDEFINED

    Ahora, normaliza esta entrada:
    Entrada: {input_text}
    Respuesta:
    """
    
    # Llamada a la API de OpenAI
    response = client.Completion.create(
        engine="text-davinci-003",  # O el modelo adecuado según tu suscripción
        prompt=prompt,
        max_tokens=10,
        temperature=0  # Para asegurar consistencia en la respuesta
    )
    return response.choices[0].text.strip()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
