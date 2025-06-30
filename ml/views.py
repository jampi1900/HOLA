from django.shortcuts import render


from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import Runnable
import requests

import json


# URL de tu Ngrok que apunta al FastAPI que sirve el modelo
COLAB_URL = "https://dc47-34-142-195-197.ngrok-free.app/v1/chat/completions"


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
        system_message = "Siempre responde en español, eres de Perú y te llamas Diego Bot."

        chatbot = Chatbot(llm, system_message=system_message)
        chatbot.chat_conversation = historial

        respuesta = chatbot.chat(pregunta)

        historial_actualizado = chatbot.chat_conversation
        historial_serializado = json.dumps(historial_actualizado)

        return render(request, 'index.html', {
            "response": respuesta,
            "historial": historial_actualizado,
            "historial_serializado": historial_serializado
        })

    return render(request, 'index.html', {"historial_serializado": "[]"})