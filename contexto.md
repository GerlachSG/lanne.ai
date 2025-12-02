# Lanne AI - Documentação Técnica do Sistema

## 1. Modelos de IA Utilizados

### 1.1 Modelo Principal: Qwen2.5-7B-Instruct

**Por que Qwen2.5?**
- **Estabilidade**: Mais estável que alternativas como Mistral para português brasileiro
- **Qualidade de resposta**: Melhor compreensão de contexto técnico Linux
- **Suporte a quantização**: Funciona bem com quantização 8-bit
- **Tamanho otimizado**: 7B parâmetros é o balanço ideal entre qualidade e performance

**Configuração de quantização:**
```python
# Quantização 8-bit com BitsAndBytes
# Reduz uso de VRAM de ~14GB para ~8.71GB
BitsAndBytesConfig(
    load_in_8bit=True,
    llm_int8_threshold=6.0
)
```

### 1.2 Modelo de Embeddings: all-MiniLM-L6-v2

**Por que este modelo?**
- **Dimensão 384**: Compacto mas eficiente para busca semântica
- **Velocidade**: Rápido para gerar embeddings em tempo real
- **Qualidade**: Boa representação semântica para textos técnicos
- **Compatibilidade**: Integração nativa com FAISS

### 1.3 Classificador ML: Scikit-learn Pipeline

**Por que ML local ao invés de só LLM?**
- **Velocidade**: Classificação em <10ms vs >500ms do LLM
- **Economia de recursos**: Não consome GPU para classificar intenção
- **Confiabilidade**: Pipeline TF-IDF + RandomForest é determinístico

```python
# Pipeline de classificação
classifier_pipeline = Pipeline([
    ('tfidf', TfidfVectorizer()),
    ('classifier', RandomForestClassifier())
])
```

---

## 2. Banco de Dados e Persistência

### 2.1 Por que JSON ao invés de SQL?

**Auth Service (users.json):**
```python
def save_users(users: dict):
    with open(USERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(users, f, indent=2, ensure_ascii=False, default=str)
```

**Justificativa:**
- **Simplicidade**: Projeto educacional, sem necessidade de ORM complexo
- **Portabilidade**: Arquivo único, fácil backup e migração
- **Desenvolvimento rápido**: Sem migrations ou schema rígido
- **Escala atual**: <1000 usuários, JSON é suficiente

**Conversation Service (conversations.json):**
- Mesma lógica: histórico de conversas persiste em arquivo
- Estrutura aninhada: `{conversation_id: {messages: [], metadata: {}}}`

### 2.2 Por que não SQLite/PostgreSQL?

| Aspecto | JSON | SQLite | PostgreSQL |
|---------|------|--------|------------|
| Setup | Zero | Baixo | Alto |
| Queries complexas | Não | Sim | Sim |
| Concorrência | Baixa | Média | Alta |
| Uso neste projeto | Ideal | Overkill | Overkill |

---

## 3. RAG (Retrieval-Augmented Generation)

### 3.1 Por que usar RAG?

**Problema sem RAG:**
- LLM tem conhecimento limitado ao treinamento
- Pode "alucinar" comandos incorretos
- Não conhece documentação específica

**Solução com RAG:**
```
Query → Embedding → Busca FAISS → Top-K documentos → Contexto para LLM
```

### 3.2 Por que FAISS?

**Comparação de índices vetoriais:**

| Biblioteca | Performance | Memória | Simplicidade |
|------------|-------------|---------|--------------|
| **FAISS** | Excelente | Baixa | Alta |
| Pinecone | Excelente | Cloud | Média (API) |
| ChromaDB | Boa | Média | Alta |
| Milvus | Excelente | Alta | Baixa |

**FAISS foi escolhido porque:**
- **Offline**: Não depende de serviços externos
- **Performance**: Busca em milhões de vetores em ms
- **Meta (Facebook)**: Biblioteca madura e bem documentada
- **CPU/GPU**: Funciona em ambos

