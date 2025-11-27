"""
Orchestrator Service - Cerebro do sistema Lanne AI
Porta: 8001
Responsabilidades:
- Classificacao de intencao (TECHNICAL, CASUAL, GREETING)
- Gerenciamento do fluxo de RAG hibrido
- Orquestracao de chamadas aos servicos inference, rag e web-search

MUDANCAS v2:
- Removidos TODOS os emojis
- Prompts otimizados para Qwen2.5 (formato ChatML)
- Pos-processamento de resposta melhorado
- Parametros de geracao mais restritivos

MUDANCAS v3:
- collect_agent_logs agora usa LLM para decidir comandos
- Suporta ate 3 comandos por query
- Sem fallbacks - LLM decide tudo
"""

from fastapi import FastAPI, HTTPException, status
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import httpx
from typing import Optional, AsyncGenerator
import logging
import joblib
from pathlib import Path
import asyncio
import json
import re

from lanne_schemas import (
    ChatQuery,
    ChatResponse,
    LLMRequest,
    RAGSearchRequest,
    WebSearchRequest,
    IntentClassification,
    AgentExecuteRequest
)

# Configuracao de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Inicializar FastAPI
app = FastAPI(
    title="Lanne AI Orchestrator Service",
    description="Servico de orquestracao e roteamento de intencao",
    version="3.0.0"
)

# Configurar CORS para permitir streaming do navegador
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configurar encoding UTF-8 para respostas
@app.middleware("http")
async def add_charset(request, call_next):
    response = await call_next(request)
    if "application/json" in response.headers.get("Content-Type", ""):
        response.headers["Content-Type"] = "application/json; charset=utf-8"
    return response

# Carregar modelo de classificacao e dataset
CLASSIFIER_PATH = Path(__file__).parent / "intent_classifier.joblib"
DATASET_PATH = Path(__file__).parent / "intent_dataset.json"
USE_ML_CLASSIFIER = False
classifier_pipeline = None
TECHNICAL_KEYWORDS = []
GREETING_KEYWORDS = []
dataset_rules = {}

@app.on_event("startup")
async def load_classifier():
    """Carrega modelo ML e dataset de keywords."""
    global classifier_pipeline, TECHNICAL_KEYWORDS, GREETING_KEYWORDS, dataset_rules
    
    try:
        import json
        with open(DATASET_PATH, 'r', encoding='utf-8') as f:
            dataset = json.load(f)
        
        for category, words in dataset['keywords']['TECHNICAL'].items():
            TECHNICAL_KEYWORDS.extend(words)
        for category, words in dataset['keywords']['GREETING'].items():
            GREETING_KEYWORDS.extend(words)
        
        dataset_rules = dataset.get('rules', {})
        
        logger.info(f"[OK] Dataset carregado: {len(TECHNICAL_KEYWORDS)} technical, {len(GREETING_KEYWORDS)} greeting keywords")
    except Exception as e:
        logger.error(f"[ERRO] Erro ao carregar dataset: {e}")
    
    try:
        classifier_pipeline = joblib.load(CLASSIFIER_PATH)
        logger.info(f"[OK] Intent classifier (ML) carregado de {CLASSIFIER_PATH}")
    except Exception as e:
        logger.error(f"[AVISO] Erro ao carregar classifier ML: {e}")
        logger.warning("Sistema funcionara apenas com keywords")


# URLs dos servicos internos
INFERENCE_URL = "http://localhost:8002"
RAG_URL = "http://localhost:8003"
WEB_SEARCH_URL = "http://localhost:8004"

# Configuracao do Agent (mutavel - pode ser alterado via API)
AGENT_CONFIG = {
    "url": "http://localhost:9000",
    "enabled": True
}

# Constantes
CONFIDENCE_THRESHOLD = 0.75

# =============================================================================
# DETECCAO DE TIPO DE PEDIDO
# =============================================================================

EXECUTION_KEYWORDS = [
    # Verbos de execução
    "executa", "execute", "execute pra mim", "executa pra mim",
    "roda", "rode", "roda pra mim", "rode pra mim",
    "mostra", "mostre", "me mostra", "me mostre", 
    "veja", "verifica", "verifique", "checa", "cheque",
    "analisa", "analise", "diagnostica", "diagnostique",
    "le", "leia", "ve", "olha", "olhe",
    "consegue ver", "pode ver", "da pra ver",
    "me diz", "me fala", "qual e", "quais sao",
    "ta como", "esta como", "como esta", "como ta",
    "pode executar", "consegue executar",
    "roda ai", "executa ai", "verifica ai",
    "me passa", "passa pra mim",
    # Novos - pedidos diretos
    "executa o comando", "roda o comando", "execute o comando",
    "consegue executar", "pode executar", "da pra executar",
    "consegue rodar", "pode rodar", "da pra rodar",
    "executa pra mim", "roda pra mim", "faz pra mim",
    "pra mim", "pra eu ver", "quero ver",
]

TUTORIAL_KEYWORDS = [
    "como faco", "como fazer", "como eu faco",
    "como configuro", "como configurar",
    "como instalo", "como instalar", 
    "ensina", "me ensina", "tutorial",
    "qual comando", "quais comandos",
    "passo a passo", "explica", "explique",
    "o que e", "o que significa",
    "para que serve", "pra que serve",
]


