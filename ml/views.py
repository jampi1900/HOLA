from django.shortcuts import render
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableLambda, RunnableParallel
import requests
import json
import re
import os
import markdown2

# --- Configuración de endpoint del modelo ---
COLAB_URL = os.getenv("COLAB_URL", "https://f577f483d323.ngrok-free.app/v1/chat/completions")

# --- Función: Conversión de mensajes a formato JSON compatible con la API ---
def mensajes_a_json(messages):
    resultado = []
    for msg in messages:
        if msg.type == "system":
            resultado.append({"role": "system", "content": msg.content})
        elif msg.type == "human":
            resultado.append({"role": "user", "content": msg.content})
        elif msg.type == "ai":
            resultado.append({"role": "assistant", "content": msg.content})
    return resultado

# --- Clase: Proxy para conectarse con Llama vía API ---
class LlamaProxy:
    def __init__(self, endpoint):
        self.endpoint = endpoint

    def __call__(self, chat_prompt_value):
        mensajes = mensajes_a_json(chat_prompt_value.to_messages())
        payload = {"messages": mensajes, "stream": False}
        try:
            response = requests.post(self.endpoint, json=payload)
            response.raise_for_status()  # Lanza un error si la respuesta no es 200
            data = response.json()
            return data["choices"][0]["message"]["content"]
        except requests.exceptions.RequestException as e:
            print(f"Error en la llamada a la API: {e}")
            return "Lo siento, hubo un error al procesar tu solicitud."

# --- Clase: Chatbot principal que gestiona la conversación ---
class Chatbot:
    def __init__(self, llm, system_message=''):
        chat_conversation_template = ChatPromptTemplate.from_messages([
            ('system', system_message),
            ('placeholder', '{chat_conversation}')
        ])
        self.chat_chain = chat_conversation_template | llm | StrOutputParser()
        self.chat_conversation = []

    def chat(self, prompt):
        self.chat_conversation.append(('user', prompt))
        response = self.chat_chain.invoke({'chat_conversation': self.chat_conversation})
        self.chat_conversation.append(('ai', response))
        return response

    def clear(self):
        self.chat_conversation = []

# --- Función: Extraer datos estructurados de una respuesta de texto del chatbot ---
def extraer_datos(respuesta):
    patron = r"^(.*?),\s*(\d+),\s*(.*?),\s*(.*?),\s*(.*?),\s*(.*?),\s*(.*?)$"
    match = re.match(patron, respuesta)
    if match:
        return {
            "nombre": match.group(1),
            "edad": int(match.group(2)),
            "intereses": match.group(3),
            "habilidades": match.group(4),
            "personalidad": match.group(5),
            "area_preferida": match.group(6),
            "correo": match.group(7)
        }
    return None

# --- Runnables: Extracción individual de campos (nombre, edad, intereses) ---
extraer_nombre = RunnableLambda(lambda x: {
    "nombre": x["input"].split(",")[0].strip() if len(x["input"].split(",")) > 0 else ""
})
extraer_edad = RunnableLambda(lambda x: {
    "edad": x["input"].split(",")[1].strip() if len(x["input"].split(",")) > 1 else ""
})
extraer_intereses = RunnableLambda(lambda x: {
    "intereses": x["input"].split(",")[2].strip() if len(x["input"].split(",")) > 2 else ""
})

# --- Runnable paralelo: Extraer datos en paralelo ---
extraer_datos_paralelo = RunnableParallel({
    "nombre": extraer_nombre,
    "edad": extraer_edad,
    "intereses": extraer_intereses
})

# --- Cargar prompt de sistema desde archivo ---
def cargar_system_message():
    ruta = os.path.join(os.path.dirname(__file__), 'prompts', 'system_message.txt')
    with open(ruta, 'r', encoding='utf-8') as file:
        return file.read()

# --- Vista principal del chatbot ---
def formulario(request):
    if request.method == 'POST':
        pregunta = request.POST['mensaje_humano']
        historial_str = request.POST.get('historial', '[]')

        try:
            historial = json.loads(historial_str)
        except json.JSONDecodeError:
            historial = []

        # Configurar LLM con mensaje de sistema
        llm = LlamaProxy(COLAB_URL)
        system_message = cargar_system_message()
        
        chatbot = Chatbot(llm, system_message=system_message)
        chatbot.chat_conversation = historial

        # Obtener respuesta del chatbot
        respuesta = chatbot.chat(pregunta)

        # Actualizar historial
        historial_actualizado = chatbot.chat_conversation
        historial_serializado = json.dumps(historial_actualizado)

        # Formatear los mensajes del bot con Markdown
        historial_renderizado = []
        for tipo, mensaje in historial_actualizado:
            if tipo == 'ai':
                mensaje = markdown2.markdown(mensaje)
            historial_renderizado.append((tipo, mensaje))

        # Extraer datos estructurados y paralelos
        datos_estructurados = extraer_datos(respuesta)
        paralelo = extraer_datos_paralelo.invoke({"input": respuesta})

        return render(request, 'index.html', {
            "historial": historial_renderizado,
            "historial_serializado": historial_serializado,
            "datos": datos_estructurados,
            "paralelo": paralelo
        })

    # Vista por defecto (GET)
    return render(request, 'index.html', {"historial_serializado": "[]"})