```python
class RAGService:
    def __init__(self):
        self.index: Optional[faiss.Index] = None
        self.dimension = 384  # all-MiniLM-L6-v2
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
```

---

## 4. Arquitetura ReAct (Reason + Act)

### 4.1 O que é ReAct?

Padrão arquitetural onde o LLM **raciocina** antes de **agir**:

```
1. REASON: Analisar query e decidir recursos necessários
2. ACT: Executar apenas o que foi decidido
3. OBSERVE: Avaliar se precisa de mais dados
4. RESPOND: Gerar resposta final
```

### 4.2 Implementação no Orchestrator

```python
class ReactOrchestrator:
    """
    Orquestrador com arquitetura ReAct.
    
    FLUXO:
    1. classify_intent() - ML + regras decide GREETING/CASUAL/TECHNICAL
    2. Se GREETING/CASUAL -> resposta direta
    3. Se TECHNICAL -> LLM planner decide agent_commands, use_rag, etc.
    """
    
    async def create_plan(self, query: str) -> ExecutionPlan:
        """ETAPA 1: Classificar intenção e criar plano"""
        intent = await classify_intent(query)
        
        if intent == "GREETING":
            return ExecutionPlan(intent="GREETING", response_style="CHAT")
        
        if intent == "TECHNICAL":
            # LLM decide quais recursos usar
            prompt = build_planner_prompt(query)
            response = await call_llm_classify(prompt)
            return parse_plan(response)
    
    async def execute_plan(self, plan: ExecutionPlan, query: str) -> ExecutionContext:
        """ETAPA 2: Executar apenas o que o plano pede"""
        context = ExecutionContext()
        
        if plan.use_agent:
            context.agent_data = await execute_agent_commands(plan.agent_commands)
        
        if plan.use_rag:
            context.rag_data = await search_rag(query)
        
        return context
    
    async def generate_response(self, query: str, context: ExecutionContext) -> str:
        """ETAPA 4: Gerar resposta final"""
        prompt = build_response_prompt(query, context.build_context())
        return await call_llm(prompt)
```

### 4.3 Benefícios do ReAct

- **Sem desperdício**: RAG/Web só quando necessário
- **Transparência**: Plano explicito (debug fácil)
- **Flexibilidade**: Fácil adicionar novos recursos

---

## 5. Exemplos de POO no Projeto

### 5.1 Dataclasses para Estruturas de Dados

```python
from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class ExecutionPlan:
    """Plano de execução decidido pelo LLM"""
    intent: str                                    # GREETING, CASUAL, TECHNICAL
    use_agent: bool = False
    agent_commands: List[str] = field(default_factory=list)
    use_rag: bool = False
    use_web: bool = False
    response_style: str = "CHAT"                   # CHAT, ANALYZE, TUTORIAL
    reasoning: str = ""
    
    def to_dict(self) -> dict:
        """Serialização para JSON"""
        return {
            "intent": self.intent,
            "use_agent": self.use_agent,
            "agent_commands": self.agent_commands,
            "use_rag": self.use_rag,
            "use_web": self.use_web,
            "response_style": self.response_style,
            "reasoning": self.reasoning
        }


@dataclass
class ExecutionContext:
    """Contexto coletado durante execução"""
    agent_data: Optional[str] = None
    rag_data: Optional[str] = None
    rag_similarity: float = 0.0
    web_data: Optional[str] = None
    sources: List[str] = field(default_factory=list)
    
    def has_data(self) -> bool:
        """Verifica se há dados coletados"""
        return any([self.agent_data, self.rag_data, self.web_data])
    
    def build_context(self) -> str:
        """Monta contexto formatado para o LLM"""
        parts = []
        if self.agent_data:
            parts.append(self.agent_data)
        if self.rag_data:
            parts.append(f"[BASE DE CONHECIMENTO]\n{self.rag_data}")
        if self.web_data:
            parts.append(f"[PESQUISA WEB]\n{self.web_data}")
        return "\n\n".join(parts) if parts else ""
```

### 5.2 Classes de Serviço (Encapsulamento)

