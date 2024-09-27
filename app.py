from flask import Flask, request, jsonify
import openai

app = Flask(__name__)

openai.api_key = "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"

# Função para enviar a conversa ao ChatGPT
def enviar_conversa(mensagem, lista_mensagens=[]):
    lista_mensagens.append({"role": "user", "content": mensagem})
    
    try:
        resposta = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=lista_mensagens,
        )
        return resposta.choices[0].message['content']
    except Exception as e:
        print(f"Erro: {e}")
        return "Ocorreu um erro na comunicação com a API."

# Rota para o frontend enviar mensagens
@app.route('/chat', methods=['POST'])
def chat():
    dados = request.get_json()
    mensagem = dados.get('mensagem')
    lista_mensagens = dados.get('historico', [])
    
    resposta = enviar_conversa(mensagem, lista_mensagens)
    lista_mensagens.append({"role": "assistant", "content": resposta})

    return jsonify({"resposta": resposta, "historico": lista_mensagens})

if __name__ == '__main__':
    app.run(debug=True)