def detect_request_type(query: str) -> str:
    """
    Detecta se o usuario quer:
    - EXECUTE: que a IA execute/analise algo no sistema
    - TUTORIAL: que a IA ensine como fazer algo
    - MIXED: ambos ou ambiguo
    """
    query_lower = query.lower()
    
    exec_matches = sum(1 for kw in EXECUTION_KEYWORDS if kw in query_lower)
    tutorial_matches = sum(1 for kw in TUTORIAL_KEYWORDS if kw in query_lower)
    
    exec_patterns = [
        r"(me )?(mostra|mostre|ve|veja|verifica|analisa|roda|executa)",
        r"(consegue|pode|da pra) (ver|executar|rodar|mostrar)",
        r"(qual|quais|como) (e|esta|ta) (o|a|meu|minha)",
        r"(me )?diz (o|qual|como)",
        # Novos padrões
        r"(executa|roda|execute|rode) (o |esse |este )?(comando)",
        r"(executa|roda) (pra|para) (mim|eu)",
        r"(consegue|pode|da pra) (executar|rodar) (pra|para)? ?(mim)?",
        r"(quero|preciso) (ver|saber)",
    ]
    
    tutorial_patterns = [
        r"como (eu )?(faco|fazer|configuro|instalo)",
        r"(me )?(ensina|explica)",
        r"qual (o )?comando (para|pra)",
    ]
    
    for pattern in exec_patterns:
        if re.search(pattern, query_lower):
            exec_matches += 2
    
    for pattern in tutorial_patterns:
        if re.search(pattern, query_lower):
            tutorial_matches += 2
    
    logger.info(f"[DETECT] Request type: exec={exec_matches}, tutorial={tutorial_matches}")
    
    if exec_matches > tutorial_matches + 1:
        return "EXECUTE"
    elif tutorial_matches > exec_matches + 1:
        return "TUTORIAL"
    else:
        return "MIXED"


# =============================================================================
# PROMPTS OTIMIZADOS PARA QWEN2.5 (FORMATO CHATML)
# =============================================================================

SYSTEM_PROMPT = """Voce e Lanne, uma assistente tecnica especializada em Linux e Debian.

REGRAS OBRIGATORIAS:
1. Responda APENAS em portugues brasileiro
2. NUNCA use emojis ou emoticons
3. NUNCA repita comandos com variacoes numericas (como -n 1, -n 10, -n 100...)
4. Seja objetiva e concisa (maximo 4 paragrafos)
5. Use crases para destacar comandos: `comando`
6. Quando analisar dados do sistema, foque nos problemas encontrados"""


def build_execution_prompt(query: str, context: str, has_agent_data: bool) -> str:
    """
    Prompt para quando o usuario pediu para EXECUTAR/ANALISAR algo.
    Foca em analisar os dados coletados, nao em dar instrucoes.
    """
    if has_agent_data:
        return f"""<|im_start|>system
{SYSTEM_PROMPT}

TAREFA ATUAL: O usuario pediu para voce analisar o sistema. Voce JA COLETOU os dados.
Sua funcao agora e ANALISAR os dados, nao ensinar comandos.
<|im_end|>
<|im_start|>user
Pergunta do usuario: {query}

Dados coletados do sistema:
{context[:2500]}

Analise os dados acima e responda:
- O que voce encontrou
- Se ha erros ou problemas, destaque-os
- Se esta tudo normal, diga isso brevemente
<|im_end|>
<|im_start|>assistant
"""
    else:
        return f"""<|im_start|>system
{SYSTEM_PROMPT}
<|im_end|>
<|im_start|>user
{query}

Contexto disponivel:
{context[:2000]}

Nao foi possivel coletar dados do sistema. Explique brevemente como o usuario pode verificar manualmente.
<|im_end|>
<|im_start|>assistant
"""


def build_tutorial_prompt(query: str, context: str) -> str:
    """
    Prompt para quando o usuario quer INSTRUCOES/TUTORIAL.
    """
    return f"""<|im_start|>system
{SYSTEM_PROMPT}

TAREFA ATUAL: O usuario quer aprender como fazer algo.
De instrucoes claras com no maximo 3 comandos.
<|im_end|>
<|im_start|>user
{query}

Referencia:
{context[:2000]}
<|im_end|>
<|im_start|>assistant
"""


def build_mixed_prompt(query: str, context: str, has_agent_data: bool) -> str:
    """
    Prompt para casos ambiguos.
    """
    agent_note = ""
    if has_agent_data:
        agent_note = "Os dados abaixo sao do sistema do usuario. Analise-os primeiro."
    
    return f"""<|im_start|>system
{SYSTEM_PROMPT}
<|im_end|>
<|im_start|>user
{query}

{agent_note}

Contexto:
{context[:2000]}

Responda de forma pratica e direta.
<|im_end|>
<|im_start|>assistant
"""


# =============================================================================
# COLETA DE DADOS DO AGENT (v3 - LLM DECIDE)
# =============================================================================

# Todos os comandos disponiveis no agent
AGENT_COMMANDS = {
    # Logs
    "journalctl": "Logs do systemd - erros gerais, eventos recentes",
    "syslog": "Arquivo /var/log/syslog - log tradicional",
    "dmesg": "Mensagens do kernel - hardware, drivers, USB, GPU",
    "boot_log": "Log de inicializacao - problemas de boot",
    
    # Servicos
    "systemctl_list": "Lista servicos do systemd rodando",
    "systemctl_failed": "Servicos que falharam",
    
    # Recursos
    "disk_usage": "Uso de disco - particoes, espaco livre",
    "memory_detailed": "Uso de RAM e swap",
    "cpu_usage": "Uso de CPU e load average",
    "processes_top": "Processos consumindo mais recursos",
    
    # Rede
    "network_info": "Interfaces de rede - IP, MAC, status",
    "network_connections": "Conexoes ativas e portas abertas",
    
    # Sistema
    "os_release": "Informacoes do SO - distro, versao",
    "debian_version": "Versao especifica do Debian",
    "uptime": "Tempo que o sistema esta ligado",
    
    # Pacotes
    "apt_updates": "Atualizacoes disponiveis",
    "dpkg_list": "Pacotes instalados",
    
    # Usuarios
    "logged_users": "Usuarios logados no sistema",
}