```python
class LLMService:
    """
    Serviço de gerenciamento do LLM
    Implementa quantização 8-bit para balanço qualidade/VRAM
    """
    
    def __init__(self):
        self.model = None
        self.tokenizer = None
        self.device = None
        self.model_name = None
    
    def load_model(self):
        """Carrega o modelo com quantização 8-bit"""
        if torch.cuda.is_available():
            self.device = "cuda"
            # Configurar quantização
            quantization_config = BitsAndBytesConfig(load_in_8bit=True)
            self.model = AutoModelForCausalLM.from_pretrained(
                MODEL_NAME,
                quantization_config=quantization_config,
                device_map="auto"
            )
        else:
            self.device = "cpu"
            # Fallback para modelo leve
            self.model = AutoModelForCausalLM.from_pretrained(FALLBACK_MODEL)


class RAGService:
    """Serviço de gerenciamento do índice FAISS"""
    
    def __init__(self):
        self.index: Optional[faiss.Index] = None
        self.metadata: List[Dict[str, Any]] = []
        self.dimension = 384
        self.embedding_model = None
    
    def load_or_create_index(self):
        """Carrega índice existente ou cria novo"""
        if FAISS_INDEX_PATH.exists():
            self.index = faiss.read_index(str(FAISS_INDEX_PATH))
        else:
            self.index = faiss.IndexFlatIP(self.dimension)
    
    def search(self, query: str, top_k: int = 5) -> List[Dict]:
        """Busca documentos similares"""
        query_vector = self.embedding_model.encode([query])
        scores, indices = self.index.search(query_vector, top_k)
        return [self.metadata[i] for i in indices[0]]
```

### 5.3 Modelos Pydantic (Validação e Serialização)

```python
from pydantic import BaseModel, Field

class ChatQuery(BaseModel):
    """Requisição de chat do usuário via Gateway"""
    text: str = Field(..., min_length=1, max_length=2000)
    user_id: Optional[str] = None
    conversation_id: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "text": "Como instalar nginx?",
                "user_id": "user123"
            }
        }


class LLMResponse(BaseModel):
    """Resposta da inferência do LLM"""
    generated_text: str
    tokens_generated: int
    inference_time_ms: float


class AgentExecuteRequest(BaseModel):
    """Requisição para executar comando no agent Linux"""
    command: str = Field(..., description="Comando da whitelist")
    params: Optional[Dict[str, Any]] = None
```

### 5.4 Aplicação TUI com Herança

```python
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer

class LanneApp(App):
    """Aplicação Textual principal - Herda de App"""
    
    TITLE = "Lanne AI - Linux Assistant"
    
    CSS = """
    Screen { background: $surface; }
    .ascii-logo { color: $accent; text-align: center; }
    """
    
    def __init__(self):
        super().__init__()
        self.api_client = LanneAPIClient()
    
    def compose(self) -> ComposeResult:
        """Composição da interface"""
        yield Header()
        yield Footer()
    
    async def on_mount(self):
        """Evento ao montar aplicação"""
        await self.push_screen(LoginScreen())
```

---

## 6. Arquitetura de Microserviços

### 6.1 Diagrama de Microserviços

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        LANNE AI - MICROSERVIÇOS                          │
└─────────────────────────────────────────────────────────────────────────┘

    ┌─────────────────────────────────────────────────────────────────┐
    │                         CLIENTES                                 │
    │  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐          │
    │  │  Website    │    │  TUI Linux  │    │  API REST   │          │
    │  │  (HTML/JS)  │    │  (Textual)  │    │  (Externo)  │          │
    │  └──────┬──────┘    └──────┬──────┘    └──────┬──────┘          │
    └─────────┼──────────────────┼──────────────────┼─────────────────┘
              │                  │                  │
              └──────────────────┼──────────────────┘
                                 │ HTTP/JSON
                                 ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                           API GATEWAY :8000                              │
