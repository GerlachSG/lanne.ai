import sys
import warnings
import os

# Suprimir warnings no início
warnings.filterwarnings('ignore')
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

from db_service import DatabaseService
from chat_service import ChatService
from ui_service import UIService

class LanneApp:
    """
    Classe principal da aplicação (Orquestrador).
    Conecta e coordena os diferentes serviços (UI, DB, Chat).
    Atende ao requisito de OOP.
    """
    
    def __init__(self):
        try:
            self.db = DatabaseService()
            self.chat = ChatService()
            self.ui = UIService()
        except Exception as e:
            print(f"Erro fatal ao inicializar serviços: {e}")
            sys.exit(1)
            
        self.current_user = None

    def run(self):
        """Inicia o fluxo principal da aplicação."""
        try:
            self.ui.clear_screen()
            self.ui.show_main_menu_art()
            self._handle_login()
            self._handle_main_menu()
        except KeyboardInterrupt:
            print("\n\nSaindo. Até logo!")
        finally:
            print("\nAplicação encerrada.")

    def _handle_login(self):
        """Cuida do processo de login/criação de usuário."""
        username = self.ui.get_username()
        self.current_user = self.db.get_or_create_user(username)

    def _handle_main_menu(self):
        """Gerencia o loop do menu principal."""
        while True:
            self.ui.clear_screen()
            self.ui.show_main_menu_art()
            
            # Busca chats toda vez para saber se mostra a opção "Continuar"
            user_chats = self.db.get_chat_history(self.current_user["id"])
            
            choice = self.ui.show_main_menu(
                self.current_user["username"], 
                has_history=(len(user_chats) > 0)
            )

            if choice == "continuar":
                self._handle_chat_history(user_chats)
            elif choice == "novo":
                self._handle_chat_session(chat_id=None, history=[])
            elif choice == "sair":
                break

    def _handle_chat_history(self, chats):
        """Gerencia o menu de histórico (paginação, exclusão, seleção)."""
        while True:
            action = self.ui.show_chat_history_menu(chats)
            
            if action == "back":
                break # Volta para o menu principal
            
            elif isinstance(action, tuple) and action[0] == 'delete':
                # Ação é ('delete', chat_id)
                chat_id_to_delete = action[1]
                self.db.delete_chat(chat_id_to_delete)
                print(f"Chat {chat_id_to_delete} excluído.")
                # Atualiza a lista de chats local
                chats = [c for c in chats if c['id'] != chat_id_to_delete]
            
            elif isinstance(action, int):
                # Ação é um chat_id para carregar
                chat_id = action
                messages = self.db.get_chat_messages(chat_id)
                self._handle_chat_session(chat_id, messages)
                break # Volta ao menu principal após o fim do chat

    def _handle_chat_session(self, chat_id, history):
        """
        Gerencia uma sessão de chat ativa.
        Se chat_id for None, um novo chat será criado na primeira mensagem.
        """
        self.ui.show_chat_interface(history)
        
        while True:
            user_input = self.ui.get_chat_input()

            if user_input.lower() == 'sair':
                print("\nVoltando ao menu principal...")
                input("Pressione ENTER para continuar.")
                break

            # Se for a primeira mensagem de um novo chat
            if chat_id is None:
                title = self.chat.generate_title(user_input)
                chat_id = self.db.create_new_chat(self.current_user["id"], title)
            
            # Salva a mensagem do usuário
            self.db.add_message_to_chat(chat_id, "user", user_input)
            history.append({"sender": "user", "content": user_input})
            
            # Obtém e mostra a resposta da IA
            lanne_response = self.chat.get_lanne_response(history)
            
            # ✅ CORREÇÃO: garantir que é string
            if isinstance(lanne_response, tuple):
                lanne_response = lanne_response[0]
            
            self.ui.show_lanne_response(lanne_response)
            
            # Salva a resposta da IA
            self.db.add_message_to_chat(chat_id, "lanne", lanne_response)
            history.append({"sender": "lanne", "content": lanne_response})


# --- Ponto de Entrada ---
if __name__ == "__main__":
    app = LanneApp()
    app.run()