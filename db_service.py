import sqlite3
import datetime
import os
from contextlib import closing

# Define o nome do banco de dados
DB_NAME = "lanne_user_data.db"

class DatabaseService:
    """
    Serviço independente para gerenciar toda a interação
    com o banco de dados SQLite.
    """
    
    def __init__(self, db_name=DB_NAME):
        self.db_name = db_name
        self._init_db()

    def _get_connection(self):
        """Retorna uma nova conexão com o banco de dados."""
        # O banco será criado na mesma pasta do script
        db_path = os.path.join(os.path.dirname(__file__), self.db_name)
        return sqlite3.connect(db_path)

    def _init_db(self):
        """Cria as tabelas se elas não existirem."""
        with closing(self._get_connection()) as con:
            with con: # Habilita transação
                con.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY,
                        username TEXT UNIQUE NOT NULL
                    )
                """)
                con.execute("""
                    CREATE TABLE IF NOT EXISTS chats (
                        id INTEGER PRIMARY KEY,
                        user_id INTEGER NOT NULL,
                        title TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY(user_id) REFERENCES users(id)
                    )
                """)
                con.execute("""
                    CREATE TABLE IF NOT EXISTS messages (
                        id INTEGER PRIMARY KEY,
                        chat_id INTEGER NOT NULL,
                        sender TEXT NOT NULL, -- 'user' ou 'lanne'
                        content TEXT NOT NULL,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY(chat_id) REFERENCES chats(id)
                          ON DELETE CASCADE -- Se deletar o chat, deleta as msgs
                    )
                """)
        print(f"[DB Service] Banco de dados '{self.db_name}' inicializado.")

    def get_or_create_user(self, username):
        """Busca um usuário pelo nome ou cria um novo se não existir."""
        with closing(self._get_connection()) as con:
            with con:
                cur = con.execute("SELECT id, username FROM users WHERE username = ?", (username,))
                user = cur.fetchone()
                
                if user:
                    return {"id": user[0], "username": user[1]}
                else:
                    cur = con.execute("INSERT INTO users (username) VALUES (?)", (username,))
                    return {"id": cur.lastrowid, "username": username}

    def get_chat_history(self, user_id):
        """Busca todos os chats de um usuário, ordenados pelo mais recente."""
        with closing(self._get_connection()) as con:
            con.row_factory = sqlite3.Row # Retorna dict-like
            cur = con.execute(
                "SELECT id, title FROM chats WHERE user_id = ? ORDER BY created_at DESC", 
                (user_id,)
            )
            chats = [dict(row) for row in cur.fetchall()]
            return chats

    def get_chat_messages(self, chat_id):
        """Retorna todas as mensagens de um chat específico."""
        with closing(self._get_connection()) as con:
            con.row_factory = sqlite3.Row
            cur = con.execute(
                "SELECT sender, content FROM messages WHERE chat_id = ? ORDER BY timestamp ASC",
                (chat_id,)
            )
            messages = [dict(row) for row in cur.fetchall()]
            return messages

    def create_new_chat(self, user_id, title):
        """Cria uma nova entrada de chat e retorna o ID do chat."""
        with closing(self._get_connection()) as con:
            with con:
                cur = con.execute(
                    "INSERT INTO chats (user_id, title) VALUES (?, ?)", 
                    (user_id, title)
                )
                return cur.lastrowid

    def add_message_to_chat(self, chat_id, sender, content):
        """Adiciona uma nova mensagem ao histórico de um chat."""
        with closing(self._get_connection()) as con:
            with con:
                con.execute(
                    "INSERT INTO messages (chat_id, sender, content) VALUES (?, ?, ?)",
                    (chat_id, sender, content)
                )

    def update_chat_title(self, chat_id, new_title):
        """Atualiza o título de um chat (ainda não usado, mas útil)."""
        with closing(self._get_connection()) as con:
            with con:
                con.execute("UPDATE chats SET title = ? WHERE id = ?", (new_title, chat_id))

    def delete_chat(self, chat_id):
        """Deleta um chat e todas as suas mensagens (graças ao 'ON DELETE CASCADE')."""
        with closing(self._get_connection()) as con:
            with con:
                con.execute("DELETE FROM chats WHERE id = ?", (chat_id,))