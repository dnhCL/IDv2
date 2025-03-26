# main.py

from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import openai
import uuid
from dotenv import load_dotenv
import document_manipulation
from embedding_pipeline import ingest_file, retrieve_relevant_chunks

load_dotenv()
OPENAI_API_KEY = os.environ["OPEN_AI_API_KEY"]
openai.api_key = OPENAI_API_KEY

app = Flask(__name__)
CORS(app)

# Diccionario para simular la conversacion: { conversation_id: [messages] }
conversation_messages = {}

@app.route("/start", methods=["GET"])
def start_conversation():
    """
    Crea un conversation_id único en nuestro pipeline.
    """
    conv_id = str(uuid.uuid4())
    conversation_messages[conv_id] = []
    return jsonify({"conversation_id": conv_id})

@app.route("/upload", methods=["POST"])
def upload_file():
    """
    Subir uno o varios archivos para la conversación.
    Tomamos conversation_id y convertimos el PDF (o lo que sea) a texto y lo indexamos.
    """
    conv_id = request.form.get("conversation_id")
    if not conv_id:
        return jsonify({"error":"Missing conversation_id"}), 400

    # Extraer archivos
    files = request.files.getlist("files")
    if not files:
        return jsonify({"error":"No files uploaded"}), 400

    for f in files:
        file_path = os.path.join("uploads", f.filename)
        f.save(file_path)
        # Ingestar con el pipeline
        ingest_file(conv_id, file_path)

    return jsonify({"success": True, "message": f"Files indexed for conversation {conv_id}."})

@app.route("/chat", methods=["POST"])
def chat():
    """
    Recibe conversation_id, message
    Retorna la respuesta de GPT con el pipeline de retrieval.
    """
    data = request.form
    conv_id = data.get("conversation_id")
    user_message = data.get("message", "")

    if not conv_id or not user_message:
        return jsonify({"error":"Missing conversation_id or message"}), 400

    # 1) Almacenamos el mensaje en la conversacion local
    if conv_id not in conversation_messages:
        conversation_messages[conv_id] = []
    conversation_messages[conv_id].append({"role": "user", "content": user_message})

    # 2) Hacemos retrieval
    # Buscamos los chunks relevantes
    chunks = retrieve_relevant_chunks(conv_id, user_message, k=3)
    context_text = "\n\n".join([doc.page_content for doc in chunks])

    # 3) Construimos el prompt
    # Podrías usar un system message con tus "instructions" globales. Ej:
    system_prompt = (
        "Eres un asistente que ayuda a completar disclosures. "
        "Usa la info del usuario y sé conciso."
    )

    final_prompt = f"""
    CONTEXT FROM DOCUMENTS:
    {context_text}

    USER SAYS:
    {user_message}

    Respond helpfully using the context above if relevant.
    """

    # 4) Llamamos a GPT
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role":"system", "content": system_prompt},
            {"role":"user", "content": final_prompt},
        ],
        temperature=0.7
    )
    assistant_reply = response.choices[0].message["content"]

    # 5) Guardamos en la conversacion local
    conversation_messages[conv_id].append({"role": "assistant", "content": assistant_reply})

    return jsonify({"response": assistant_reply})

@app.route("/history", methods=["GET"])
def get_history():
    """
    Devuelve la historia local de la conversacion
    """
    conv_id = request.args.get("conversation_id")
    if not conv_id or conv_id not in conversation_messages:
        return jsonify({"error":"Invalid conv_id"}), 400
    return jsonify({"data": conversation_messages[conv_id]})

@app.route("/modifyLatex", methods=["POST"])
def modify_latex():
    """
    Demostración de la función 'modify_document' que antes usábamos
    en el function-calling approach. Lo hacemos manual aquí.
    """
    data = request.json
    conv_id = data.get("conversation_id")
    section = data.get("section")
    content = data.get("content")

    if not conv_id or not section or not content:
        return jsonify({"error":"Missing fields"}), 400

    # Ejemplo de manipulación
    document_manipulation.update_latex_section(section, content, conv_id)
    return jsonify({"success": True})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
