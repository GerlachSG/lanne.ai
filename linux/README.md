# Lanne AI - Linux Client

## 📋 Visão Geral

Interface de terminal (TUI) para o Lanne AI, compatível com Windows e Linux.

---

## 🐧 Instalação no Linux (Debian/Ubuntu)

### 1. Instalar Python 3.11+

```bash
sudo apt update
sudo apt install python3 python3-pip python3-venv -y
```

### 2. Criar Ambiente Virtual

```bash
cd linux
python3 -m venv venv
source venv/bin/activate
```

### 3. Instalar Dependências

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Copiar Logo ASCII

```bash
# O logo já está em ../lanne_ascii.txt
# Não precisa fazer nada
```

---

## 🚀 Como Usar

2. Menu principal:
   - 📝 **Novo Chat** - Conversa nova
   - 📜 **Histórico** - Ver conversas antigas
   - 🚪 **Sair**

3. No chat:
   - Digite e pressione Enter
   - Ctrl+C para voltar ao menu
   - A IA lembra do contexto!

---

## ⚙️ Configuração

### Arquivo de Config

`~/.lanne/config.json`:
```json
{
  "username": "seu_usuario",
  "token": "seu_token_jwt",
  "backend_url": "http://192.168.x.x",
  "conversation_id": null
}
```

### Conectar a Servidor Remoto

Edite o arquivo de config:

```bash
nano ~/.lanne/config.json
# Mude backend_url para IP do Windows
```

Ou use variável de ambiente:

```bash
export LANNE_BACKEND=http://192.168.1.100
python lanne_client.py
```

---

## 🔧 Troubleshooting

### Erro: "Connection refused"

**Problema:** Backend não está acessível

**Solução:**
```bash
# Testar conectividade
ping 192.168.x.x  # IP do Windows

# Verificar se portas estão abertas
curl http://192.168.x.x:8007  # Auth service
curl http://192.168.x.x:8006  # Conversation service
```

### Erro: "ModuleNotFoundError: textual"

**Problema:** Dependências não instaladas

**Solução:**
```bash
source venv/bin/activate
pip install -r requirements.txt
```

### TUI não mostra cores

**Problema:** Terminal não suporta cores

**Solução:**
```bash
# Usar terminal moderno
# Recomendado: Gnome Terminal, Konsole ou Terminator

# Ou definir TERM
export TERM=xterm-256color
```

---

## 📝 Comandos Úteis

```bash
# Ativar ambiente virtual
cd linux
source venv/bin/activate

# Desativar ambiente virtual
deactivate

# Atualizar dependências
pip install --upgrade -r requirements.txt

# Limpar cache
rm -rf ~/.lanne/

# Ver logs (se implementado)
tail -f ~/.lanne/lanne.log
```

---

## 🔑 Atalhos de Teclado

- **Enter** - Enviar mensagem
- **Ctrl+C** - Voltar/Sair
- **Ctrl+D** - Sair completamente
- **Tab** - Navegar entre elementos
- **↑/↓** - Navegar histórico
- **F1** - Ajuda (se implementado)

---

## 📦 Estrutura de Arquivos

```
linux/
├── lanne_client.py          # TUI Client (entry point)
├── lanne_agent.py           # Agent Server (porta 9000)
├── requirements.txt         # Dependências Python
├── README.md               # Este arquivo
├── install.sh              # Instalação automatica
├── run.sh                  # Executa TUI
├── run_agent.sh            # Executa Agent
├── tui/                    # Código do TUI
│   ├── __init__.py
│   ├── app.py              # App Textual principal
│   ├── api_client.py       # Cliente HTTP
│   └── screens/            # Telas do TUI
│       ├── __init__.py
│       ├── login.py        # Login com logo ASCII
│       ├── chat.py         # Chat interativo
│       └── history.py      # Histórico
└── venv/                   # Ambiente virtual (criado)
```

---

## 🆘 Suporte

Problemas comuns já resolvidos acima em Troubleshooting.

Para desenvolvimento/bugs, veja task.md no repositório.

---

**Desenvolvido com ❤️ usando Textual + Rich**
