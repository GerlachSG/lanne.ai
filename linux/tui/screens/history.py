"""
Tela de Histórico de Conversas
MELHORADO: Melhor UI, preview de mensagens, ordenação
"""

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Header, Footer, Static, ListView, ListItem, Label, Button
from textual.containers import Container, Vertical, Horizontal
from textual import on
from datetime import datetime


class HistoryScreen(Screen):
    """Tela de histórico de conversas"""
    
    CSS = """
    #history-container {
        height: 100%;
        padding: 1;
    }
    
    #history-title {
        text-align: center;
        text-style: bold;
        color: $accent;
        margin-bottom: 1;
    }
    
    #conversation-list {
        height: 1fr;
        border: solid $primary;
        margin-bottom: 1;
    }
    
    .conv-item {
        padding: 1;
    }
    
    .conv-title {
        color: $text;
        text-style: bold;
    }
    
    .conv-desc {
        color: $text-muted;
        text-style: italic;
    }
    
    .conv-meta {
        color: $text-disabled;
    }
    
    #button-row {
        height: 3;
        align: center middle;
    }
    
    #button-row Button {
        margin: 0 1;
    }
    
    #status-label {
        text-align: center;
        height: 2;
    }
    """
    
    BINDINGS = [
        ("escape", "back", "Menu"),
        ("enter", "open", "Abrir"),
        ("r", "refresh", "Atualizar"),
    ]
    
    def __init__(self, api):
        super().__init__()
        self.api = api
        self.conversations = []
    
    def compose(self) -> ComposeResult:
        """Compor widgets"""
        yield Header()
        
        yield Vertical(
            Label("📜 Histórico de Conversas", id="history-title"),
            ListView(id="conversation-list"),
            Horizontal(
                Button("📂 Abrir", variant="primary", id="open-btn"),
                Button("🔄 Atualizar", variant="default", id="refresh-btn"),
                Button("← Menu", variant="default", id="back-btn"),
                id="button-row"
            ),
            Label("", id="status-label"),
            id="history-container"
        )
        
        yield Footer()
    
    async def on_mount(self) -> None:
        """Ao montar tela"""
        await self.load_conversations()
    
    async def load_conversations(self) -> None:
        """Carregar lista de conversas"""
        status = self.query_one("#status-label", Label)
        status.update("🔄 Carregando conversas...")
        
        try:
            self.conversations = await self.api.list_conversations()
            
            # Ordenar por data (mais recentes primeiro)
            self.conversations.sort(
                key=lambda x: x.get('updated_at', x.get('created_at', '')),
                reverse=True
            )
            
            list_view = self.query_one("#conversation-list", ListView)
            list_view.clear()
            
            if not self.conversations:
                list_view.append(ListItem(
                    Label("📭 Nenhuma conversa encontrada"),
                    id="empty-item"
                ))
                status.update("Comece uma nova conversa no menu!")
                return
            
            for i, conv in enumerate(self.conversations):
                # Formatar item
                title = conv.get('title') or f"Conversa {conv['id'][:8]}"
                desc = conv.get('description', '')
                msg_count = conv.get('message_count', 0)
                
                # Formatar data
                created = conv.get('created_at', '')
                if created:
                    try:
                        dt = datetime.fromisoformat(created.replace('Z', '+00:00'))
                        date_str = dt.strftime("%d/%m/%Y %H:%M")
                    except:
                        date_str = created[:10]
                else:
                    date_str = "Data desconhecida"
                
                # Criar texto formatado
                item_text = f"[bold]{title}[/bold]"
                if desc:
                    item_text += f"\n[dim]{desc[:60]}{'...' if len(desc) > 60 else ''}[/dim]"
                item_text += f"\n[dim]📅 {date_str} | 💬 {msg_count} msgs[/dim]"
                
                list_view.append(ListItem(
                    Static(item_text, markup=True),
                    id=f"conv-{i}"
                ))
            
            status.update(f"✅ {len(self.conversations)} conversas encontradas")
            
        except Exception as e:
            status.update(f"❌ Erro: {str(e)}")
    
    @on(Button.Pressed, "#open-btn")
    @on(ListView.Selected)
    async def action_open(self, event=None) -> None:
        """Abrir conversa selecionada"""
        list_view = self.query_one("#conversation-list", ListView)
        
        if list_view.index is None or not self.conversations:
            self.query_one("#status-label", Label).update("⚠️ Selecione uma conversa!")
            return
        
        if list_view.index >= len(self.conversations):
            return
        
        selected_conv = self.conversations[list_view.index]
        self.api.conversation_id = selected_conv['id']
        self.api.conversation_title = selected_conv.get('title', 'Conversa')
        self.api.save_config()
        
        # Ir para chat
        from .chat import ChatScreen
        self.app.switch_screen(ChatScreen(self.api))
    
    @on(Button.Pressed, "#refresh-btn")
    async def action_refresh(self) -> None:
        """Atualizar lista"""
        await self.load_conversations()
    
    @on(Button.Pressed, "#back-btn")
    def action_back(self) -> None:
        """Voltar para menu"""
        from .menu import MenuScreen
        self.app.switch_screen(MenuScreen(self.api))