def _build_agent_router_prompt(query: str) -> str:
    """Constroi prompt para o LLM decidir comandos"""
    
    commands_list = "\n".join(f"- {cmd}: {desc}" for cmd, desc in AGENT_COMMANDS.items())
    
    return f"""<|im_start|>system
Voce e um roteador de comandos para monitoramento Linux.
Analise a pergunta e decida quais comandos executar NO SISTEMA DO USUARIO.

COMANDOS DISPONIVEIS:
{commands_list}

MAPEAMENTO DE COMANDOS LINUX:
- who, w, usuarios logados -> logged_users
- free, memoria, ram -> memory_detailed
- df, disco, espaco -> disk_usage
- top, htop, processos -> processes_top
- ip, ifconfig, rede -> network_info
- netstat, ss, portas, conexoes -> network_connections
- uptime, tempo ligado -> uptime
- uname, versao, distro -> os_release
- journalctl, logs -> journalctl
- dmesg, kernel -> dmesg
- systemctl, servicos -> systemctl_list

REGRAS:
1. Se o usuario pede para EXECUTAR, RODAR, VER, MOSTRAR, VERIFICAR algo -> retorne o comando
2. Se o usuario menciona um comando Linux (who, free, df, top, etc) -> retorne o equivalente
3. Maximo 3 comandos, separados por virgula
4. APENAS retorne NONE se for conversa casual ou pedido de tutorial/explicacao

EXECUTE (retorne comandos):
- "executa o comando who" -> logged_users
- "roda o who pra mim" -> logged_users
- "mostra quem ta logado" -> logged_users
- "verifica a memoria" -> memory_detailed
- "como ta o disco" -> disk_usage
- "me mostra os processos" -> processes_top
- "qual meu IP" -> network_info
- "ve o uptime" -> uptime
- "quais suas capacidades" -> NONE
- "o que voce sabe fazer" -> NONE

NAO EXECUTE (retorne NONE):
- "ola tudo bem" -> NONE
- "como instalar apache" -> NONE
- "o que e o comando who" -> NONE
- "me explica o top" -> NONE
- "quem e voce" -> NONE
<|im_end|>
<|im_start|>user
{query}
<|im_end|>
<|im_start|>assistant
"""


def _quick_keyword_check(query: str) -> list:
    """
    Checagem rapida de keywords para casos obvios.
    Evita chamar o LLM para queries simples.
    """
    q = query.lower().strip()
    
    # Mapeamento direto de palavras-chave -> comandos
    direct_map = {
        "memoria": ["memory_detailed"],
        "memória": ["memory_detailed"],
        "ram": ["memory_detailed"],
        "disco": ["disk_usage"],
        "disk": ["disk_usage"],
        "rede": ["network_info"],
        "network": ["network_info"],
        "ip": ["network_info"],
        "processos": ["processes_top"],
        "processo": ["processes_top"],
        "cpu": ["cpu_usage"],
        "uptime": ["uptime"],
        "logs": ["journalctl"],
        "log": ["journalctl"],
        "servicos": ["systemctl_list"],
        "serviços": ["systemctl_list"],
    }
    
    # Se query é só uma palavra, usar mapeamento direto
    if len(q.split()) <= 2:
        for keyword, cmds in direct_map.items():
            if keyword in q:
                return cmds
    
    # Mapeamento de comandos Linux mencionados
    linux_commands = {
        "who": "logged_users",
        "w ": "logged_users",
        "free": "memory_detailed",
        "df": "disk_usage",
        "top": "processes_top",
        "htop": "processes_top",
        "ps": "processes_top",
        "ifconfig": "network_info",
        "ip addr": "network_info",
        "netstat": "network_connections",
        "ss ": "network_connections",
        "journalctl": "journalctl",
        "dmesg": "dmesg",
        "systemctl": "systemctl_list",
        "uname": "os_release",
    }
    
    # Se menciona um comando Linux especifico
    for linux_cmd, agent_cmd in linux_commands.items():
        if linux_cmd in q:
            return [agent_cmd]
    
    return []  # Vazio = deixa o LLM decidir


