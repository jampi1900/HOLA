from django.shortcuts import render


from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import Runnable
import requests

import json


import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Definir el alcance de acceso (Google Sheets + Drive)
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]


#####################
import os
# Obtiene la ruta absoluta del archivo JSON, basado en la ubicación del archivo views.py
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
json_path = os.path.join(BASE_DIR, 'awesome-griffin-444122-i8-8a38575f1dd6.json')
scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
credenciales = ServiceAccountCredentials.from_json_keyfile_name(json_path, scope)
# Autorizar el cliente
cliente = gspread.authorize(credenciales)
# Abrir la hoja de cálculo por nombre
spreadsheet = cliente.open('asis').sheet1
#################


# URL de tu Ngrok que apunta al FastAPI que sirve el modelo
COLAB_URL = "https://38ad-34-53-98-247.ngrok-free.app/v1/chat/completions"


class Chatbot:
    def __init__(self, llm,system_message=''):
        # This is the same prompt template we used earlier, which a placeholder message for storing conversation history.
        chat_conversation_template = ChatPromptTemplate.from_messages([
            ('system', system_message),
            ('placeholder', '{chat_conversation}')
        ])

        # This is the same chain we created above, added to `self` for use by the `chat` method below.
        self.chat_chain = chat_conversation_template | llm | StrOutputParser()

        # Here we instantiate an empty list that will be added to over time.
        self.chat_conversation = []

    # `chat` expects a simple string prompt.
    def chat(self, prompt):
        # Append the prompt as a user message to chat conversation.
        self.chat_conversation.append(('user', prompt))

        response = self.chat_chain.invoke({'chat_conversation': self.chat_conversation})
        # Append the chain response as an `ai` message to chat conversation.
        self.chat_conversation.append(('ai', response))
        # Return the chain response to the user for viewing.
        return response

    # Clear conversation history.
    def clear(self):
        self.chat_conversation = []



# Conversión de mensajes a formato JSON esperado por el servidor
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

# Proxy personalizado para comunicar Django con tu API de LLaMA
class LlamaProxy:
    def __init__(self, endpoint):
        self.endpoint = endpoint

    def __call__(self, chat_prompt_value):
        mensajes = mensajes_a_json(chat_prompt_value.to_messages())
        payload = {"messages": mensajes, "stream": False}
        response = requests.post(self.endpoint, json=payload)
        data = response.json()
        return data["choices"][0]["message"]["content"]




def formulario(request):
    if request.method == 'POST':
        pregunta = request.POST['mensaje_humano']

        # Recuperar historial como string o lista vacía por defecto
        historial_str = request.POST.get('historial', '[]')

        try:
            historial = json.loads(historial_str)
        except json.JSONDecodeError:
            historial = []  # Si falla, inicializa lista vacía




        llm = LlamaProxy(COLAB_URL)
        #mi chat ot es un vendedor de cursos
        system_message = (
            "Siempre responde en español. Eres Diego Bot, un vendedor de cursos de Python, Power BI y Excel en Perú. "
            "Cuando el usuario diga que quiere comprar un curso, dile: 'Perfecto, por favor dime tu nombre, edad y correo en ese orden, separados por comas'. "
            "Cuando el usuario te dé los datos, responde únicamente con: nombre, edad, correo — en ese orden, separados por comas, sin ninguna palabra adicional. "
            "Por ejemplo: Yampier Quispe, 34, yamquis@gmail.com"
        )

        #mi clase de chatbot
        chatbot = Chatbot(llm, system_message=system_message)
        chatbot.chat_conversation = historial

        respuesta = chatbot.chat(pregunta)

        

        # Intentar extraer y guardar si el formato es correcto
        try:
            # Validamos si hay comas y si hay 3 datos
            if ',' in respuesta:
                datos = respuesta.split(',')
                if len(datos) == 3:
                    nombre = datos[0].strip()
                    edad = datos[1].strip()
                    email = datos[2].strip()

                    # Validación simple (puedes mejorarla)
                    if nombre and edad.isdigit() and "@" in email:
                        spreadsheet.append_row([nombre, edad, email])
                        print(f"✅ Datos añadidos correctamente:\nNombre: {nombre}\nEdad: {edad}\nEmail: {email}")
                    else:
                        print("❌ El formato es incorrecto. Verifica que sea: nombre, edad, correo (correo válido).")
                else:
                    print("❌ Debes ingresar exactamente tres datos: nombre, edad, correo.")
            else:
                print("❌ Formato inválido. Debes usar comas: nombre, edad, correo.")

        except Exception as e:
            print("❌ Hubo un error al procesar los datos.")
            print("Error:", e)





        historial_actualizado = chatbot.chat_conversation

        historial_serializado = json.dumps(historial_actualizado)

        return render(request, 'index.html', {
            "response": respuesta,
            "historial": historial_actualizado,
            "historial_serializado": historial_serializado
        })

    return render(request, 'index.html', {"historial_serializado": "[]"})