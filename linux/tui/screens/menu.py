"""
Tela de Menu Principal - Hub central da aplicação
Com logo ASCII completa
"""

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Header, Footer, Static, Button, Label
from textual.containers import Container, Vertical, Grid
from textual import on

from ..utils import load_ascii_logo


class MenuScreen(Screen):
    """Tela de menu principal após login"""
    
    CSS = """
    #menu-container {
        align: center middle;
        width: 100%;
        height: 100%;
    }
    
    #menu-box {
        width: 100;
        height: auto;
        border: solid $primary;
        padding: 2;
    }
    
    .ascii-logo {
        color: $accent;
        text-align: center;
        padding: 1 0;
        margin-bottom: 1;
    }
    
    #welcome-label {
        text-align: center;
        color: $success;
        margin-bottom: 1;
    }
    
    #user-info {
        text-align: center;
        color: $text-muted;
        margin-bottom: 1;
    }
    
    #button-grid {
        grid-size: 2 3;
        grid-gutter: 1;
        height: auto;
        margin-top: 1;
    }
    
    #button-grid Button {
        width: 100%;
        height: 3;
    }
    """
    
    BINDINGS = [
        ("q", "quit", "Sair"),
        ("n", "new_chat", "Novo"),
        ("h", "history", "Historico"),
        ("l", "logout", "Logout"),
    ]
    
    def __init__(self, api):
        super().__init__()
        self.api = api
    
    def compose(self) -> ComposeResult:
        """Compor widgets"""
        logo = load_ascii_logo()
        
        yield Header()
        
        yield Container(
            Vertical(
                Static(logo, classes="ascii-logo"),
                Label(f"Usuario: {self.api.username}", id="welcome-label"),
                Label(f"Servidor: {self.api.base_url}", id="user-info"),
                
                # Botões em grid 2x3
                Grid(
                    Button("Novo Chat", variant="primary", id="new-chat-btn"),
                    Button("Historico", variant="default", id="history-btn"),
                    Button("Gerenciar", variant="warning", id="manage-btn"),
                    Button("Configuracoes", variant="default", id="settings-btn"),
                    Button("Logout", variant="error", id="logout-btn"),
                    Button("Sair", variant="default", id="quit-btn"),
                    id="button-grid"
                ),
                
                id="menu-box"
            ),
            id="menu-container"
        )
        
        yield Footer()
    
    async def on_mount(self) -> None:
        """Ao montar tela"""
        try:
            if self.api.is_logged_in:
                self.query_one("#welcome-label", Label).update(
                    f"Usuario: {self.api.username}"
                )
        except Exception:
            pass
    
    @on(Button.Pressed, "#new-chat-btn")
    async def action_new_chat(self) -> None:
        """Iniciar novo chat"""
        from .chat import ChatScreen
        
        # Limpar conversa anterior
        self.api.conversation_id = None
        self.api.conversation_title = None
        
        # Ir para chat
        self.app.push_screen(ChatScreen(self.api))
    
    @on(Button.Pressed, "#history-btn")
    async def action_history(self) -> None:
        """Ver histórico"""
        from .history import HistoryScreen
        self.app.push_screen(HistoryScreen(self.api))
    
    @on(Button.Pressed, "#manage-btn")
    async def open_manage(self) -> None:
        """Gerenciar conversas"""
        from .manage import ManageScreen
        self.app.push_screen(ManageScreen(self.api))
    
    @on(Button.Pressed, "#settings-btn")
    async def open_settings(self) -> None:
        """Abrir configurações"""
        self.app.notify("Configuracoes em desenvolvimento", title="Info")
    
    @on(Button.Pressed, "#logout-btn")
    async def action_logout(self) -> None:
        """Fazer logout"""
        try:
            await self.api.logout()
            self.app.notify("Logout realizado!", title="Sucesso")
        except Exception:
            pass
        
        # Voltar para login
        from .login import LoginScreen
        self.app.pop_screen()
        self.app.push_screen(LoginScreen(self.api))
    
    @on(Button.Pressed, "#quit-btn")
    def action_quit(self) -> None:
        """Sair da aplicação"""
        self.app.exit()