async def _llm_decide_commands(query: str) -> list:
    """Usa o LLM para decidir quais comandos executar"""
    
    # Primeiro tenta checagem rapida
    quick_result = _quick_keyword_check(query)
    if quick_result:
        logger.info(f"[AGENT] Quick match: {quick_result}")
        return quick_result
    
    prompt = _build_agent_router_prompt(query)
    
    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.post(
            f"{INFERENCE_URL}/internal/classify",
            json={
                "prompt": prompt,
                "max_tokens": 50,
                "temperature": 0.1,
                "top_p": 0.9
            }
        )
        
        if response.status_code != 200:
            logger.error(f"[AGENT] LLM retornou {response.status_code}")
            return []
        
        result = response.json()
        text = result.get("generated_text", "").strip()
        
        logger.info(f"[AGENT] LLM respondeu: '{text[:100]}'")
        
        # Se vazio, retorna vazio
        if not text:
            return []
        
        # Limpar resposta - pegar primeira linha, remover lixo
        first_line = text.split('\n')[0].strip()
        
        # Remover prefixos comuns que o LLM pode adicionar
        prefixes_to_remove = [
            "comandos:", "comando:", "execute:", "executar:",
            "->", "=>", ":", "-"
        ]
        for prefix in prefixes_to_remove:
            if first_line.lower().startswith(prefix):
                first_line = first_line[len(prefix):].strip()
        
        # Limpar caracteres especiais
        cleaned = re.sub(r'[^a-zA-Z0-9_,\s]', '', first_line)
        cleaned = cleaned.upper().strip()
        
        logger.info(f"[AGENT] Apos limpeza: '{cleaned}'")
        
        if cleaned == "NONE" or not cleaned:
            return []
        
        # Validar comandos
        commands = []
        for cmd in cleaned.lower().replace(" ", "").split(","):
            cmd = cmd.strip()
            if cmd in AGENT_COMMANDS and cmd not in commands:
                commands.append(cmd)
        
        if not commands:
            logger.warning(f"[AGENT] Nenhum comando valido extraido de: '{text[:50]}'")
        
        return commands[:3]


async def collect_agent_logs(query: str) -> Optional[str]:
    """
    Coleta dados do Agent Linux baseado na query.
    O LLM decide quais comandos executar.
    """
    logger.info(f"[AGENT] Processando: {query}")
    
    if not AGENT_CONFIG["enabled"]:
        logger.warning("[AGENT] Desabilitado")
        return None
    
    agent_url = AGENT_CONFIG["url"]
    
    # LLM decide os comandos
    try:
        commands = await _llm_decide_commands(query)
    except Exception as e:
        logger.error(f"[AGENT] Erro ao consultar LLM: {e}")
        return None
    
    if not commands:
        logger.info("[AGENT] LLM decidiu: NONE (nenhum comando necessario)")
        return None
    
    logger.info(f"[AGENT] Executando comandos: {commands}")
    
    # Executa comandos
    outputs = []
    
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            for cmd in commands:
                params = {"lines": "100"} if cmd == "journalctl" else {}
                
                response = await client.post(
                    f"{agent_url}/execute",
                    json={"command": cmd, "params": params}
                )
                
                if response.status_code == 200:
                    result = response.json()
                    output = result.get("stdout", "") or result.get("stderr", "")
                    
                    if output and len(output) > 10:
                        outputs.append((cmd, output[:2500]))
                        logger.info(f"[AGENT] {cmd}: {len(output)} chars")
    
    except Exception as e:
        logger.error(f"[AGENT] Erro na execucao: {e}")
        return None
    
    if not outputs:
        logger.warning("[AGENT] Nenhum comando retornou dados")
        return None
    
    # Formata resultado
    parts = ["[DADOS DO SISTEMA]", "=" * 50]
    
    for cmd, output in outputs:
        parts.append(f"\n>> {cmd.upper()}: {AGENT_COMMANDS[cmd]}")
        parts.append("-" * 40)
        parts.append(output)
    
    parts.append("\n" + "=" * 50)
    
    formatted = "\n".join(parts)
    logger.info(f"[AGENT] Total: {len(formatted)} chars de {len(outputs)} comando(s)")
    
    return formatted


# =============================================================================
# POS-PROCESSAMENTO DE RESPOSTA
# =============================================================================

def clean_response(text: str) -> str:
    """
    Limpa a resposta do LLM:
    - Remove emojis
    - Remove repeticoes
    - Remove tokens especiais
    """
    # Remover emojis
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"
        "\U0001F300-\U0001F5FF"
        "\U0001F680-\U0001F6FF"
        "\U0001F1E0-\U0001F1FF"
        "\U00002702-\U000027B0"
        "\U000024C2-\U0001F251"
        "]+",
        flags=re.UNICODE
    )
    text = emoji_pattern.sub('', text)
    
    # Remover tokens do ChatML
    text = re.sub(r'<\|im_start\|>.*?<\|im_end\|>', '', text, flags=re.DOTALL)
    text = re.sub(r'<\|im_start\|>', '', text)
    text = re.sub(r'<\|im_end\|>', '', text)
    text = re.sub(r'<\|endoftext\|>', '', text)
    
    # Remover tokens do Mistral (caso ainda use)
    text = re.sub(r'\[INST\].*?\[/INST\]', '', text, flags=re.DOTALL)
    text = re.sub(r'\[INST\]', '', text)
    text = re.sub(r'\[/INST\]', '', text)
    
    # Remover sequencias numericas repetidas
    text = re.sub(r'(\d+[\s,]+){4,}', '', text)
    
    # Remover linhas duplicadas
    lines = text.split('\n')
    seen = set()
    unique_lines = []
    for line in lines:
        line_normalized = re.sub(r'\d+', 'N', line.strip())
        if line_normalized not in seen or len(line_normalized) < 15:
            seen.add(line_normalized)
            unique_lines.append(line)
    text = '\n'.join(unique_lines)
    
    # Limpar espacos extras
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r' {2,}', ' ', text)
    
    return text.strip()


# =============================================================================
# PIPELINE TECNICO
# =============================================================================

