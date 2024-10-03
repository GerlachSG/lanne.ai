from flask import Flask, request, jsonify
import openai
import sqlite3

app = Flask(__name__)

openai.api_key = "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"

# Função para conectar ao banco de dados SQLite
def conectar_banco():
    conn = sqlite3.connect('database/bordinhondb.db')
    return conn

# Função para criar as tabelas no banco de dados
def criar_tabelas():
    conn = conectar_banco()
    cursor = conn.cursor()
    
    # Criando as tabelas de usuários e histórico
    cursor.execute('''CREATE TABLE IF NOT EXISTS usuarios (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        google_id TEXT UNIQUE)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS historico (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        usuario_id INTEGER,
                        mensagem TEXT,
                        resposta TEXT,
                        FOREIGN KEY(usuario_id) REFERENCES usuarios(id))''')
    conn.commit()
    conn.close()

# verificar se o usuário existe no BD e retornar o ID do usuário
def obter_usuario_id(google_id):
    conn = conectar_banco()
    cursor = conn.cursor()
    
    # Verificar se o usuário já existe
    cursor.execute('SELECT id FROM usuarios WHERE google_id = ?', (google_id,))
    resultado = cursor.fetchone()
    
    if resultado:
        usuario_id = resultado[0]
    else:
        # Criar um novo usuário se não existir
        cursor.execute('INSERT INTO usuarios (google_id) VALUES (?)', (google_id,))
        conn.commit()
        usuario_id = cursor.lastrowid
    
    conn.close()
    return usuario_id

# salvar o histórico de chat
def salvar_historico(usuario_id, mensagem, resposta):
    conn = conectar_banco()
    cursor = conn.cursor()
    
    # Inserir no banco de dados
    cursor.execute('INSERT INTO historico (usuario_id, mensagem, resposta) VALUES (?, ?, ?)', 
                   (usuario_id, mensagem, resposta))
    conn.commit()
    conn.close()

# obter o histórico de chat de um usuário
def obter_historico(usuario_id):
    conn = conectar_banco()
    cursor = conn.cursor()
    
    cursor.execute('SELECT mensagem, resposta FROM historico WHERE usuario_id = ?', (usuario_id,))
    historico = cursor.fetchall()
    
    conn.close()
    return historico

# enviar a conversa ao ChatGPT
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
    google_id = dados.get('google_id')
    lista_mensagens = dados.get('historico', [])
    
    # Obter ou criar o usuário no BD
    usuario_id = obter_usuario_id(google_id)
    
    # Enviar a mensagem para o ChatGPT e obter a resposta
    resposta = enviar_conversa(mensagem, lista_mensagens)
    
    # Salvar no BD
    salvar_historico(usuario_id, mensagem, resposta)
    
    # Adicionar  resposta ao histórico e retornar ao frontend
    lista_mensagens.append({"role": "assistant", "content": resposta})
    
    return jsonify({"resposta": resposta, "historico": lista_mensagens})

# Rota para obter o histórico de chat do usuário
@app.route('/historico', methods=['POST'])
def historico():
    dados = request.get_json()
    google_id = dados.get('google_id')
    
    # Obter o ID do usuário
    usuario_id = obter_usuario_id(google_id)
    
    # Obter o histórico do BD
    historico = obter_historico(usuario_id)
    
    return jsonify({"historico": historico})

if __name__ == '__main__':
    criar_tabelas()
    app.run(debug=True)

