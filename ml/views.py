from django.shortcuts import render
#################################################
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
#from langchain_core.runnables import Runnable,RunnableParallel
from langchain_core.runnables import RunnableLambda, RunnableParallel

import requests
import json
########################################################################################
import re
########################################################################################

COLAB_URL = "https://1d8f-34-142-173-31.ngrok-free.app/v1/chat/completions"

# --- Conversión de mensajes a JSON ---
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

# --- Clase que conecta con el modelo vía API ---
class LlamaProxy:
    def __init__(self, endpoint):
        self.endpoint = endpoint

    def __call__(self, chat_prompt_value):
        mensajes = mensajes_a_json(chat_prompt_value.to_messages())
        payload = {"messages": mensajes, "stream": False}
        response = requests.post(self.endpoint, json=payload)
        data = response.json()
        return data["choices"][0]["message"]["content"]

# --- Chatbot principal con historia de conversación ---
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

# --- Extraer campos estructurados desde la respuesta AI ---
"""
def extraer_datos(respuesta):
    patron = r"^(.*?),\s*(\d+),\s*(\d+),\s*(\d+),\s*(.*?),\s*(.*?),\s*(.*?)$"
    match = re.match(patron, respuesta)
    if match:
        return {
            "nombre": match.group(1),
            "edad": int(match.group(2)),
            "peso": int(match.group(3)),
            "estatura": int(match.group(4)),
            "actividad": match.group(5),
            "objetivo": match.group(6),
            "correo": match.group(7)
        }
    return None
"""

# --- Cadenas paralelas: extraer múltiples datos a la vez ---

#extraer_nombre = RunnableLambda(lambda x: {"nombre": x["input"].split(",")[0].strip()})
#extraer_edad = RunnableLambda(lambda x: {"edad": x["input"].split(",")[1].strip()})
#extraer_peso = RunnableLambda(lambda x: {"peso": x["input"].split(",")[2].strip()})


#extraer_datos_paralelo = RunnableParallel({
#    "nombre": extraer_nombre,
#    "edad": extraer_edad,
#    "peso": extraer_peso
#})

# --- Vista principal del chatbot ---
def formulario(request):
    if request.method == 'POST':
        pregunta = request.POST['mensaje_humano']
        historial_str = request.POST.get('historial', '[]')
        try:
            historial = json.loads(historial_str)
        except json.JSONDecodeError:
            historial = []

        llm = LlamaProxy(COLAB_URL)

        system_message = (
            "Siempre responde en español. Eres Diego Bot, un nutricionista profesional en Perú. "
            "Primero piensa paso a paso (cadena de pensamiento) antes de responder. "
            "Cuando el usuario diga que quiere una asesoría nutricional, dile: "
            "'Perfecto. Por favor indícame tu nombre completo, edad, peso en kilogramos, estatura en centímetros, "
            "nivel de actividad física (sedentario, moderado o activo), objetivo (bajar de peso, ganar masa muscular o mantener peso) "
            "y tu correo electrónico. Todo en ese orden, separado por comas.' "
            "Cuando el usuario te proporcione estos datos, responde únicamente con: nombre completo, edad, peso, estatura, nivel de actividad, objetivo, correo — "
            "en ese orden, separados por comas, sin ninguna palabra adicional."
            "SIEMPRE RESPONDE DE MANERA CORTA Y PRECIZA SIN EXPLICACIONES ADICIONALES."
            "Eres un experto en pokemon y puedes responder preguntas sobre ellos. "
        )

        chatbot = Chatbot(llm, system_message=system_message)
        chatbot.chat_conversation = historial

        respuesta = chatbot.chat(pregunta)
        #datos_estructurados = extraer_datos(respuesta)

        # (opcional) extracción en paralelo solo nombre, edad y peso
        #paralelo = extraer_datos_paralelo.invoke({"input": respuesta})

        historial_actualizado = chatbot.chat_conversation
        historial_serializado = json.dumps(historial_actualizado)

        return render(request, 'index.html', {
            "response": respuesta,
            "historial": historial_actualizado,
            "historial_serializado": historial_serializado
            #"datos": datos_estructurados,
            #"paralelo": paralelo
        })

    return render(request, 'index.html', {"historial_serializado": "[]"})