async def handle_technical(query: str) -> ChatResponse:
    """
    Pipeline de RAG hibrido para consultas tecnicas
    """
    try:
        request_type = detect_request_type(query)
        logger.info(f"[PIPELINE] Tipo de request: {request_type}")
        
        # Etapa 1: Coleta de logs do agent
        logger.info("[PIPELINE] 1/4 - Coletando dados do agent...")
        agent_logs = await collect_agent_logs(query)
        has_agent_data = agent_logs is not None
        logger.info(f"[PIPELINE] Agent: {'coletado' if has_agent_data else 'sem dados'}")
        
        # Etapa 2: Busca interna no FAISS
        logger.info("[PIPELINE] 2/4 - Buscando na base de conhecimento...")
        rag_request = RAGSearchRequest(
            query=query,
            top_k=3,
            threshold=0.0
        )
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{RAG_URL}/internal/search",
                json=rag_request.model_dump()
            )
            response.raise_for_status()
            rag_response = response.json()
        
        logger.info("[PIPELINE] RAG search completo")
        
        max_similarity = rag_response.get("max_similarity", 0.0)
        documents = rag_response.get("documents", [])
        
        # Montar contexto
        context_parts = []
        sources = []
        used_web = False
        
        # Adicionar logs do agent PRIMEIRO
        if agent_logs:
            context_parts.append(agent_logs)
            sources.append("linux-agent")
        
        # Adicionar RAG se relevante
        if max_similarity >= CONFIDENCE_THRESHOLD:
            logger.info(f"[PIPELINE] Usando conhecimento interno (sim: {max_similarity:.2f})")
            rag_context = "\n\n".join([doc["text"][:500] for doc in documents])
            context_parts.append(f"[BASE DE CONHECIMENTO]\n{rag_context}")
            sources.extend([doc.get("metadata", {}).get("source", "internal") for doc in documents])
        else:
            # Fallback: buscar na web
            logger.info(f"[PIPELINE] 3/4 - Baixa similaridade ({max_similarity:.2f}), buscando na web...")
            
            web_query = f"Linux Debian {query}"
            web_request = WebSearchRequest(query=web_query, max_results=3)
            
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(
                    f"{WEB_SEARCH_URL}/internal/web_search",
                    json=web_request.model_dump()
                )
                response.raise_for_status()
                web_response = response.json()
            
            web_results = web_response.get("results", [])
            if web_results:
                web_context = "\n\n".join([
                    f"- {r.get('title', 'Sem titulo')}\n{r.get('snippet', '')[:300]}"
                    for r in web_results
                ])
                context_parts.append(f"[PESQUISA WEB]\n{web_context}")
                sources.extend([r.get("url", "") for r in web_results])
                used_web = True
        
        # Consolidar contexto
        context = "\n\n".join(context_parts)
        
        # Etapa 4: Gerar resposta
        logger.info("[PIPELINE] 4/4 - Gerando resposta...")
        
        if request_type == "EXECUTE":
            prompt = build_execution_prompt(query, context, has_agent_data)
        elif request_type == "TUTORIAL":
            prompt = build_tutorial_prompt(query, context)
        else:
            prompt = build_mixed_prompt(query, context, has_agent_data)
        
        logger.info(f"[PIPELINE] Usando prompt tipo: {request_type}")
        
        # Parametros otimizados para evitar loops
        llm_request = LLMRequest(
            prompt=prompt,
            max_tokens=400,
            temperature=0.3,
            top_p=0.85
        )
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{INFERENCE_URL}/internal/generate",
                json=llm_request.model_dump()
            )
            response.raise_for_status()
            llm_response = response.json()
        
        # Limpar resposta
        generated_text = llm_response["generated_text"].strip()
        cleaned_text = clean_response(generated_text)
        
        # Verificar se resposta ficou muito curta ou vazia
        if len(cleaned_text) < 20:
            cleaned_text = "Desculpe, nao consegui gerar uma resposta adequada. Pode reformular sua pergunta?"
        
        logger.info("[PIPELINE] Resposta gerada com sucesso")
        
        return ChatResponse(
            response=cleaned_text,
            intent="TECHNICAL",
            sources=sources,
            metadata={
                "rag_similarity": max_similarity,
                "used_web_fallback": used_web,
                "used_agent": has_agent_data,
                "request_type": request_type
            }
        )
        
    except Exception as e:
        logger.error(f"[PIPELINE] Erro: {e}", exc_info=True)
        
        # Fallback com dados do RAG se disponivel
        try:
            if 'rag_response' in locals() and rag_response.get("documents"):
                docs = rag_response["documents"][:2]
                formatted = "Informacoes encontradas:\n\n"
                for i, doc in enumerate(docs, 1):
                    text = doc.get("text", "")[:300]
                    formatted += f"{i}. {text}...\n\n"
                
                return ChatResponse(
                    response=formatted,
                    intent="TECHNICAL",
                    sources=[doc.get("metadata", {}).get("source", "") for doc in docs],
                    metadata={"error": str(e), "fallback": "rag_only"}
                )
        except:
            pass
        
        return ChatResponse(
            response=f"Erro no pipeline tecnico: {str(e)}",
            intent="TECHNICAL",
            sources=[],
            metadata={"error": str(e)}
        )


# =============================================================================
# CLASSIFICACAO DE INTENCAO
# =============================================================================

GREETING_RESPONSES = [
    "Ola! Sou Lanne, sua assistente especialista em Linux e Debian. Como posso ajudar voce hoje?",
    "Oi! Estou aqui para ajudar com questoes sobre Linux, Debian e tecnologia em geral. Em que posso ser util?",
    "Ola! Pronto para responder suas perguntas sobre sistemas Linux. O que voce gostaria de saber?"
]


