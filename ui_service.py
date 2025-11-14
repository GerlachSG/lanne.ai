import os

class UIService:
    """
    Serviço independente para gerenciar toda a
    interação com o console (CMD).
    """
    
    def __init__(self):
        # Mapeamento de 'nome de usuário' para 'usuário'
        self.user_label = "Usuário" 

    def clear_screen(self):
        """Limpa a tela do terminal."""
        os.system('cls' if os.name == 'nt' else 'clear')

    def show_main_menu_art(self):
        """Exibe a arte ASCII principal."""
        # Backslashes (\) precisam ser escapados (\\) em strings Python
        ascii_art = r""" __         ______   __    __  __    __  ________         ______   ______ 
/  |       /      \ /  \  /  |/  \  /  |/        |       /      \ /      |
$$ |      /$$$$$$  |$$  \ $$ |$$  \ $$ |$$$$$$$$/       /$$$$$$  |$$$$$$/ 
$$ |      $$ |__$$ |$$$  \$$ |$$$  \$$ |$$ |__          $$ |__$$ |  $$ |  
$$ |      $$    $$ |$$$$  $$ |$$$$  $$ |$$    |         $$    $$ |  $$ |  
$$ |      $$$$$$$$ |$$ $$ $$ |$$ $$ $$ |$$$$$/          $$$$$$$$ |  $$ |  
$$ |_____ $$ |  $$ |$$ |$$$$ |$$ |$$$$ |$$ |_____       $$ |  $$ | _$$ |_ 
$$       |$$ |  $$ |$$ | $$$ |$$ | $$$ |$$       |      $$ |  $$ |/ $$   |
$$$$$$$$/ $$/   $$/ $$/   $$/ $$/   $$/ $$$$$$$$/       $$/   $$/ $$$$$$/ 
                                                                          """
        print(ascii_art)
        print("                                                                      ")
        print("\n" + "="*80)
        print(" " * 25 + "BEM-VINDO AO LANNE.AI (CMD)")
        print("="*80 + "\n")

    def get_username(self):
        """Pergunta e obtém o nome de usuário."""
        username = ""
        while not username:
            username = input("Digite seu nome de usuário para começar: ").strip()
        self.user_label = username # Salva para usar no prompt
        return username

    def show_main_menu(self, username, has_history):
        """Mostra o menu principal (Novo Chat / Continuar)."""
        print(f"Olá, {username}!")
        print("\nO que você gostaria de fazer?\n")
        
        options = {}
        if has_history:
            print("  [1] Continuar conversa anterior")
            print("  [2] Iniciar um novo chat")
            print("  [3] Sair")
            options = {"1", "2", "3"}
        else:
            print("  [1] Iniciar um novo chat")
            print("  [2] Sair")
            options = {"1", "2"}

        choice = ""
        while choice not in options:
            choice = input("\nEscolha uma opção: ").strip()
        
        # Ajusta a escolha se não houver histórico
        if not has_history:
            if choice == "1": return "novo"
            if choice == "2": return "sair"
        else:
            if choice == "1": return "continuar"
            if choice == "2": return "novo"
            if choice == "3": return "sair"
        
        return "" # Fallback

    def show_chat_history_menu(self, chats):
        """
        Mostra o menu paginado do histórico de chats.
        Retorna um ID de chat, 'delete', 'back', ou 'refresh'.
        """
        page = 0
        page_size = 10
        total_chats = len(chats)
        if total_chats == 0:
            print("Nenhum histórico encontrado.")
            input("Pressione ENTER para voltar...")
            return "back"
            
        total_pages = (total_chats - 1) // page_size + 1

        while True:
            self.clear_screen()
            print("="*80)
            print(f"SEU HISTÓRICO DE CHATS (Página {page + 1} de {total_pages})")
            print("="*80 + "\n")

            # Mapeia 0-9 para os IDs de chat reais
            display_map = {}
            
            start_index = page * page_size
            end_index = min(start_index + page_size, total_chats)
            
            current_page_chats = chats[start_index:end_index]
            
            for i, chat in enumerate(current_page_chats):
                print(f"  [{i}] {chat['title']}")
                display_map[str(i)] = chat['id']
            
            print("\n" + "-"*80)
            print("INSTRUÇÕES:")
            print("- Digite um número (0-9) para carregar o chat.")
            print("- [P] Próxima Página  [A] Página Anterior")
            print("- [E] Excluir um chat [V] Voltar ao Menu")
            print("-" * 80)
            
            choice = input("Sua escolha: ").strip().lower()

            if choice.isdigit() and choice in display_map:
                return display_map[choice] # Retorna o ID do chat
            elif choice == 'v':
                return "back" # Voltar
            elif choice == 'p':
                if page < total_pages - 1:
                    page += 1
            elif choice == 'a':
                if page > 0:
                    page -= 1
            elif choice == 'e':
                del_choice = input("Digite o NÚMERO (0-9) do chat que deseja excluir: ").strip()
                if del_choice in display_map:
                    return ("delete", display_map[del_choice]) # Retorna tupla ('delete', chat_id)
                else:
                    print("Número inválido. Tente novamente.")
                    input("Pressione ENTER para continuar...")
            else:
                print("Comando inválido.")
                input("Pressione ENTER para continuar...")
    
    def show_chat_interface(self, history):
        """Exibe a tela de chat, imprimindo o histórico."""
        self.clear_screen()
        print("="*80)
        print(" " * 30 + "CONVERSA COM LANNE.AI")
        print("="*80)
        print("Digite 'sair' a qualquer momento para voltar ao menu principal.\n")

        for message in history:
            if message['sender'] == 'user':
                print(f"({self.user_label}): {message['content']}")
            else:
                print(f"(Lanne): {message['content']}")
        print("\n") # Espaço antes do novo prompt

    def get_chat_input(self):
        """Pega o input do usuário durante o chat."""
        return input(f"({self.user_label}): ").strip()

    def show_lanne_response(self, response):
        """Mostra a resposta da Lanne."""
        print(f"(Lanne): {response}")