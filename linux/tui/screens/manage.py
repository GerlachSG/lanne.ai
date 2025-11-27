"""
Tela de Gerenciamento de Conversas
Corrigido: Removido markup problemático que causa erro de renderização
"""

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Header, Footer, Static, ListView, ListItem, Label, Button, Input
from textual.containers import Container, Vertical, Horizontal, Grid
from textual import on
from datetime import datetime


class ManageScreen(Screen):
    """Tela de gerenciamento de conversas"""
    
    CSS = """
    #manage-container {
        height: 100%;
        padding: 1;
    }
    
    #manage-title {
        text-align: center;
        text-style: bold;
        color: $warning;
        margin-bottom: 1;
    }
    
    #conversation-list {
        height: 1fr;
        border: solid $warning;
        margin-bottom: 1;
    }
    
    #button-grid {
        grid-size: 2 2;
        grid-gutter: 1;
        height: auto;
        margin-bottom: 1;
    }
    
    #button-grid Button {
        width: 100%;
        height: 3;
    }
    
    #rename-section {
        height: auto;
        margin-bottom: 1;
    }
    
    #rename-input {
        width: 1fr;
    }
    
    #status-label {
        text-align: center;
        height: 2;
    }
    
    .hidden {
        height: 0;
        overflow: hidden;
        margin: 0;
        padding: 0;
    }
    
    .visible {
        height: auto;
    }
    """
    
    BINDINGS = [
        ("escape", "back", "Menu"),
        ("d", "delete", "Deletar"),
        ("r", "show_rename", "Renomear"),
    ]
    
    def __init__(self, api):
        super().__init__()
        self.api = api
        self.conversations = []
        self.selected_index = None
    
    def compose(self) -> ComposeResult:
        """Compor widgets"""
        yield Header()
        
        yield Vertical(
            Label("Gerenciar Conversas", id="manage-title"),
            
            ListView(id="conversation-list"),
            
            # Seção de renomear (oculta por padrão)
            Horizontal(
                Input(placeholder="Novo titulo...", id="rename-input"),
                Button("Salvar", variant="success", id="save-rename-btn"),
                Button("Cancelar", variant="default", id="cancel-rename-btn"),
                id="rename-section",
                classes="hidden"
            ),
            
            # Botões em grid 2x2
            Grid(
                Button("Renomear", variant="primary", id="rename-btn"),
                Button("Deletar", variant="error", id="delete-btn"),
                Button("Deletar TODAS", variant="error", id="delete-all-btn"),
                Button("Voltar ao Menu", variant="default", id="back-btn"),
                id="button-grid"
            ),
            
            Label("", id="status-label"),
            id="manage-container"
        )
        
        yield Footer()
    
    async def on_mount(self) -> None:
        """Ao montar tela"""
        await self.load_conversations()
    
    async def load_conversations(self) -> None:
        """Carregar lista de conversas"""
        status = self.query_one("#status-label", Label)
        status.update("Carregando...")
        
        try:
            self.conversations = await self.api.list_conversations()
            
            # Ordenar por data
            self.conversations.sort(
                key=lambda x: x.get('updated_at', x.get('created_at', '')),
                reverse=True
            )
            
            list_view = self.query_one("#conversation-list", ListView)
            list_view.clear()
            
            if not self.conversations:
                list_view.append(ListItem(
                    Label("Nenhuma conversa para gerenciar"),
                    id="empty-item"
                ))
                status.update("")
                return
            
            # CORRIGIDO: Removido markup problemático
            for i, conv in enumerate(self.conversations):
                title = conv.get('title') or f"Conversa {conv['id'][:8]}"
                msg_count = conv.get('message_count', 0)
                
                # Texto simples sem markup - evita erro de renderização
                item_text = f"{title} ({msg_count} msgs)"
                
                list_view.append(ListItem(
                    Label(item_text),
                    id=f"conv-{i}"
                ))
            
            status.update(f"{len(self.conversations)} conversas | Selecione uma acao")
            
        except Exception as e:
            status.update(f"Erro: {str(e)}")
    
    @on(ListView.Selected)
    def on_select(self, event: ListView.Selected) -> None:
        """Ao selecionar item"""
        list_view = self.query_one("#conversation-list", ListView)
        self.selected_index = list_view.index
    
    @on(Button.Pressed, "#rename-btn")
    def action_show_rename(self) -> None:
        """Mostrar campo de renomear"""
        list_view = self.query_one("#conversation-list", ListView)
        
        if list_view.index is None or not self.conversations:
            self.query_one("#status-label", Label).update("Selecione uma conversa!")
            return
        
        # Mostrar campo de renomear
        rename_section = self.query_one("#rename-section")
        rename_section.remove_class("hidden")
        rename_section.add_class("visible")
        
        # Preencher com título atual
        conv = self.conversations[list_view.index]
        rename_input = self.query_one("#rename-input", Input)
        rename_input.value = conv.get('title', '')
        rename_input.focus()
    
    @on(Button.Pressed, "#save-rename-btn")
    @on(Input.Submitted, "#rename-input")
    async def save_rename(self, event=None) -> None:
        """Salvar novo título"""
        list_view = self.query_one("#conversation-list", ListView)
        
        if list_view.index is None:
            return
        
        new_title = self.query_one("#rename-input", Input).value.strip()
        
        if not new_title:
            self.query_one("#status-label", Label).update("Digite um titulo!")
            return
        
        try:
            conv = self.conversations[list_view.index]
            await self.api.update_conversation(conv['id'], title=new_title)
            
            self.query_one("#status-label", Label).update("Titulo atualizado!")
            rename_section = self.query_one("#rename-section")
            rename_section.remove_class("visible")
            rename_section.add_class("hidden")
            
            await self.load_conversations()
            
        except Exception as e:
            self.query_one("#status-label", Label).update(f"Erro: {str(e)}")
    
    @on(Button.Pressed, "#cancel-rename-btn")
    def cancel_rename(self) -> None:
        """Cancelar renomear"""
        rename_section = self.query_one("#rename-section")
        rename_section.remove_class("visible")
        rename_section.add_class("hidden")
    
    @on(Button.Pressed, "#delete-btn")
    async def action_delete(self) -> None:
        """Deletar conversa selecionada"""
        list_view = self.query_one("#conversation-list", ListView)
        status = self.query_one("#status-label", Label)
        
        if list_view.index is None or not self.conversations:
            status.update("Selecione uma conversa!")
            return
        
        conv = self.conversations[list_view.index]
        
        try:
            await self.api.delete_conversation(conv['id'])
            status.update("Conversa deletada!")
            
            await self.load_conversations()
            
        except Exception as e:
            status.update(f"Erro: {str(e)}")
    
    @on(Button.Pressed, "#delete-all-btn")
    async def delete_all(self) -> None:
        """Deletar todas as conversas"""
        status = self.query_one("#status-label", Label)
        
        if not self.conversations:
            status.update("Nenhuma conversa para deletar!")
            return
        
        # Confirmar com notificação
        self.app.notify(
            "Clique novamente para confirmar exclusao de TODAS as conversas!",
            title="Atencao",
            severity="warning"
        )
        
        # Mudar botão para confirmar
        delete_all_btn = self.query_one("#delete-all-btn", Button)
        
        if delete_all_btn.label == "Deletar TODAS":
            delete_all_btn.label = "CONFIRMAR"
            delete_all_btn.variant = "warning"
        else:
            # Confirmar exclusão
            status.update("Deletando todas as conversas...")
            
            try:
                for conv in self.conversations:
                    await self.api.delete_conversation(conv['id'])
                
                status.update("Todas as conversas deletadas!")
                delete_all_btn.label = "Deletar TODAS"
                delete_all_btn.variant = "error"
                
                await self.load_conversations()
                
            except Exception as e:
                status.update(f"Erro: {str(e)}")
    
    @on(Button.Pressed, "#back-btn")
    def action_back(self) -> None:
        """Voltar para menu"""
        from .menu import MenuScreen
        self.app.switch_screen(MenuScreen(self.api))