async def classify_intent(query: str) -> IntentClassification:
    """
    Classificacao hibrida:
    1. ML Classifier (treinado) decide primeiro
    2. LLM valida apenas casos duvidosos
    """
    global classifier_pipeline
    
    query_lower = query.lower()
    
    # =========================================================
    # REGRA RAPIDA: Saudacoes curtas = GREETING
    # =========================================================
    if len(query.split()) <= 4:
        if any(kw in query_lower for kw in GREETING_KEYWORDS):
            logger.info(f"[INTENT] '{query}' -> GREETING (quick rule)")
            return IntentClassification(intent="GREETING", confidence=0.95)
    
    # =========================================================
    # ML CLASSIFIER (modelo treinado)
    # =========================================================
    ml_prediction = None
    ml_confidence = 0.0
    
    if classifier_pipeline is not None:
        try:
            ml_prediction = classifier_pipeline.predict([query])[0]
            if hasattr(classifier_pipeline.named_steps['classifier'], 'predict_proba'):
                probabilities = classifier_pipeline.predict_proba([query])[0]
                ml_confidence = float(max(probabilities))
            else:
                ml_confidence = 0.80
            
            logger.info(f"[ML] '{query}' -> {ml_prediction} (conf={ml_confidence:.2f})")
            
        except Exception as e:
            logger.error(f"[ML] Erro: {e}")
    
    # =========================================================
    # DECISAO: ML confiante? Usa direto. Senao, LLM valida.
    # =========================================================
    
    # NOVO: Detectar palavras de execução + comandos Linux
    execution_words = ["executa", "execute", "roda", "rode", "mostra", "mostre", "pode executar", "consegue executar"]
    linux_commands = ["who", "free", "df", "top", "htop", "ps", "ifconfig", "netstat", "journalctl", "dmesg", "systemctl"]
    
    has_exec_words = any(word in query_lower for word in execution_words)
    has_linux_cmd = any(cmd in query_lower for cmd in linux_commands)
    
    # ML confiante (>= 0.75) MAS check hints primeiro
    if ml_prediction and ml_confidence >= 0.75:
        # Se tem execução + comando Linux, força validação do LLM
        if not (has_exec_words and has_linux_cmd):
            logger.info(f"[INTENT] '{query}' -> {ml_prediction} (ML confiante)")
            return IntentClassification(intent=ml_prediction, confidence=ml_confidence)
        else:
            logger.info(f"[INTENT] ML confiante MAS query tem execução+comando, validando...")
    
    # ML deu CASUAL mas tem palavras tecnicas? LLM valida
    needs_validation = False
    technical_hints = [
        "executa", "execute", "roda", "rode", "mostra", "mostre",
        "verifica", "analisa", "como ta", "como está",
        "memoria", "disco", "rede", "cpu", "log", "processo",
        "servico", "serviço", "uptime", "ip", "porta",
    ]
    
    if ml_prediction == "CASUAL":
        if any(hint in query_lower for hint in technical_hints):
            needs_validation = True
            logger.info(f"[INTENT] ML deu CASUAL mas tem hints tecnicos, validando com LLM...")
    
    # ML incerto (< 0.75) = LLM valida
    if ml_prediction and ml_confidence < 0.75:
        needs_validation = True
        logger.info(f"[INTENT] ML incerto ({ml_confidence:.2f}), validando com LLM...")
    
    # Sem ML = LLM decide
    if ml_prediction is None:
        needs_validation = True
        logger.info(f"[INTENT] Sem ML, usando LLM...")
    
    # =========================================================
    # LLM VALIDA (so quando necessario)
    # =========================================================
    if needs_validation:
        try:
            llm_intent = await _llm_classify_intent(query)
            logger.info(f"[INTENT] '{query}' -> {llm_intent} (LLM validou)")
            return IntentClassification(intent=llm_intent, confidence=0.85)
        except Exception as e:
            logger.error(f"[INTENT] LLM falhou: {type(e).__name__}")
            # Fallback pro ML se LLM falhar
            if ml_prediction:
                logger.info(f"[INTENT] Usando ML como fallback: {ml_prediction}")
                return IntentClassification(intent=ml_prediction, confidence=ml_confidence)
    
    # Se ML teve resultado (mesmo sem validacao), usa ele
    if ml_prediction:
        logger.info(f"[INTENT] '{query}' -> {ml_prediction} (ML direto)")
        return IntentClassification(intent=ml_prediction, confidence=ml_confidence)
    
    # =========================================================
    # FALLBACK: Keywords
    # =========================================================
    tech_matches = sum(1 for kw in TECHNICAL_KEYWORDS if kw in query_lower)
    if tech_matches >= 2:
        logger.info(f"[INTENT] '{query}' -> TECHNICAL (fallback keywords)")
        return IntentClassification(intent="TECHNICAL", confidence=0.7)
    
    logger.info(f"[INTENT] '{query}' -> CASUAL (fallback)")
    return IntentClassification(intent="CASUAL", confidence=0.6)