│                     (Roteamento, CORS, Proxy)                            │
└────────────────────────────────┬────────────────────────────────────────┘
                                 │
                                 │ Valida Token JWT
                                 ▼
                       ┌─────────────────┐
                       │  AUTH SERVICE   │
                       │     :8007       │
                       │                 │
                       │ • Registro      │
                       │ • Login JWT     │
                       │ • Validação     │
                       │                 │
                       │ [users.json]    │
                       └────────┬────────┘
                                │
                                │ Token válido? → Libera acesso
                                ▼
                       ┌─────────────────┐
                       │  ORCHESTRATOR   │◀──────────────────────────────┐
                       │     :8001       │                               │
                       │                 │                               │
                       │ • Classificação │                               │
                       │ • ReAct/Planner │                               │
                       │ • Orquestração  │                               │
                       │                 │                               │
                       │ [ML Classifier] │                               │
                       └────────┬────────┘                               │
                                │                                        │
         ┌──────────────────────┼──────────────────────┐                 │
         │                      │                      │                 │
         ▼                      ▼                      ▼                 │
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐        │
│  CONVERSATION   │    │   INFERENCE     │    │   RAG SERVICE   │        │
│     :8006       │    │     :8002       │    │     :8003       │        │
│                 │    │                 │    │                 │        │
│ • Histórico     │    │ • Qwen2.5-7B    │    │ • FAISS Index   │        │
│ • Memória       │    │ • Quantização   │    │ • Embeddings    │        │
│ • Contexto      │    │ • Geração texto │    │ • Busca vetorial│        │
│                 │    │                 │    │                 │        │
│[conversations]  │    │ [GPU/CUDA]      │    │ [faiss_index]   │        │
└────────┬────────┘    └─────────────────┘    └─────────────────┘        │
         │                                                               │
         │  Orchestrator busca histórico e salva após resposta           │
         └───────────────────────────────────────────────────────────────┘

         ┌──────────────────────┬──────────────────────┐
         │                      │                      │
         ▼                      ▼                      ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   WEB SEARCH    │    │  LINUX AGENT    │    │    METRICS      │
│     :8004       │    │    :9000        │    │     :8005       │
│                 │    │                 │    │                 │
│ • DuckDuckGo    │    │ • Whitelist cmd │    │ • Logs          │
│ • Pesquisa web  │    │ • Execução      │    │ • Latência      │
│ • Resultados    │    │ • Dados sistema │    │ • Monitoramento │
│                 │    │                 │    │                 │
│ [API externa]   │    │ [Máquina Linux] │    │ [metrics.jsonl] │
└─────────────────┘    └────────┬────────┘    └─────────────────┘
                                │
                                ▼
                     ┌─────────────────────┐
                     │  MÁQUINA LINUX DO   │
                     │      USUÁRIO        │
                     └─────────────────────┘
