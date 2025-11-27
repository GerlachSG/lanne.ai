# Lanne AI - Intelligent Linux Assistant

> 🤖 Sistema de IA conversacional especializado em Linux/Debian com memória persistente e arquitetura de microserviços.

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-Latest-green.svg)](https://fastapi.tiangolo.com)
[![Textual](https://img.shields.io/badge/Textual-TUI-purple.svg)](https://textual.textualize.io)

---

## 📋 Visão Geral

**Lanne AI** é um assistente de IA especializado em sistemas Linux/Debian que combina:

- 🧠 **Memória inteligente** - Lembra contexto de conversas anteriores
- 🔍 **RAG híbrido** - Busca vetorial (FAISS) + Web search
- 🐧 **Agent Linux** - Executa comandos remotos com segurança
- 💬 **TUI moderno** - Interface de terminal com Textual
- 🏗️ **Microserviços** - Arquitetura escalável e modular

---

## 🏛️ Arquitetura

```
┌─────────────────────────────────────────────────────────────┐
│                    LANNE AI SYSTEM                           │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌────────────┐     ┌──────────────┐     ┌──────────────┐  │
│  │  Linux     │────▶│   Gateway    │────▶│ Orchestrator │  │
│  │  TUI       │     │   (8000)     │     │    (8001)    │  │
│  │  Client    │     └──────────────┘     └──────┬───────┘  │
│  └────────────┘                                  │          │
│                                                   │          │
│  ┌────────────┐     ┌──────────────┐            │          │
│  │  Linux     │     │     Auth     │◀───────────┤          │
│  │  Agent     │     │    (8007)    │            │          │
│  │  (9000)    │     └──────────────┘            │          │
│  └─────▲──────┘                                  │          │
│        │         ┌──────────────┐                │          │
│        └─────────│ Conversation │◀───────────────┤          │
│                  │    (8006)    │                │          │
│                  └──────────────┘                │          │
│                                                   │          │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐    │          │
│  │Inference │◀──│   RAG    │◀──│   Web    │◀───┘          │
│  │  (8002)  │   │  (8003)  │   │  Search  │               │
│  └──────────┘   └──────────┘   │  (8004)  │               │
│                                 └──────────┘               │
└─────────────────────────────────────────────────────────────┘
```

### Componentes

| Serviço | Porta | Função |
|---------|-------|--------|
| **Gateway** | 8000 | API Gateway e roteamento |
| **Orchestrator** | 8001 | Orquestração e classificação de intenção |
| **Inference** | 8002 | LLM local (Mistral/Llama) |
| **RAG** | 8003 | Busca vetorial com FAISS |
| **Web Search** | 8004 | Pesquisa web (DuckDuckGo) |
| **Metrics** | 8005 | Métricas e logging |
| **Conversation** | 8006 | Histórico e memória de conversas |
| **Auth** | 8007 | Autenticação JWT |
| **Linux Agent** | 9000 | Executor de comandos Linux (opcional) |

---

## 🚀 Configurações de Uso

### Configuração 1: Servidor Windows (Backend Completo)

**Ideal para:** Desenvolvimento, servidor central, múltiplos clientes

#### Requisitos
- Windows 10/11
- Python 3.11+
- 8GB RAM (16GB recomendado para LLM)
- GPU NVIDIA (opcional, para inference mais rápido)

#### 1. Instalação

```powershell
# Clone o repositório
cd "lannelinux 0611 mais funcional"

# Instalar dependências
pip install -r requirements.txt

# Instalar schemas compartilhados
pip install -e lanne-schemas/
```

#### 2. Iniciar Serviços

```powershell
python start_all.py
```

Aguarde ~30-60 segundos para o **inference-service** baixar o modelo LLM na primeira execução.

#### 3. Verificar Status

Acesse em qualquer navegador:
- http://localhost:8000 - Gateway (deve retornar JSON)
- http://localhost:8001 - Orchestrator
- http://localhost:8002/docs - Inference (Swagger UI)

#### 4. Testar API

```powershell
# Registrar usuário
curl -X POST http://localhost:8007/register -H "Content-Type: application/json" -d "{\"username\": \"admin\", \"admin\": true}"

# Criar conversa
curl -X POST http://localhost:8006/conversations -H "Content-Type: application/json" -d "{\"user_id\": \"admin\"}"

# Enviar mensagem
curl -X POST http://localhost:8001/internal/orchestrate -H "Content-Type: application/json" -d "{\"text\": \"Como instalar nginx?\", \"conversation_id\": \"conv-123\"}"
```

---

### Configuração 2: Cliente Linux + Agent (TUI)

**Ideal para:** Uso diário, acesso remoto ao servidor Windows

#### Requisitos
- Debian/Ubuntu Linux
- Python 3.11+
- Conexão de rede com servidor Windows

#### 1. Instalação

```bash
cd linux
chmod +x *.sh
./install.sh
```

O script irá:
- Criar ambiente virtual Python
- Instalar dependências (Textual, httpx, Rich)
- Configurar estrutura de pastas

#### 2. Configurar Backend

**Não é mais necessário editar arquivos manualmente!**

Ao iniciar o TUI pela primeira vez:

1. **Seleção de Servidor** - Escolha entre:
   - 🏠 **Localhost** - Backend no mesmo PC
   - 🌐 **IP Remoto** - Backend no servidor Windows

2. **Se escolher IP Remoto**:
   - Digite o IP do servidor Windows (ex: 192.168.1.100)
   - Sistema validará automaticamente (ping/pong)

3. **Validação Automática**:
   - ✅ Backend conectado (porta 8000)
   - ✅ Agent conectado (porta 9000, opcional)

4. **Configuração Salva**:
   - Salva automaticamente em `~/.lanne/config.json`
   - Próximas vezes faz login direto

**Variável de ambiente (opcional):**

```bash
export LANNE_BACKEND=http://192.168.1.100
```

#### 3. Iniciar TUI (Modo Cliente)

```bash
./run.sh
```

Navegação:
- **Enter** - Enviar mensagem
- **Ctrl+C** - Voltar/Sair  
- **Tab** - Navegar elementos
- **Esc** - Voltar

#### 4. (Opcional) Iniciar Agent (Modo Servidor)

O **Agent** permite que o backend Windows execute comandos no Linux remotamente.

```bash
# Em outro terminal
./run_agent.sh
```

Configurar no Windows (`orchestrator-service/main.py`):

```python
AGENT_URL = "http://192.168.X.X:9000"  # IP do Linux
```

---

## 💡 Funcionalidades

### ✅ Memória Persistente

Conversas são salvas automaticamente com:
- **Títulos e descrições** gerados por IA
- **Resumos hierárquicos** para contexto eficiente
- **Janela deslizante** - últimas 6 mensagens + resumo

### ✅ RAG Híbrido

1. **RAG Local** (FAISS) - Documentação e comandos Linux
2. **Web Search** (DuckDuckGo) - Informações atualizadas
3. **LLM** - Síntese e geração de resposta

### ✅ TUI Moderno

- Logo ASCII personalizado
- Chat interativo com markdown
- Histórico navegável
- Indicador "digitando..."

### ✅ Segurança

- Autenticação JWT
- Whitelist de comandos no Agent
- Validação de tokens

---

## 📁 Estrutura do Projeto

```
lannelinux-0611-mais-funcional/
├── auth-service/              # Autenticação JWT
├── conversation-service/      # Histórico e memória
├── gateway-service/           # API Gateway
├── orchestrator-service/      # Orquestração principal
├── inference-service/         # LLM local
├── rag-service/               # Busca vetorial
├── web-search-service/        # Pesquisa web
├── metrics-service/           # Métricas
├── lanne-schemas/             # Modelos Pydantic compartilhados
├── linux/                     # TUI + Agent Linux
│   ├── lanne_client.py        # Cliente TUI
│   ├── lanne_agent.py         # Agent servidor
│   ├── tui/                   # Código Textual
│   └── README.md              # Guia Linux
├── start_all.py               # Inicia todos serviços (Windows)
├── requirements.txt           # Dependências Python
└── README.md                  # Este arquivo
```

---

## 📖 Documentação

- **[README-Linux](linux/README.md)** - Guia completo do TUI
- **[Walkthrough](docs/walkthrough.md)** - Implementação detalhada
- **[Task List](docs/task.md)** - Checklist de desenvolvimento
- **[Guia TUI](docs/guia-tui.md)** - Arquitetura do TUI

---

## 🧪 Testes

### Backend (Windows)

```powershell
# Teste básico
python test_services.py

# Teste manual
curl http://localhost:8000
```

### TUI (Linux)

```bash
cd linux
./run.sh

# Testar memória:
# 1. "Como instalar nginx?"
# 2. "E como configuro porta 8080?"
# IA deve lembrar do contexto!
```

---

## 🛠️ Troubleshooting

### Windows

**Erro: "Port already in use"**
```powershell
# Verificar portas em uso
netstat -ano | findstr :8000

# Matar processo
taskkill /PID <PID> /F
```

**Erro: "ModuleNotFoundError"**
```powershell
pip install -r requirements.txt
pip install -e lanne-schemas/
```

###Linux

**Erro: "Connection refused"**
```bash
# Testar conectividade
ping 192.168.X.X  # IP do Windows

# Verificar firewall Windows
# Permitir portas 8000-8007 e 9000
```

**Erro: "Permission denied"**
```bash
chmod +x *.sh
```

---

## 🤝 Contribuindo

1. Fork o projeto
2. Crie uma branch (`git checkout -b feature/MinhaFeature`)
3. Commit suas mudanças (`git commit -m 'Add: MinhaFeature'`)
4. Push para a branch (`git push origin feature/MinhaFeature`)
5. Abra um Pull Request

---

## 📝 Licença

Este projeto é licenciado sob a MIT License.

---

## 👨‍💻 Autores

Desenvolvido com ❤️ usando:
- [FastAPI](https://fastapi.tiangolo.com/) - Framework web assíncrono
- [Textual](https://textual.textualize.io/) - TUI framework
- [Transformers](https://huggingface.co/transformers/) - LLM local
- [FAISS](https://github.com/facebookresearch/faiss) - Busca vetorial
- [SQLAlchemy](https://www.sqlalchemy.org/) - ORM assíncrono

---

## 🚀 Próximos Passos

- [ ] Frontend web (React/Vue)
- [ ] Docker containers
- [ ] PostgreSQL para produção
- [ ] Testes automatizados (pytest)
- [ ] CI/CD pipeline
- [ ] Documentação API (OpenAPI)

---

**Lanne AI - Seu assistente Linux inteligente com memória!** 🤖✨
