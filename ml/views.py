from django.shortcuts import render


from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
import requests

# URL de tu Ngrok que apunta al FastAPI que sirve el modelo
COLAB_URL = "https://effa-34-124-159-89.ngrok-free.app/v1/chat/completions"



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

    def invoke(self, chat_prompt_value):
        mensajes = mensajes_a_json(chat_prompt_value.to_messages())
        payload = {"messages": mensajes, "stream": False}
        response = requests.post(self.endpoint, json=payload)
        data = response.json()
        return data["choices"][0]["message"]["content"]

# Vista Django para manejar el formulario
def formulario(request):
    if request.method == 'POST':
        pregunta = request.POST['mensaje_humano']

        llm = LlamaProxy(COLAB_URL)

        prompt_template = ChatPromptTemplate.from_messages([
            ("system", "Eres un vendedor estrella y te llams diego Diego"),
            ("human", "responde de manera corta con 20 palabras {prompt}")
        ])

        parser = StrOutputParser()
        chain = prompt_template | llm.invoke | parser

        respuesta = chain.invoke({"prompt": pregunta})

        return render(request, 'index.html', {"response": respuesta})

    return render(request, 'index.html')