```

### 6.2 Comunicação entre Serviços

```
┌───────────────────────────────────────────────────────────────┐
│                    PROTOCOLO DE COMUNICAÇÃO                    │
├───────────────────────────────────────────────────────────────┤
│                                                               │
│   Cliente ───HTTP/JSON───▶ Gateway ───HTTP/JSON───▶ Serviços  │
│                                                               │
│   Endpoints públicos (sem auth): /register, /login            │
│   Endpoints protegidos: /* (requer JWT válido)                │
│   Endpoints internos: /internal/* (entre serviços)            │
│                                                               │
├───────────────────────────────────────────────────────────────┤
│                                                               │
│   FLUXO DE AUTENTICAÇÃO:                                      │
│                                                               │
│   1. Cliente ──POST /login──▶ Gateway ──▶ Auth :8007          │
│      └──▶ Retorna Token JWT                                   │
│                                                               │
│   2. Cliente ──POST /chat + JWT──▶ Gateway                    │
│      └──▶ Gateway valida JWT com Auth :8007                   │
│          └──▶ Se válido: roteia para Orchestrator :8001       │
│          └──▶ Se inválido: retorna 401 Unauthorized           │
│                                                               │
├───────────────────────────────────────────────────────────────┤
│                                                               │
│   Gateway :8000                                               │
│      │                                                        │
│      ├──▶ POST /register ────────▶ Auth :8007 (público)       │
│      ├──▶ POST /login ───────────▶ Auth :8007 (público)       │
│      │                                                        │
│      │   [APÓS VALIDAR JWT COM AUTH]                          │
│      ├──▶ POST /chat ────────────▶ Orchestrator :8001         │
│      └──▶ GET  /conversations ───▶ Conversation :8006         │
│                                                               │
│   Orchestrator :8001                                          │
│      │                                                        │
│      ├──▶ GET  /conversations/{id} ─▶ Conversation :8006      │
│      │        (busca histórico para contexto)                 │
│      │                                                        │
│      ├──▶ POST /internal/generate ──▶ Inference :8002         │
│      ├──▶ POST /internal/search ────▶ RAG :8003               │
│      ├──▶ POST /internal/web_search ▶ Web Search :8004        │
│      ├──▶ POST /execute ────────────▶ Agent :9000             │
│      │                                                        │
│      └──▶ POST /conversations/{id} ─▶ Conversation :8006      │
│               (salva mensagem + resposta)                     │
│                                                               │
└───────────────────────────────────────────────────────────────┘
```

### 6.2 Responsabilidades dos Serviços

| Serviço | Porta | Responsabilidade |
|---------|-------|------------------|
| **Gateway** | 8000 | Roteamento, CORS, proxy reverso |
| **Orchestrator** | 8001 | ReAct, classificação, orquestração |
| **Inference** | 8002 | LLM Qwen2.5, geração de texto |
| **RAG** | 8003 | FAISS, busca semântica |
| **Web Search** | 8004 | DuckDuckGo, pesquisa web |
| **Metrics** | 8005 | Logs, latência, métricas |
| **Conversation** | 8006 | Histórico, memória, contexto |
| **Auth** | 8007 | JWT, usuários, sessões |
| **Agent** | 9000 | Comandos Linux remotos |

### 6.3 Por que essas Portas?

| Porta | Serviço | Justificativa |
|-------|---------|---------------|
| **8000** | Gateway | Porta padrão do Uvicorn/FastAPI, fácil de lembrar |
| **8001-8007** | Serviços internos | Sequência lógica a partir do Gateway |
| **9000** | Agent Linux | Separado na faixa 9xxx por rodar em máquina diferente |

**Por que portas altas (8000+)?**
- Portas abaixo de 1024 requerem privilégios de root
- Faixa 8000-9000 é comum para desenvolvimento web
- Evita conflitos com serviços do sistema (80, 443, 22, etc.)
- Padrão de mercado: Uvicorn/Django (8000), Tomcat (8080), Node (3000)

**Organização sequencial:**
```
8000 → Gateway (entrada única)
8001 → Orchestrator (cérebro)
8002 → Inference (LLM)
8003 → RAG (busca)
8004 → Web Search
8005 → Metrics
8006 → Conversation
8007 → Auth
9000 → Agent (máquina remota)
```

### 6.4 Por que Microserviços?

**Vantagens:**
- **Escalabilidade**: Cada serviço escala independente
- **Manutenibilidade**: Código isolado por domínio
- **Desenvolvimento paralelo**: Equipes trabalham em serviços diferentes
- **Tolerância a falhas**: Falha em um serviço não derruba o sistema

**Comunicação:**
- Síncrona via HTTP/REST (JSON)
- Endpoints prefixados com `/internal/` para chamadas internas

---

## 7. Requisitos do Sistema

### 7.1 Requisitos Funcionais

| RF | Descrição |
|----|-----------|
| RF01 | O sistema deve classificar intenções em GREETING, CASUAL ou TECHNICAL |
| RF02 | O sistema deve buscar documentos relevantes via RAG |
| RF03 | O sistema deve gerar respostas em português brasileiro |
| RF04 | O sistema deve persistir histórico de conversas |
| RF05 | O sistema deve autenticar usuários via JWT |
| RF06 | O sistema deve executar comandos em máquinas Linux remotas |
| RF07 | O sistema deve buscar informações na web quando RAG for insuficiente |
| RF08 | O sistema deve lembrar contexto de mensagens anteriores |

### 7.2 Requisitos Não-Funcionais

| RNF | Descrição |
|-----|-----------|
| RNF01 | Tempo de resposta < 5 segundos para queries técnicas |
| RNF02 | Suporte a quantização 8-bit para GPUs com 8GB+ VRAM |
| RNF03 | Disponibilidade de fallback para CPU (modelo leve) |
| RNF04 | Interface TUI responsiva com feedback visual |
| RNF05 | API RESTful com documentação OpenAPI (Swagger) |
| RNF06 | Logs estruturados para debugging |
| RNF07 | CORS habilitado para frontend web |
| RNF08 | Tokens JWT com expiração de 30 dias |

---

## 8. Tecnologias Utilizadas

### 8.1 Backend

| Tecnologia | Versão | Uso |
|------------|--------|-----|
| Python | 3.11+ | Linguagem principal |
| FastAPI | Latest | Framework web assíncrono |
| Uvicorn | Latest | Servidor ASGI |
| Pydantic | v2 | Validação de dados |
| PyTorch | 2.x | Backend para LLM |
| Transformers | Latest | Carregamento de modelos HuggingFace |
| BitsAndBytes | Latest | Quantização 8-bit |

### 8.2 IA/ML

| Tecnologia | Uso |
|------------|-----|
| Qwen2.5-7B-Instruct | Modelo de linguagem principal |
| all-MiniLM-L6-v2 | Embeddings para RAG |
| FAISS | Índice vetorial |
| Scikit-learn | Classificador ML |

### 8.3 Frontend

| Tecnologia | Uso |
|------------|-----|
| Textual | TUI Python (terminal) |
| HTML/CSS/JS | Website |
| HTTPX | Cliente HTTP assíncrono |

---

## 9. Bibliotecas Importadas

### 9.1 requirements.txt Completo

```python
# ===== Core Framework =====
fastapi                    # Framework web assíncrono
uvicorn[standard]          # Servidor ASGI
pydantic                   # Validação de dados

# ===== HTTP Client =====
httpx                      # Cliente HTTP assíncrono

# ===== LLM & Inference =====
transformers               # Modelos HuggingFace
torch                      # Backend PyTorch
bitsandbytes               # Quantização 8-bit
accelerate                 # Otimização de modelos
sentencepiece              # Tokenização

# ===== RAG Service =====
faiss-cpu                  # Índice vetorial
numpy                      # Operações numéricas
sentence-transformers      # Embeddings

# ===== ML Classifier =====
scikit-learn               # Pipeline ML
joblib                     # Serialização de modelos

# ===== Auth & Persistence =====
PyJWT                      # Tokens JWT
SQLAlchemy                 # ORM (preparado para SQL futuro)
aiosqlite                  # SQLite assíncrono

# ===== Utilities =====
python-multipart           # Upload de arquivos
```

### 9.2 TUI (linux/requirements.txt)

```python
textual                    # Framework TUI
rich                       # Formatação terminal
httpx                      # Cliente HTTP
```

---

## 10. DFD Nível 1 - Fluxo de Dados

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          DFD NÍVEL 1 - LANNE AI                          │
└─────────────────────────────────────────────────────────────────────────┘

                              USUÁRIO
                                 │
                    ┌────────────┴────────────┐
                    │                         │
                    ▼                         ▼
            ┌───────────────┐         ┌───────────────┐
            │   Autenticar  │         │  Enviar Query │
            │   Usuário     │         │   de Chat     │
            └───────┬───────┘         └───────┬───────┘
                    │                         │
                    ▼                         ▼
            ┌───────────────┐         ┌───────────────┐
            │  AUTH SERVICE │         │    GATEWAY    │
            │    :8007      │         │     :8000     │
            └───────┬───────┘         └───────┬───────┘
                    │                         │
                    │ Token JWT               │ Query
                    ▼                         ▼
            ┌───────────────┐         ┌───────────────┐
            │  users.json   │         │ ORCHESTRATOR  │
            │  (Armazém)    │         │    :8001      │
            └───────────────┘         └───────┬───────┘
                                              │
                    ┌─────────────────────────┼─────────────────────────┐
                    │                         │                         │
                    ▼                         ▼                         ▼
            ┌───────────────┐         ┌───────────────┐         ┌───────────────┐
            │  INFERENCE    │         │   RAG/FAISS   │         │   AGENT       │
            │    :8002      │         │    :8003      │         │   :9000       │
            └───────┬───────┘         └───────┬───────┘         └───────┬───────┘
                    │                         │                         │
                    │ Resposta LLM            │ Documentos              │ Dados Sistema
                    └─────────────────────────┼─────────────────────────┘
                                              │
                                              ▼
                                      ┌───────────────┐
                                      │ CONVERSATION  │
                                      │    :8006      │
                                      └───────┬───────┘
                                              │
                                              ▼
                                      ┌───────────────┐
                                      │conversations  │
                                      │   .json       │
                                      └───────────────┘
                                              │
                                              ▼
                                      ┌───────────────┐
                                      │   Resposta    │
                                      │   ao Usuário  │
                                      └───────────────┘
```

### 10.1 Fluxo Detalhado

```
USUÁRIO ──(1)──▶ Login/Registro
              │
              └──▶ AUTH SERVICE ──▶ Valida/Cria ──▶ users.json
                        │
                        └──▶ Retorna Token JWT
                        
USUÁRIO ──(2)──▶ Envia Pergunta
              │
              └──▶ GATEWAY ──▶ Roteia para Orchestrator
                        │
                        └──▶ ORCHESTRATOR
                              │
                              ├──▶ Classifica Intenção (ML)
                              │
                              ├──▶ Se TECHNICAL:
                              │     ├──▶ RAG (busca docs)
                              │     ├──▶ AGENT (dados sistema)
                              │     └──▶ WEB SEARCH (se necessário)
                              │
                              ├──▶ INFERENCE (gera resposta)
                              │
                              └──▶ CONVERSATION (salva histórico)
                                        │
                                        └──▶ conversations.json

SERVIDOR ──(3)──▶ Retorna Resposta ao Usuário
```

---

## 11. Estrutura do Projeto

```
lanne.ai-ia_integrada/
├── auth-service/              # Autenticação JWT
│   ├── main.py                # Endpoints /register, /login, /validate
│   └── users.json             # Persistência de usuários
│
├── conversation-service/      # Histórico e memória
│   ├── main.py                # CRUD de conversas
│   └── conversations.json     # Persistência de conversas
│
├── gateway-service/           # API Gateway
│   └── main.py                # Roteamento e CORS
│
├── orchestrator-service/      # Cérebro do sistema
│   ├── main.py                # ReAct, classificação, orquestração
│   ├── intent_classifier.joblib  # Modelo ML treinado
│   └── intent_dataset.json    # Dataset de treinamento
│
├── inference-service/         # LLM local
│   └── main.py                # Qwen2.5 + quantização
│
├── rag-service/               # Busca vetorial
│   ├── main.py                # FAISS + embeddings
│   └── data/                  # Índice e documentos
│
├── web-search-service/        # Pesquisa web
│   └── main.py                # DuckDuckGo API
│
├── metrics-service/           # Métricas e logs
│   └── main.py                # Coleta de métricas
│
├── lanne-schemas/             # Modelos Pydantic compartilhados
│   └── lanne_schemas/
│       └── models.py          # ChatQuery, LLMResponse, etc.
│
├── linux/                     # Cliente TUI
│   ├── lanne_client.py        # Cliente principal
│   ├── lanne_agent.py         # Agent executor
│   └── tui/                   # Interface Textual
│
├── website/                   # Frontend Web
│   ├── pages/                 # HTML
│   ├── scripts/               # JavaScript
│   └── css/                   # Estilos
│
├── run.py                     # Inicializador completo
├── requirements.txt           # Dependências Python
└── contexto.md                # Este documento
```
