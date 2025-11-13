import os
import openai

#key gpt
chave_api = "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"

openai.api_key = chave_api

def enviar_conversa(mensagem, lista_mensagens=[]):
    try:
        lista_mensagens.append({"role":"user", "content": mensagem})
        resposta = openai.ChatCompletion.create(
            model = "gpt-3.5-turbo",
            messages = lista_mensagens,
        )
        return resposta.choices[0].message['content']
    #caso ocorra erro entre a api gpt e o chat
    except Exception as e:
        print("Ocorreu um erro:", e)
        return "Desculpe, houve um problema com a API."
    
#interaçao do usuario
lista_mensagens = []
while True:
    texto = input("Digite sua mensagem (ou digite 'sair' para encerrar): ")

    if texto.lower() == "sair":
        break
    else:
        resposta = enviar_conversa(texto, lista_mensagens)
        lista_mensagens.append({"role": "assistant", "content": resposta})
        print("Chatbot:", resposta)
