"""
Aplicação principal do TUI Lanne AI
MELHORADO: Melhor estrutura, CSS unificado, suporte a temas
"""

from textual.app import App, ComposeResult
from textual.widgets import Header, Footer
from pathlib import Path

from .api_client import LanneAPIClient
from .screens.login import LoginScreen


class LanneApp(App):
    """Aplicação Textual principal"""
    
    TITLE = "Lanne AI - Linux Assistant"
    SUB_TITLE = "Powered by Textual"
    
    # CSS Global da aplicação
    CSS = """
    /* Tema base */
    Screen {
        background: $surface;
    }
    
    /* Logo ASCII */
    .ascii-logo {
        color: $accent;
        text-align: center;
        margin: 1 0;
    }
    
    /* Utilitários */
    .hidden {
        display: none;
    }
    
    .center {
        align: center middle;
    }
    
    .bold {
        text-style: bold;
    }
    
    .italic {
        text-style: italic;
    }
    
    /* Mensagens de status */
    .status-ok {
        color: $success;
    }
    
    .status-error {
        color: $error;
    }
    
    .status-warning {
        color: $warning;
    }
    
    /* Containers */
    .card {
        border: solid $primary;
        padding: 1 2;
        margin: 1;
    }
    
    .panel {
        background: $panel;
        border: solid $primary-darken-2;
        padding: 1;
    }
    
    /* Chat específico */
    #chat-log {
        background: $surface;
        border: solid $primary;
        height: 1fr;
        margin-bottom: 1;
    }
    
    .user-message {
        color: $success;
        margin: 1 2;
    }
    
    .ai-message {
        color: $primary;
        margin: 1 2;
    }
    
    .system-message {
        color: $warning;
        margin: 1 2;
        text-style: italic;
    }
    
    /* Formulários */
    .form-group {
        margin: 1 0;
    }
    
    .form-label {
        margin-bottom: 0;
    }
    
    .form-input {
        margin-top: 0;
    }
    
    /* Botões em linha */
    .button-row {
        height: auto;
        align: center middle;
    }
    
    .button-row Button {
        margin: 0 1;
    }
    """
    
    # Atalhos globais
    BINDINGS = [
        ("ctrl+c", "quit", "Sair"),
        ("ctrl+q", "quit", "Sair"),
        ("f1", "help", "Ajuda"),
        ("f5", "refresh", "Atualizar"),
    ]
    
    def __init__(self):
        super().__init__()
        self.api = LanneAPIClient()
    
    def on_mount(self) -> None:
        """Executado ao iniciar"""
        # Ir para tela de login
        self.push_screen(LoginScreen(self.api))
    
    def action_help(self) -> None:
        """Mostrar ajuda"""
        self.notify(
            "Atalhos Globais:\n"
            "━━━━━━━━━━━━━━\n"
            "Enter → Enviar/Confirmar\n"
            "Escape → Voltar/Cancelar\n"
            "Ctrl+C → Sair\n"
            "Tab → Navegar\n"
            "F1 → Esta ajuda",
            title="❓ Ajuda - Lanne AI",
            timeout=10
        )
    
    def action_refresh(self) -> None:
        """Atualizar tela atual"""
        self.refresh()
        self.notify("Tela atualizada!", timeout=2)
    
    def action_quit(self) -> None:
        """Sair da aplicação"""
        self.exit()


def main():
    """Ponto de entrada principal"""
    app = LanneApp()
    app.run()


if __name__ == "__main__":
    main()