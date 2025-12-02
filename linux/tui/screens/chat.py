"""
Tela de Chat com Worker (Thread Fix)
CORREÇÃO: Usa call_later para evitar RuntimeError em workers assíncronos.
"""
from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Header, Footer, RichLog, Input, Button, Label
from textual.containers import Vertical, Horizontal
from textual import on, work

class ChatScreen(Screen):
    
    CSS = """
    #chat-container { height: 100%; }
    #chat-header { dock: top; height: 3; background: $surface; border-bottom: solid $primary; padding: 0 1; }
    #chat-log { height: 1fr; border: none; padding: 1; scrollbar-gutter: stable; }
    #input-container { dock: bottom; height: 3; padding: 0 1; }
    #message-input { width: 1fr; }
    #send-btn { width: 12; }
    """
    
    BINDINGS = [("escape", "back_to_menu", "Menu")]
    
    def __init__(self, api):
        super().__init__()
        self.api = api
        self.is_busy = False
    
    def compose(self) -> ComposeResult:
        yield Header()
        yield Vertical(
            Label(f"Chat: {self.api.username}", id="header-label"),
            RichLog(id="chat-log", wrap=True, markup=True, highlight=True, auto_scroll=True),
            Horizontal(
                Input(placeholder="Mensagem...", id="message-input"),
                Button("Enviar", variant="primary", id="send-btn"),
                id="input-container"
            ),
            id="chat-container"
        )
        yield Footer()
    
    async def on_mount(self):
        self.query_one("#message-input", Input).focus()
        if not self.api.conversation_id:
            try:
                await self.api.create_conversation()
            except: pass

    # Worker seguro
    @work(exclusive=True)
    async def run_streaming(self, text: str):
        log = self.query_one("#chat-log", RichLog)
        
        # Helper para atualizar UI de dentro do async worker
        def update_ui(func, *args):
            self.app.call_later(func, *args)

        try:
            async for event in self.api.send_message_stream(text):
                
                if event["type"] == "status":
                    update_ui(log.write, f"[dim]>> {event['msg']}[/dim]")
                
                elif event["type"] == "final_response":
                    resp = event["data"].get("response", "")
                    meta = event["data"].get("metadata", {})
                    cmds = meta.get("commands", [])
                    
                    update_ui(log.write, f"\n[bold cyan]Lanne:[/bold cyan] {resp}")
                    
                    if cmds:
                        update_ui(log.write, f"\n[magenta]Comandos usados: {', '.join(cmds)}[/magenta]\n")

                elif event["type"] == "error":
                    update_ui(log.write, f"[red]Erro: {event.get('msg')}[/red]")
                    
        except Exception as e:
            update_ui(log.write, f"[red]Erro critico: {e}[/red]")
        
        finally:
            self.is_busy = False

    @on(Input.Submitted, "#message-input")
    @on(Button.Pressed, "#send-btn")
    async def send(self, event=None):
        if self.is_busy: return
        
        inp = self.query_one("#message-input", Input)
        text = inp.value.strip()
        if not text: return
        
        inp.value = ""
        log = self.query_one("#chat-log", RichLog)
        log.write(f"\n[bold green]Voce:[/bold green] {text}")
        
        self.is_busy = True
        self.run_streaming(text) 

    @on(Button.Pressed, "#back-btn")
    def back(self):
        from .menu import MenuScreen
        self.app.switch_screen(MenuScreen(self.api))