async def _llm_classify_intent(query: str) -> str:
    """Usa LLM para validar/classificar a intencao."""
    
    prompt = """<|im_start|>system
Classifique a intencao do usuario:

TECHNICAL = Usuario quer executar/ver/verificar algo no sistema, ou ajuda tecnica com Linux
CASUAL = Conversa, agradecimento, feedback, perguntas sobre a IA
GREETING = Apenas saudacao (oi, ola)

Responda APENAS: TECHNICAL, CASUAL ou GREETING
<|im_end|>
<|im_start|>user
{query}
<|im_end|>
<|im_start|>assistant
""".format(query=query)
    
    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            response = await client.post(
                f"{INFERENCE_URL}/internal/classify",
                json={
                    "prompt": prompt,
                    "max_tokens": 10,
                    "temperature": 0.1,
                    "top_p": 0.9
                }
            )
            
            if response.status_code != 200:
                logger.error(f"[LLM_INTENT] Status {response.status_code}: {response.text[:100]}")
                raise Exception(f"LLM retornou {response.status_code}")
            
            result = response.json()
            text = result.get("generated_text", "").strip().upper()
            
            logger.info(f"[LLM_INTENT] Resposta: '{text}'")
            
            if "TECHNICAL" in text:
                return "TECHNICAL"
            elif "GREETING" in text:
                return "GREETING"
            else:
                return "CASUAL"
                
    except httpx.TimeoutException:
        logger.error(f"[LLM_INTENT] Timeout ao classificar")
        raise
    except Exception as e:
        logger.error(f"[LLM_INTENT] Erro: {type(e).__name__}: {e}")
        raise


async def handle_greeting() -> str:
    """Retorna uma resposta de saudacao pre-definida."""
    import random
    return random.choice(GREETING_RESPONSES)


async def handle_casual(query: str) -> str:
    """Gera resposta casual usando o LLM."""
    try:
        prompt = f"""<|im_start|>system
Voce e Lanne, uma assistente amigavel especialista em Linux e Debian.
Responda de forma casual e amigavel em portugues brasileiro.
NUNCA use emojis.
<|im_end|>
<|im_start|>user
{query}
<|im_end|>
<|im_start|>assistant
"""
        
        llm_request = LLMRequest(
            prompt=prompt,
            max_tokens=256,
            temperature=0.5,
            top_p=0.9
        )
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{INFERENCE_URL}/internal/generate",
                json=llm_request.model_dump()
            )
            
            if response.status_code != 200:
                logger.error(f"[CASUAL] LLM retornou {response.status_code}: {response.text[:100]}")
                return "Desculpe, tive um problema ao processar sua mensagem. Pode tentar novamente?"
            
            llm_response = response.json()
        
        text = llm_response["generated_text"].strip()
        return clean_response(text)
        
    except httpx.TimeoutException:
        logger.error(f"[CASUAL] Timeout ao gerar resposta")
        return "Desculpe, demorei muito para processar. Pode tentar novamente?"
    except Exception as e:
        logger.error(f"[CASUAL] Erro: {type(e).__name__}: {e}")
        return "Desculpe, tive um problema ao processar sua mensagem. Pode tentar novamente?"


# =============================================================================
# ENDPOINTS
# =============================================================================

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "service": "orchestrator-service",
        "status": "running",
        "version": "3.0.0",
        "features": ["qwen2.5_prompts", "no_emojis", "response_cleaning", "llm_agent_routing"]
    }


@app.post("/reload-keywords")
async def reload_keywords():
    """Recarrega keywords do dataset sem reiniciar o servico"""
    global TECHNICAL_KEYWORDS, GREETING_KEYWORDS, dataset_rules
    
    try:
        import json
        with open(DATASET_PATH, 'r', encoding='utf-8') as f:
            dataset = json.load(f)
        
        TECHNICAL_KEYWORDS.clear()
        GREETING_KEYWORDS.clear()
        
        for category, words in dataset['keywords']['TECHNICAL'].items():
            TECHNICAL_KEYWORDS.extend(words)
        for category, words in dataset['keywords']['GREETING'].items():
            GREETING_KEYWORDS.extend(words)
        
        dataset_rules = dataset.get('rules', {})
        
        logger.info(f"[OK] Keywords recarregadas: {len(TECHNICAL_KEYWORDS)} technical, {len(GREETING_KEYWORDS)} greeting")
        
        return {
            "status": "success",
            "technical_keywords": len(TECHNICAL_KEYWORDS),
            "greeting_keywords": len(GREETING_KEYWORDS),
            "dataset_version": dataset.get('version', 'unknown')
        }
    except Exception as e:
        logger.error(f"[ERRO] Erro ao recarregar keywords: {e}")
        raise HTTPException(status_code=500, detail=f"Erro ao recarregar: {str(e)}")



# =============================================================================
# STREAMING GENERATOR
# =============================================================================

