"""
Tela de Login - Wizard Multi-Step
Navegação sequencial: Username → Agent IP → Server IP → Confirmação
"""

from textual.app import ComposeResult
from textual.screen import Screen
from textual.widgets import Static, Input, Button, Label, RadioButton, RadioSet
from textual.containers import Container, Vertical, Horizontal
from textual import on

from ..utils import load_ascii_logo


class LoginScreen(Screen):
    """Tela de login com wizard de 4 passos"""
    
    CSS = """
    #login-container {
        align: center middle;
        width: 100%;
        height: 100%;
    }
    
    #login-box {
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
    
    .step-title {
        text-align: center;
        text-style: bold;
        color: $primary;
        margin-bottom: 2;
    }
    
    .form-label {
        margin-top: 1;
        color: $text;
        text-style: bold;
    }
    
    .form-input {
        margin-bottom: 1;
    }
    
    .radio-section {
        margin: 1 0;
    }
    
    .summary-box {
        border: solid $success;
        padding: 1 2;
        margin: 1 0;
    }
    
    .summary-label {
        color: $text-muted;
    }
    
    .summary-value {
        color: $success;
        text-style: bold;
    }
    
    .button-row {
        margin-top: 2;
        height: 3;
        align: center middle;
    }
    
    .button-row Button {
        margin: 0 1;
    }
    
    #status {
        text-align: center;
        margin-top: 1;
        height: 2;
    }
    
    .status-ok {
        color: $success;
    }
    
    .status-error {
        color: $error;
    }
    
    .status-warning {
        color: $warning;
    }
    
    .hidden {
        display: none;
    }
    
    .visible {
        display: block;
    }
    """
    
    BINDINGS = [
        ("escape", "quit", "Sair"),
    ]
    
    def __init__(self, api):
        super().__init__()
        self.api = api
        
        # Estado do wizard
        self.current_step = 1
        self.username = ""
        self.agent_type = "localhost"
        self.agent_ip = ""
        self.server_type = "localhost"
        self.server_ip = ""
    
    def compose(self) -> ComposeResult:
        """Compor widgets"""
        logo = load_ascii_logo()
        
        yield Container(
            Vertical(
                Static(logo, classes="ascii-logo"),
                Vertical(id="step-container"),
                Label("", id="status"),
                id="login-box"
            ),
            id="login-container"
        )
    
    async def on_mount(self) -> None:
        """Ao montar tela"""
        self.render_step()
    
    def render_step(self):
        """Renderiza o passo atual do wizard"""
        container = self.query_one("#step-container", Vertical)
        
        # CORREÇÃO: Limpar widgets manualmente para evitar IDs duplicados
        for child in list(container.children):
            child.remove()
        
        if self.current_step == 1:
            self._render_step_username(container)
        elif self.current_step == 2:
            self._render_step_agent(container)
        elif self.current_step == 3:
            self._render_step_server(container)
        elif self.current_step == 4:
            self._render_step_summary(container)
    
    def _render_step_username(self, container):
        """Passo 1: Nome de usuário"""
        container.mount(
            Label("Bem-vindo ao Lanne AI", classes="step-title"),
            Label("Nome de Usuario:", classes="form-label"),
            Input(
                placeholder="Digite seu nome de usuario",
                id="username-input",
                classes="form-input",
                value=self.username
            ),
            Horizontal(
                Button("Proximo", variant="primary", id="next-btn"),
                classes="button-row"
            )
        )
        self.set_timer(0.1, lambda: self.query_one("#username-input", Input).focus())
    
    def _render_step_agent(self, container):
        """Passo 2: IP do Agente"""
        container.mount(
            Label("Configuracao do Agente Linux", classes="step-title"),
            Label("Onde esta o Agente?", classes="form-label"),
            RadioSet(
                RadioButton("Meu PC (localhost)", id="radio-agent-localhost", value=(self.agent_type == "localhost")),
                RadioButton("Outro PC (IP)", id="radio-agent-remote", value=(self.agent_type == "remote")),
                id="agent-options",
                classes="radio-section"
            ),
            Vertical(
                Label("IP do Agente:", classes="form-label"),
                Input(placeholder="172.17.1.1", id="agent-ip-input", classes="form-input", value=self.agent_ip),
                id="agent-ip-section",
                classes="hidden" if self.agent_type == "localhost" else "visible"
            ),
            Horizontal(
                Button("Voltar", variant="default", id="back-btn"),
                Button("Proximo", variant="primary", id="next-btn"),
                classes="button-row"
            )
        )
    
    def _render_step_server(self, container):
        """Passo 3: IP do Servidor"""
        container.mount(
            Label("Configuracao do Servidor Backend", classes="step-title"),
            Label("Qual IP da IA?", classes="form-label"),
            RadioSet(
                RadioButton("Localhost (mesmo PC)", id="radio-server-localhost", value=(self.server_type == "localhost")),
                RadioButton("Servidor Remoto (IP)", id="radio-server-remote", value=(self.server_type == "remote")),
                id="server-options",
                classes="radio-section"
            ),
            Vertical(
                Label("IP do Servidor:", classes="form-label"),
                Input(placeholder="192.168.1.100", id="server-ip-input", classes="form-input", value=self.server_ip),
                id="server-ip-section",
                classes="hidden" if self.server_type == "localhost" else "visible"
            ),
            Horizontal(
                Button("Voltar", variant="default", id="back-btn"),
                Button("Proximo", variant="primary", id="next-btn"),
                classes="button-row"
            )
        )
    
    def _render_step_summary(self, container):
        """Passo 4: Resumo e Confirmação"""
        agent_display = "localhost:9000" if self.agent_type == "localhost" else f"{self.agent_ip}:9000"
        server_display = "localhost:8001" if self.server_type == "localhost" else f"{self.server_ip}:8001"
        
        container.mount(
            Label("Confirmacao de Dados", classes="step-title"),
            Vertical(
                Label("Nome de Usuario:", classes="summary-label"),
                Label(self.username, classes="summary-value"),
                Label(""),
                Label("IP do Agente:", classes="summary-label"),
                Label(agent_display, classes="summary-value"),
                Label(""),
                Label("IP do Servidor:", classes="summary-label"),
                Label(server_display, classes="summary-value"),
                classes="summary-box"
            ),
            Horizontal(
                Button("Voltar", variant="default", id="back-btn"),
                Button("Registrar", variant="success", id="register-btn"),
                Button("Conectar", variant="primary", id="connect-btn"),
                classes="button-row"
            )
        )
    
    def update_status(self, message: str, status_type: str = ""):
        """Atualiza label de status"""
        status = self.query_one("#status", Label)
        status.update(message)
        status.remove_class("status-ok", "status-error", "status-warning")
        
        if status_type == "ok":
            status.add_class("status-ok")
        elif status_type == "error":
            status.add_class("status-error")
        elif status_type == "warning":
            status.add_class("status-warning")
    
    @on(Button.Pressed, "#next-btn")
    async def handle_next(self):
        """Avançar para próximo passo"""
        if self.current_step == 1:
            username_input = self.query_one("#username-input", Input)
            username = username_input.value.strip()
            
            if not username:
                self.update_status("Digite um username!", "error")
                return
            if len(username) < 3:
                self.update_status("Username deve ter pelo menos 3 caracteres!", "error")
                return
            if not username.isalnum():
                self.update_status("Username deve conter apenas letras e numeros!", "error")
                return
            
            self.username = username
            self.current_step = 2
            self.update_status("")
            self.render_step()
            
        elif self.current_step == 2:
            if self.agent_type == "remote":
                agent_ip = self.query_one("#agent-ip-input", Input).value.strip()
                if not agent_ip:
                    self.update_status("Digite o IP do agente!", "error")
                    return
                self.agent_ip = agent_ip
            
            self.current_step = 3
            self.update_status("")
            self.render_step()
            
        elif self.current_step == 3:
            if self.server_type == "remote":
                server_ip = self.query_one("#server-ip-input", Input).value.strip()
                if not server_ip:
                    self.update_status("Digite o IP do servidor!", "error")
                    return
                self.server_ip = server_ip
            
            self.current_step = 4
            self.update_status("")
            self.render_step()
    
    @on(Button.Pressed, "#back-btn")
    def handle_back(self):
        """Voltar para passo anterior"""
        if self.current_step > 1:
            self.current_step -= 1
            self.update_status("")
            self.render_step()
    
    @on(RadioSet.Changed, "#agent-options")
    def handle_agent_change(self, event: RadioSet.Changed):
        """Ao mudar tipo de agente"""
        ip_section = self.query_one("#agent-ip-section")
        
        if event.pressed.id == "radio-agent-remote":
            self.agent_type = "remote"
            ip_section.remove_class("hidden")
            ip_section.add_class("visible")
        else:
            self.agent_type = "localhost"
            ip_section.remove_class("visible")
            ip_section.add_class("hidden")
    
    @on(RadioSet.Changed, "#server-options")
    def handle_server_change(self, event: RadioSet.Changed):
        """Ao mudar tipo de servidor"""
        ip_section = self.query_one("#server-ip-section")
        
        if event.pressed.id == "radio-server-remote":
            self.server_type = "remote"
            ip_section.remove_class("hidden")
            ip_section.add_class("visible")
        else:
            self.server_type = "localhost"
            ip_section.remove_class("visible")
            ip_section.add_class("hidden")
    
    @on(Input.Submitted)
    async def on_input_submit(self, event: Input.Submitted):
        """Enter em qualquer input avança"""
        await self.handle_next()
    
    def _configure_server(self) -> bool:
        """Configura URL do servidor"""
        if self.server_type == "remote":
            self.api.set_base_url(f"http://{self.server_ip}")
        else:
            self.api.set_base_url("http://localhost")
        return True
    
    async def _configure_agent(self) -> bool:
        """Configura URL do agente"""
        if self.agent_type == "remote":
            agent_url = f"http://{self.agent_ip}:9000"
        else:
            agent_url = "http://localhost:9000"
        
        try:
            result = await self.api.configure_agent(agent_url)
            if result.get("status") == "ok":
                return True
            else:
                self.update_status("Erro ao configurar agente", "error")
                return False
        except Exception as e:
            self.update_status(f"Erro ao configurar agente: {str(e)[:30]}", "error")
            return False
    
    async def _test_connection(self) -> bool:
        """Testa conexão com o backend"""
        self.update_status("Testando conexao com backend...", "warning")
        
        result = await self.api.check_backend()
        
        if result["status"] == "ok":
            self.update_status("Backend conectado!", "ok")
            return True
        else:
            msg = result.get("message", "Nao foi possivel conectar")
            self.update_status(f"Erro: {msg}", "error")
            return False
    
    @on(Button.Pressed, "#connect-btn")
    async def handle_connect(self):
        """Conectar (login)"""
        if not self._configure_server():
            return
        
        if not await self._test_connection():
            return
        
        self.update_status(f"Conectando como {self.username}...", "warning")
        
        try:
            result = await self.api.login(self.username)
            
            self.update_status("Configurando agente...", "warning")
            if not await self._configure_agent():
                self.update_status("Conectado! (Agente nao disponivel)", "warning")
            else:
                self.update_status(f"Conectado como {self.username}!", "ok")
            
            self.set_timer(1, self.go_to_menu)
            
        except Exception as e:
            error_msg = str(e)
            if "não encontrado" in error_msg.lower() or "not found" in error_msg.lower():
                self.update_status("Usuario nao existe. Clique em 'Registrar'.", "error")
            else:
                self.update_status(f"Erro: {error_msg[:50]}", "error")
    
    @on(Button.Pressed, "#register-btn")
    async def handle_register(self):
        """Registrar novo usuário"""
        if not self._configure_server():
            return
        
        if not await self._test_connection():
            return
        
        self.update_status(f"Registrando {self.username}...", "warning")
        
        try:
            result = await self.api.register(self.username)
            
            self.update_status("Configurando agente...", "warning")
            if not await self._configure_agent():
                self.update_status("Registrado! (Agente nao disponivel)", "warning")
            else:
                if result["status"] == "registered":
                    self.update_status(f"Usuario {self.username} criado com sucesso!", "ok")
                else:
                    self.update_status(f"Conectado como {self.username}!", "ok")
            
            self.set_timer(1, self.go_to_menu)
            
        except Exception as e:
            self.update_status(f"Erro: {str(e)[:50]}", "error")
    
    def go_to_menu(self):
        """Ir para menu principal"""
        from .menu import MenuScreen
        self.app.switch_screen(MenuScreen(self.api))
    
    def action_quit(self):
        """Sair da aplicação"""
        self.app.exit()
