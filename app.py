from flask import Flask, request, jsonify
import openai
import psycopg2

app = Flask(__name__)

openai.api_key = "sua-chave-api"

# Conexão com o PostgreSQL
conn = psycopg2.connect(
    host="seu_host",
    database="seu_banco_de_dados",
    user="seu_usuario",
    password="sua_senha"
)
cursor = conn.cursor()

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

# Função para salvar o histórico no banco de dados
def salvar_historico(usuario_id, mensagem, resposta):
    cursor.execute(
        "INSERT INTO historico (usuario_id, mensagem, resposta) VALUES (%s, %s, %s)",
        (usuario_id, mensagem, resposta)
    )
    conn.commit()

# Rota para o frontend enviar mensagens
@app.route('/chat', methods=['POST'])
def chat():
    dados = request.get_json()
    mensagem = dados.get('mensagem')
    lista_mensagens = dados.get('historico', [])
    google_id = dados.get('google_id')

    # Verificar se o usuário já está registrado
    cursor.execute("SELECT id FROM usuarios WHERE google_id = %s", (google_id,))
    usuario = cursor.fetchone()

    if not usuario:
        # Se o usuário não existir, crie um novo
        cursor.execute("INSERT INTO usuarios (google_id) VALUES (%s) RETURNING id", (google_id,))
        usuario_id = cursor.fetchone()[0]
        conn.commit()
    else:
        usuario_id = usuario[0]

    resposta = enviar_conversa(mensagem, lista_mensagens)
    lista_mensagens.append({"role": "assistant", "content": resposta})

    # Salvar o histórico no banco de dados
    salvar_historico(usuario_id, mensagem, resposta)

    return jsonify({"resposta": resposta, "historico": lista_mensagens})

if __name__ == '__main__':
    app.run(debug=True)