async def orchestrate_stream(query_text: str) -> AsyncGenerator[str, None]:
    """Generator de streaming NDJSON"""
    def mk_event(event_type: str, data: dict) -> str:
        return json.dumps({"type": event_type, **data}) + "\n"
    
    try:
        yield mk_event("status", {"msg": "Analisando intencao..."})
        await asyncio.sleep(0.01)
        
        classification = await classify_intent(query_text)
        
        if classification.intent == "GREETING":
            response_text = await handle_greeting()
            yield mk_event("final_response", {
                "data": {
                    "response": response_text,
                    "intent": "GREETING",
                    "sources": [],
                    "metadata": {}
                }
            })
            return
        
        elif classification.intent == "CASUAL":
            yield mk_event("status", {"msg": "Processando conversa..."})
            await asyncio.sleep(0.01)
            
            response_text = await handle_casual(query_text)
            yield mk_event("final_response", {
                "data": {
                    "response": response_text,
                    "intent": "CASUAL",
                    "sources": [],
                    "metadata": {}
                }
            })
            return
        
        elif classification.intent == "TECHNICAL":
            # Pipeline TECHNICAL com status detalhado
            yield mk_event("status", {"msg": "Coletando dados do sistema..."})
            await asyncio.sleep(0.01)
            
            # Executar pipeline inline para dar yield em cada etapa
            try:
                request_type = detect_request_type(query_text)
                
                # Etapa 1: Agent
                agent_logs = await collect_agent_logs(query_text)
                has_agent_data = agent_logs is not None
                
                # Etapa 2: RAG
                yield mk_event("status", {"msg": "Buscando na base de conhecimento..."})
                await asyncio.sleep(0.01)
                
                rag_request = RAGSearchRequest(query=query_text, top_k=3, threshold=0.0)
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.post(f"{RAG_URL}/internal/search", json=rag_request.model_dump())
                    resp.raise_for_status()
                    rag_response = resp.json()
                
                max_similarity = rag_response.get("max_similarity", 0.0)
                documents = rag_response.get("documents", [])
                
                context_parts = []
                sources = []
                used_web = False
                
                if agent_logs:
                    context_parts.append(agent_logs)
                    sources.append("linux-agent")
                
                if max_similarity >= CONFIDENCE_THRESHOLD:
                    rag_context = "\n\n".join([doc["text"][:500] for doc in documents])
                    context_parts.append(f"[BASE DE CONHECIMENTO]\n{rag_context}")
                    sources.extend([doc.get("metadata", {}).get("source", "internal") for doc in documents])
                else:
                    # Etapa 3: Web fallback
                    yield mk_event("status", {"msg": "Buscando na web..."})
                    await asyncio.sleep(0.01)
                    
                    web_query = f"Linux Debian {query_text}"
                    web_request = WebSearchRequest(query=web_query, max_results=3)
                    
                    async with httpx.AsyncClient(timeout=15.0) as client:
                        resp = await client.post(f"{WEB_SEARCH_URL}/internal/web_search", json=web_request.model_dump())
                        resp.raise_for_status()
                        web_response = resp.json()
                    
                    web_results = web_response.get("results", [])
                    if web_results:
                        web_context = "\n\n".join([
                            f"- {r.get('title', 'Sem titulo')}\n{r.get('snippet', '')[:300]}"
                            for r in web_results
                        ])
                        context_parts.append(f"[PESQUISA WEB]\n{web_context}")
                        sources.extend([r.get("url", "") for r in web_results])
                        used_web = True
                
                context = "\n\n".join(context_parts)
                
                # Etapa 4: LLM
                yield mk_event("status", {"msg": "Gerando resposta..."})
                await asyncio.sleep(0.01)
                
                if request_type == "EXECUTE":
                    prompt = build_execution_prompt(query_text, context, has_agent_data)
                elif request_type == "TUTORIAL":
                    prompt = build_tutorial_prompt(query_text, context)
                else:
                    prompt = build_mixed_prompt(query_text, context, has_agent_data)
                
                llm_request = LLMRequest(prompt=prompt, max_tokens=400, temperature=0.3, top_p=0.85)
                
                async with httpx.AsyncClient(timeout=60.0) as client:
                    resp = await client.post(f"{INFERENCE_URL}/internal/generate", json=llm_request.model_dump())
                    resp.raise_for_status()
                    llm_response = resp.json()
                
                generated_text = llm_response["generated_text"].strip()
                cleaned_text = clean_response(generated_text)
                
                if len(cleaned_text) < 20:
                    cleaned_text = "Desculpe, nao consegui gerar uma resposta adequada. Pode reformular sua pergunta?"
                
                yield mk_event("final_response", {
                    "data": {
                        "response": cleaned_text,
                        "intent": "TECHNICAL",
                        "sources": sources,
                        "metadata": {
                            "rag_similarity": max_similarity,
                            "used_web_fallback": used_web,
                            "used_agent": has_agent_data,
                            "request_type": request_type
                        }
                    }
                })
                
            except Exception as e:
                logger.error(f"[STREAM_TECHNICAL] Erro: {e}")
                yield mk_event("error", {"msg": str(e)})
        
    except Exception as e:
        logger.error(f"[STREAM] Erro: {e}")
        yield mk_event("error", {"msg": str(e)})


@app.post("/internal/orchestrate")
async def orchestrate(query: ChatQuery):
    """
    Endpoint principal de orquestracao (STREAMING NDJSON)
    """
    logger.info(f"[ORCH] Query: {query.text[:50]}...")
    return StreamingResponse(
        orchestrate_stream(query.text),
        media_type="application/x-ndjson"
    )


@app.post("/internal/configure-agent")
async def configure_agent(config: dict):
    """
    Endpoint para configurar AGENT_URL dinamicamente
    
    Request:
        {
            "agent_url": "http://172.17.1.1:9000",
            "enabled": true
        }
    
    Response:
        {
            "status": "ok",
            "agent_url": "http://172.17.1.1:9000",
            "enabled": true
        }
    """
    try:
        global AGENT_CONFIG
        
        agent_url = config.get("agent_url")
        enabled = config.get("enabled", True)
        
        if not agent_url:
            raise HTTPException(
                status_code=400,
                detail="Campo 'agent_url' e obrigatorio"
            )
        
        # Atualizar configuração global
        AGENT_CONFIG["url"] = agent_url
        AGENT_CONFIG["enabled"] = enabled
        
        logger.info(f"[CONFIG] Agent URL atualizado: {agent_url} (enabled={enabled})")
        
        return {
            "status": "ok",
            "agent_url": AGENT_CONFIG["url"],
            "enabled": AGENT_CONFIG["enabled"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[CONFIG] Erro ao configurar agent: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Erro ao configurar agent: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)