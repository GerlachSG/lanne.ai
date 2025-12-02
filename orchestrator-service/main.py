"""
Orchestrator Service - Cerebro do sistema Lanne AI
Porta: 8001

VERSAO 4.0 - ARQUITETURA ReAct (Reason + Act)
=============================================
O LLM raciocina e decide dinamicamente o que fazer:
1. Planner: Analisa query e cria plano de execucao
2. Executor: Executa apenas o que o plano pede
3. Avaliador: Verifica se precisa de mais dados
4. Gerador: Cria resposta final com contexto coletado

BENEFICIOS:
- Sem desperdicio de recursos (RAG/WEB so quando necessario)
- Decisoes inteligentes baseadas em raciocinio
- Flexivel e extensivel
- Facil de debugar (plano explicito)
"""

from fastapi import FastAPI, HTTPException, status
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import httpx
from typing import Optional, AsyncGenerator, List, Dict, Any
from dataclasses import dataclass, field
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
    description="Servico de orquestracao com arquitetura ReAct",
    version="4.0.0"
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configurar encoding UTF-8
@app.middleware("http")
async def add_charset(request, call_next):
    response = await call_next(request)
    if "application/json" in response.headers.get("Content-Type", ""):
        response.headers["Content-Type"] = "application/json; charset=utf-8"
    return response


# =============================================================================
# CONFIGURACOES
# =============================================================================

INFERENCE_URL = "http://127.0.0.1:8002"
RAG_URL = "http://127.0.0.1:8003"
WEB_SEARCH_URL = "http://127.0.0.1:8004"

AGENT_CONFIG = {
    "url": "http://localhost:9000",
    "enabled": True
}

# Carregar ML classifier e dataset de keywords
CLASSIFIER_PATH = Path(__file__).parent / "intent_classifier.joblib"
DATASET_PATH = Path(__file__).parent / "intent_dataset.json"
classifier_pipeline = None
TECHNICAL_KEYWORDS = []
GREETING_KEYWORDS = []

@app.on_event("startup")
async def load_classifier():
    """Carrega modelo ML e dataset de keywords."""
    global classifier_pipeline, TECHNICAL_KEYWORDS, GREETING_KEYWORDS
    
    # Carregar keywords do dataset
    try:
        with open(DATASET_PATH, 'r', encoding='utf-8') as f:
            dataset = json.load(f)
        
        for category, words in dataset.get('keywords', {}).get('TECHNICAL', {}).items():
            TECHNICAL_KEYWORDS.extend(words)
        for category, words in dataset.get('keywords', {}).get('GREETING', {}).items():
            GREETING_KEYWORDS.extend(words)
        
        logger.info(f"[OK] Dataset carregado: {len(TECHNICAL_KEYWORDS)} technical, {len(GREETING_KEYWORDS)} greeting keywords")
    except Exception as e:
        logger.warning(f"[AVISO] Dataset nao carregado: {e}")
    
    # Carregar ML classifier
    try:
        classifier_pipeline = joblib.load(CLASSIFIER_PATH)
        logger.info(f"[OK] ML classifier carregado")
    except Exception as e:
        logger.warning(f"[AVISO] ML classifier nao disponivel: {e}")


# =============================================================================
# COMANDOS DO AGENT
# =============================================================================

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


# =============================================================================
# ESTRUTURA DO PLANO DE EXECUCAO
# =============================================================================

@dataclass
class ExecutionPlan:
    """Plano de execucao decidido pelo LLM"""
    intent: str  # GREETING, CASUAL, TECHNICAL
    use_agent: bool = False
    agent_commands: List[str] = field(default_factory=list)
    use_rag: bool = False
    use_web: bool = False
    response_style: str = "CHAT"  # CHAT, ANALYZE, TUTORIAL
    reasoning: str = ""  # Raciocinio do LLM
    
    def to_dict(self) -> dict:
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
    """Contexto coletado durante execucao"""
    agent_data: Optional[str] = None
    rag_data: Optional[str] = None
    rag_similarity: float = 0.0
    web_data: Optional[str] = None
    sources: List[str] = field(default_factory=list)
    
    def has_data(self) -> bool:
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


# =============================================================================
# PROMPTS DO SISTEMA ReAct
# =============================================================================

SYSTEM_PROMPT = """Voce e Lanne, uma assistente tecnica especializada em Linux e Debian.

REGRAS OBRIGATORIAS:
1. Responda APENAS em portugues brasileiro
2. NUNCA use emojis ou emoticons
3. Seja objetiva e concisa (maximo 4 paragrafos)
4. Use crases para destacar comandos: `comando`
5. Quando analisar dados do sistema, foque nos problemas encontrados"""


def build_planner_prompt(query: str) -> str:
    """
    Prompt para o LLM decidir QUAIS RECURSOS usar para uma query TECHNICAL.
    A intencao ja foi classificada como TECHNICAL pelo ML classifier.
    """
    commands_list = ", ".join(AGENT_COMMANDS.keys())
    
    prompt = f"""<|im_start|>system
Decida quais recursos usar para responder sobre Linux.

COMANDOS DISPONIVEIS: {commands_list}

REGRAS OBRIGATORIAS:
1. Se a pergunta pede informacao do sistema ATUAL (meu, minha, atual, agora) -> use_agent:true
2. Se a pergunta menciona IP, rede, interface, memoria, disco, cpu, usuarios -> use_agent:true
3. Se a pergunta pede executar/rodar/verificar/mostrar algo do sistema -> use_agent:true
4. Se e tutorial/como fazer/instalacao -> use_rag:true, use_agent:false
5. Problema + sistema (disco cheio, lento, erro) -> use_agent:true E use_rag:true

EXEMPLOS (siga este padrao EXATAMENTE):

Pergunta: "quem esta logado"
Resposta: {{"use_agent":true,"agent_commands":["logged_users"],"use_rag":false,"use_web":false,"response_style":"ANALYZE"}}

Pergunta: "qual o uso de memoria"
Resposta: {{"use_agent":true,"agent_commands":["memory_detailed"],"use_rag":false,"use_web":false,"response_style":"ANALYZE"}}

Pergunta: "qual meu IP"
Resposta: {{"use_agent":true,"agent_commands":["network_info"],"use_rag":false,"use_web":false,"response_style":"ANALYZE"}}

Pergunta: "mostre as informacoes de rede"
Resposta: {{"use_agent":true,"agent_commands":["network_info"],"use_rag":false,"use_web":false,"response_style":"ANALYZE"}}

Pergunta: "execute ip addr show"
Resposta: {{"use_agent":true,"agent_commands":["network_info"],"use_rag":false,"use_web":false,"response_style":"ANALYZE"}}

Pergunta: "como instalar docker"
Resposta: {{"use_agent":false,"agent_commands":[],"use_rag":true,"use_web":false,"response_style":"TUTORIAL"}}

Pergunta: "disco cheio o que faco"
Resposta: {{"use_agent":true,"agent_commands":["disk_usage"],"use_rag":true,"use_web":false,"response_style":"ANALYZE"}}

Resposta SOMENTE JSON em uma linha, sem texto adicional.
<|im_end|>
<|im_start|>user
{query}
<|im_end|>
<|im_start|>assistant
"""
    prompt += '{"use_agent":'
    return prompt


def build_evaluator_prompt(query: str, agent_data: str) -> str:
    """
    Prompt para avaliar se os dados coletados sao suficientes.
    """
    return f"""<|im_start|>system
Voce e um avaliador de contexto. Analise os dados coletados e decida se precisa de mais informacao.

RESPONDA APENAS com JSON:
{{
  "sufficient": true|false,
  "need_rag": true|false,
  "need_web": true|false,
  "reason": "explicacao curta"
}}

REGRAS:
- Se os dados respondem a pergunta completamente -> sufficient=true
- Se precisa de documentacao/tutorial para complementar -> need_rag=true
- Se precisa de informacao externa/atualizada -> need_web=true
- Na duvida, prefira sufficient=true (evitar buscas desnecessarias)
<|im_end|>
<|im_start|>user
PERGUNTA: {query}

DADOS COLETADOS:
{agent_data[:2000]}

Os dados acima sao suficientes para responder a pergunta?
<|im_end|>
<|im_start|>assistant
"""


def build_response_prompt(query: str, context: str, style: str) -> str:
    """
    Prompt para gerar a resposta final.
    """
    style_instructions = {
        "CHAT": "Responda de forma casual e amigavel.",
        "ANALYZE": "Analise os dados coletados. Foque em: o que encontrou, problemas/alertas, e recomendacoes.",
        "TUTORIAL": "De instrucoes claras e praticas. Use no maximo 3-4 comandos principais."
    }
    
    instruction = style_instructions.get(style, style_instructions["CHAT"])
    
    if context:
        return f"""<|im_start|>system
{SYSTEM_PROMPT}

{instruction}
<|im_end|>
<|im_start|>user
{query}

CONTEXTO DISPONIVEL:
{context[:3000]}
<|im_end|>
<|im_start|>assistant
"""
    else:
        return f"""<|im_start|>system
{SYSTEM_PROMPT}

{instruction}
<|im_end|>
<|im_start|>user
{query}
<|im_end|>
<|im_start|>assistant
"""


# =============================================================================
# FUNCOES DE EXECUCAO
# =============================================================================

async def call_llm(prompt: str, max_tokens: int = 768, temperature: float = 0.3) -> str:
    """Chama o servico de inferencia LLM."""
    try:
        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.post(
                f"{INFERENCE_URL}/internal/generate",
                json={
                    "prompt": prompt,
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                    "top_p": 0.9
                }
            )
            response.raise_for_status()
            result = response.json()
            return result.get("generated_text", "").strip()
    except Exception as e:
        logger.error(f"[LLM] Erro: {e}")
        raise


async def call_llm_classify(prompt: str, max_tokens: int = 100) -> str:
    """Chama LLM para classificacao (temperatura baixa)."""
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                f"{INFERENCE_URL}/internal/classify",
                json={
                    "prompt": prompt,
                    "max_tokens": max_tokens,
                    "temperature": 0.1,
                    "top_p": 0.9
                }
            )
            response.raise_for_status()
            result = response.json()
            return result.get("generated_text", "").strip()
    except Exception as e:
        logger.error(f"[LLM_CLASSIFY] Erro: {e}")
        raise


def parse_json_response(text: str) -> dict:
    """
    Extrai JSON da resposta do LLM.
    Robusto contra malformacoes comuns do Qwen2.5.
    """
    if not text:
        return {}
    
    # Limpar o texto
    cleaned = text.strip()
    
    # =========================================================
    # NORMALIZACAO DE CARACTERES CYRILICOS (Qwen2.5 bug)
    # =========================================================
    cyrillic_map = {
        'а': 'a', 'е': 'e', 'о': 'o', 'р': 'p', 'с': 'c', 'у': 'y', 'х': 'x',
        'А': 'A', 'Е': 'E', 'О': 'O', 'Р': 'P', 'С': 'C', 'У': 'Y', 'Х': 'X',
        'В': 'B', 'К': 'K', 'М': 'M', 'Н': 'H', 'Т': 'T',
        'і': 'i', 'І': 'I',  # Ucraniano
    }
    for cyrillic, latin in cyrillic_map.items():
        cleaned = cleaned.replace(cyrillic, latin)
    
    # Cortar texto apos o ultimo } (remover lixo depois do JSON)
    last_brace = cleaned.rfind('}')
    if last_brace != -1:
        cleaned = cleaned[:last_brace + 1]
    
    # Remover escapes estranhos que o modelo adiciona
    cleaned = cleaned.replace('\\"', '"')
    cleaned = cleaned.replace("\\'", "'")
    
    # Corrigir chaves malformadas comuns: "use_rag true":"true" -> "use_rag":true
    cleaned = re.sub(r'"(\w+)\s+true"\s*:\s*"?true"?', r'"\1":true', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'"(\w+)\s+false"\s*:\s*"?false"?', r'"\1":false', cleaned, flags=re.IGNORECASE)
    
    # Remover parenteses nas chaves: "(intent)" -> "intent"
    cleaned = re.sub(r'"\((\w+)\)"', r'"\1"', cleaned)
    
    # Corrigir valores booleanos com case errado ou como string
    cleaned = re.sub(r':\s*"true"', ': true', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r':\s*"false"', ': false', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r':\s*True\b', ': true', cleaned)
    cleaned = re.sub(r':\s*False\b', ': false', cleaned)
    
    # Normalizar valores de intent em portugues
    cleaned = re.sub(r'"TECHNICO"', '"TECHNICAL"', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'"TECNICO"', '"TECHNICAL"', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'"SAUDACAO"', '"GREETING"', cleaned, flags=re.IGNORECASE)
    
    # Normalizar response_style em portugues
    cleaned = re.sub(r'"ANALISE"', '"ANALYZE"', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'"ANALISAR"', '"ANALYZE"', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'"CONVERSA"', '"CHAT"', cleaned, flags=re.IGNORECASE)
    
    # Tentar encontrar JSON completo primeiro
    json_match = re.search(r'\{.*\}', cleaned, re.DOTALL)
    if json_match:
        json_str = json_match.group()
        
        # Tentar parsear direto
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            pass
        
        # Se falhou, tentar consertar JSON truncado
        # Contar chaves e colchetes
        open_braces = json_str.count('{')
        close_braces = json_str.count('}')
        open_brackets = json_str.count('[')
        close_brackets = json_str.count(']')
        
        # Adicionar fechamentos faltando
        json_str += ']' * (open_brackets - close_brackets)
        json_str += '}' * (open_braces - close_braces)
        
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            pass
    
    # Fallback: extrair campos manualmente com regex
    result = {}
    
    # intent
    intent_match = re.search(r'"intent"\s*:\s*"(\w+)"', cleaned, re.IGNORECASE)
    if intent_match:
        intent = intent_match.group(1).upper()
        # Normalizar variações
        if intent in ["GREETING", "SAUDACAO"]:
            result["intent"] = "GREETING"
        elif intent in ["CASUAL"]:
            result["intent"] = "CASUAL"
        elif intent in ["TECHNICAL", "TECHNICO", "TECNICO"]:
            result["intent"] = "TECHNICAL"
        else:
            result["intent"] = "TECHNICAL"  # default
    
    # use_agent
    agent_match = re.search(r'"use_agent"\s*:\s*"?(true|false)"?', cleaned, re.IGNORECASE)
    if agent_match:
        result["use_agent"] = agent_match.group(1).lower() == "true"
    
    # agent_commands
    commands_match = re.search(r'"agent_commands"\s*:\s*\[(.*?)\]', cleaned, re.DOTALL)
    if commands_match:
        commands_str = commands_match.group(1)
        commands = re.findall(r'"(\w+)"', commands_str)
        result["agent_commands"] = [c for c in commands if c in AGENT_COMMANDS]
    
    # use_rag
    rag_match = re.search(r'"use_rag"\s*:\s*"?(true|false)"?', cleaned, re.IGNORECASE)
    if rag_match:
        result["use_rag"] = rag_match.group(1).lower() == "true"
    
    # use_web
    web_match = re.search(r'"use_web"\s*:\s*"?(true|false)"?', cleaned, re.IGNORECASE)
    if web_match:
        result["use_web"] = web_match.group(1).lower() == "true"
    
    # response_style
    style_match = re.search(r'"response_style"\s*:\s*"(\w+)"', cleaned, re.IGNORECASE)
    if style_match:
        style = style_match.group(1).upper()
        if style in ["CHAT", "CONVERSA"]:
            result["response_style"] = "CHAT"
        elif style in ["ANALYZE", "ANALISE", "ANALISAR"]:
            result["response_style"] = "ANALYZE"
        elif style in ["TUTORIAL"]:
            result["response_style"] = "TUTORIAL"
    
    # reasoning
    reason_match = re.search(r'"reasoning"\s*:\s*"([^"]*)"', cleaned)
    if reason_match:
        result["reasoning"] = reason_match.group(1)
    
    if result:
        logger.info(f"[PARSER] Extraido: {result}")
    return result


async def execute_agent_commands(commands: List[str]) -> Optional[str]:
    """Executa comandos no agent Linux."""
    if not AGENT_CONFIG["enabled"]:
        logger.warning("[AGENT] Desabilitado")
        return None
    
    if not commands:
        return None
    
    agent_url = AGENT_CONFIG["url"]
    outputs = []
    
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            for cmd in commands[:3]:  # Maximo 3 comandos
                if cmd not in AGENT_COMMANDS:
                    logger.warning(f"[AGENT] Comando invalido ignorado: {cmd}")
                    continue
                
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
        logger.error(f"[AGENT] Erro: {e}")
        return None
    
    if not outputs:
        return None
    
    # Formatar resultado
    parts = ["[DADOS DO SISTEMA]", "=" * 50]
    for cmd, output in outputs:
        parts.append(f"\n>> {cmd.upper()}: {AGENT_COMMANDS[cmd]}")
        parts.append("-" * 40)
        parts.append(output)
    parts.append("\n" + "=" * 50)
    
    return "\n".join(parts)


async def search_rag(query: str) -> tuple[Optional[str], float]:
    """Busca na base de conhecimento RAG."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{RAG_URL}/internal/search",
                json={"query": query, "top_k": 3, "threshold": 0.0}
            )
            response.raise_for_status()
            result = response.json()
        
        documents = result.get("documents", [])
        max_sim = result.get("max_similarity", 0.0)
        
        if documents and max_sim > 0.5:
            rag_text = "\n\n".join([doc["text"][:500] for doc in documents])
            return rag_text, max_sim
        
        return None, max_sim
        
    except Exception as e:
        logger.error(f"[RAG] Erro: {e}")
        return None, 0.0


async def search_web(query: str) -> Optional[str]:
    """Busca na web."""
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                f"{WEB_SEARCH_URL}/internal/web_search",
                json={"query": f"Linux Debian {query}", "max_results": 3}
            )
            response.raise_for_status()
            result = response.json()
        
        results = result.get("results", [])
        if results:
            web_text = "\n\n".join([
                f"- {r.get('title', 'Sem titulo')}\n{r.get('snippet', '')[:300]}"
                for r in results
            ])
            return web_text
        
        return None
        
    except Exception as e:
        logger.error(f"[WEB] Erro: {e}")
        return None


# =============================================================================
# CLASSIFICACAO DE INTENCAO (ML + LLM)
# =============================================================================

async def classify_intent(query: str) -> str:
    """
    Classificacao hibrida de intencao:
    1. ML Classifier decide primeiro (rapido)
    2. LLM valida casos duvidosos (confianca baixa)
    
    Retorna: "GREETING", "CASUAL" ou "TECHNICAL"
    """
    global classifier_pipeline, GREETING_KEYWORDS, TECHNICAL_KEYWORDS
    
    query_lower = query.lower().strip()
    
    # =========================================================
    # REGRA RAPIDA: Saudacoes curtas = GREETING
    # =========================================================
    greetings = ["oi", "ola", "olá", "bom dia", "boa tarde", "boa noite", 
                 "e ai", "eai", "hey", "opa", "fala", "salve"]
    
    # Query curta que começa com saudação
    if len(query.split()) <= 4:
        for g in greetings:
            if query_lower == g or query_lower.startswith(g + " ") or query_lower.startswith(g + ","):
                logger.info(f"[INTENT] '{query}' -> GREETING (regra rapida)")
                return "GREETING"
    
    # =========================================================
    # REGRA RAPIDA: Casual (agradecimentos, despedidas)
    # =========================================================
    casual_patterns = ["obrigado", "valeu", "brigado", "vlw", "tchau", "ate mais", 
                       "até mais", "falou", "tmj", "quem e voce", "quem é você",
                       "o que voce faz", "o que você faz", "o que voce sabe"]
    
    if any(p in query_lower for p in casual_patterns):
        logger.info(f"[INTENT] '{query}' -> CASUAL (regra rapida)")
        return "CASUAL"
    
    # =========================================================
    # ML CLASSIFIER
    # =========================================================
    ml_prediction = None
    ml_confidence = 0.0
    
    if classifier_pipeline is not None:
        try:
            ml_prediction = classifier_pipeline.predict([query])[0]
            if hasattr(classifier_pipeline.named_steps.get('classifier', {}), 'predict_proba'):
                probabilities = classifier_pipeline.predict_proba([query])[0]
                ml_confidence = float(max(probabilities))
            else:
                ml_confidence = 0.80
            
            logger.info(f"[INTENT] ML: '{query[:30]}' -> {ml_prediction} (conf={ml_confidence:.2f})")
            
        except Exception as e:
            logger.error(f"[INTENT] ML erro: {e}")
    
    # =========================================================
    # DECISAO
    # =========================================================
    
    # Palavras que indicam problema tecnico (CHECAR ANTES do ML)
    technical_hints = ["memoria", "memória", "disco", "cpu", "rede", "ip", "processo",
                       "servico", "serviço", "log", "usuario", "usuário", "uptime",
                       "comando", "instalar", "configurar", "executar", "rodar",
                       "travando", "lento", "erro", "falha", "problema", "nao funciona",
                       "não funciona", "parou", "quebrou", "crashou", "tela preta",
                       "boot", "iniciar", "desligar", "reiniciar", "atualizar",
                       "computador", "sistema", "linux", "debian", "ubuntu", "terminal",
                       "interface", "ram", "swap", "particao", "partição", "porta",
                       "conexao", "conexão", "pacote", "apt", "dpkg", "ssh"]
    
    has_tech_hints = any(h in query_lower for h in technical_hints)
    
    # REGRA PRIORITARIA: Se tem palavras tecnicas -> TECHNICAL (mesmo se ML discordar)
    if has_tech_hints:
        logger.info(f"[INTENT] Hints tecnicos detectados -> TECHNICAL (override ML)")
        return "TECHNICAL"
    
    # ML confiante (>= 0.75) E sem hints tecnicos -> usa direto
    if ml_prediction and ml_confidence >= 0.75:
        logger.info(f"[INTENT] Final: {ml_prediction} (ML confiante, sem hints tecnicos)")
        return ml_prediction
    
    # =========================================================
    # VALIDACAO VIA LLM (confianca baixa 0.40-0.75)
    # =========================================================
    if ml_prediction and 0.40 <= ml_confidence < 0.75:
        logger.info(f"[INTENT] Confianca baixa ({ml_confidence:.2f}), validando com LLM...")
        
        llm_intent = await validate_intent_with_llm(query)
        
        if llm_intent:
            logger.info(f"[INTENT] LLM confirmou: {llm_intent}")
            return llm_intent
        else:
            # LLM falhou, usa ML mesmo
            logger.info(f"[INTENT] LLM falhou, usando ML: {ml_prediction}")
            return ml_prediction
    
    # ML tem resultado -> usa
    if ml_prediction:
        logger.info(f"[INTENT] Final: {ml_prediction} (ML)")
        return ml_prediction
    
    # =========================================================
    # FALLBACK: Keywords
    # =========================================================
    tech_matches = sum(1 for kw in TECHNICAL_KEYWORDS if kw in query_lower)
    greeting_matches = sum(1 for kw in GREETING_KEYWORDS if kw in query_lower)
    
    if greeting_matches > tech_matches and greeting_matches > 0:
        logger.info(f"[INTENT] Final: GREETING (keywords)")
        return "GREETING"
    
    if tech_matches >= 1:
        logger.info(f"[INTENT] Final: TECHNICAL (keywords)")
        return "TECHNICAL"
    
    # Default: validar com LLM antes de assumir CASUAL
    logger.info(f"[INTENT] Sem classificacao clara, validando com LLM...")
    llm_intent = await validate_intent_with_llm(query)
    if llm_intent:
        logger.info(f"[INTENT] Final: {llm_intent} (LLM fallback)")
        return llm_intent
    
    logger.info(f"[INTENT] Final: CASUAL (default)")
    return "CASUAL"


async def validate_intent_with_llm(query: str) -> Optional[str]:
    """
    Usa o LLM para confirmar a intencao quando ML tem baixa confianca.
    Retorna: "GREETING", "CASUAL", "TECHNICAL" ou None se falhar
    """
    prompt = f"""<|im_start|>system
Classifique a intencao do usuario em UMA das categorias:

- GREETING: saudacoes, cumprimentos (oi, ola, bom dia)
- CASUAL: conversa casual, perguntas sobre voce, agradecimentos
- TECHNICAL: qualquer coisa sobre Linux, computador, sistema, erros, problemas tecnicos, comandos, instalacao, configuracao

Responda APENAS com a palavra: GREETING, CASUAL ou TECHNICAL
<|im_end|>
<|im_start|>user
{query}
<|im_end|>
<|im_start|>assistant
"""
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{INFERENCE_URL}/internal/classify",
                json={
                    "prompt": prompt,
                    "max_tokens": 10,
                    "temperature": 0.1
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                # Tentar diferentes campos que o LLM pode retornar
                result = (
                    data.get("classification") or 
                    data.get("generated_text") or 
                    data.get("text") or 
                    data.get("response") or 
                    ""
                ).upper().strip()
                
                logger.info(f"[INTENT] LLM response raw: {result[:50]}")
                
                # Extrair apenas a primeira palavra valida
                for word in result.split():
                    word_clean = word.strip(".,!?\"':-")
                    if word_clean in ["GREETING", "CASUAL", "TECHNICAL"]:
                        return word_clean
                
                # Tentar encontrar no texto
                if "TECHNICAL" in result:
                    return "TECHNICAL"
                if "CASUAL" in result:
                    return "CASUAL"
                if "GREETING" in result:
                    return "GREETING"
                
                logger.warning(f"[INTENT] LLM nao retornou intent valido: {result}")
                    
    except Exception as e:
        logger.error(f"[INTENT] LLM validation error: {e}")
    
    return None


# =============================================================================
# LIMPEZA DE RESPOSTA
# =============================================================================

def clean_response(text: str) -> str:
    """Limpa a resposta do LLM."""
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
    
    # Remover tokens ChatML
    text = re.sub(r'<\|im_start\|>.*?<\|im_end\|>', '', text, flags=re.DOTALL)
    text = re.sub(r'<\|im_start\|>', '', text)
    text = re.sub(r'<\|im_end\|>', '', text)
    text = re.sub(r'<\|endoftext\|>', '', text)
    
    # Remover tokens Mistral
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
# ORCHESTRADOR ReAct
# =============================================================================

class ReactOrchestrator:
    """
    Orquestrador com arquitetura ReAct.
    
    FLUXO:
    1. classify_intent() - ML + regras decide GREETING/CASUAL/TECHNICAL
    2. Se GREETING/CASUAL -> resposta direta
    3. Se TECHNICAL -> LLM planner decide agent_commands, use_rag, etc.
    """
    
    async def create_plan(self, query: str) -> ExecutionPlan:
        """
        ETAPA 1: Classificar intencao e criar plano de execucao.
        
        - GREETING/CASUAL: plano simples, sem LLM planner
        - TECHNICAL: LLM planner decide os recursos
        """
        logger.info(f"[REACT] Criando plano para: {query[:50]}...")
        
        # PASSO 1: Classificar intencao (ML + regras)
        intent = await classify_intent(query)
        
        # PASSO 2: Se nao e TECHNICAL, retorna plano simples
        if intent == "GREETING":
            logger.info(f"[REACT] Plano: GREETING (sem planner LLM)")
            return ExecutionPlan(intent="GREETING", response_style="CHAT")
        
        if intent == "CASUAL":
            logger.info(f"[REACT] Plano: CASUAL (sem planner LLM)")
            return ExecutionPlan(intent="CASUAL", response_style="CHAT")
        
        # PASSO 3: TECHNICAL - chamar LLM planner para decidir recursos
        logger.info(f"[REACT] Intent=TECHNICAL, chamando planner LLM...")
        
        prompt = build_planner_prompt(query)
        
        try:
            response = await call_llm_classify(prompt, max_tokens=150)
            
            # O prompt já começa com '{"use_agent":', então precisamos completar
            full_json = '{"use_agent":' + response
            
            logger.info(f"[REACT] Planner respondeu: {full_json[:200]}")
            
            plan_dict = parse_json_response(full_json)
            
            if not plan_dict:
                logger.warning("[REACT] Falha ao parsear plano, usando fallback")
                return self._fallback_plan(query)
            
            # Validar comandos do agent
            valid_commands = [
                cmd for cmd in plan_dict.get("agent_commands", [])
                if cmd in AGENT_COMMANDS
            ]
            
            # Determinar response_style
            style = plan_dict.get("response_style", "")
            if style not in ["ANALYZE", "TUTORIAL", "CHAT"]:
                style = "ANALYZE" if plan_dict.get("use_agent") else "TUTORIAL"
            
            # VALIDACAO: Se TECHNICAL mas nao pediu nada, algo deu errado
            use_agent = plan_dict.get("use_agent", False)
            use_rag = plan_dict.get("use_rag", False)
            use_web = plan_dict.get("use_web", False)
            
            if not use_agent and not use_rag and not use_web:
                logger.warning("[REACT] Plano vazio para TECHNICAL, usando fallback")
                return self._fallback_plan(query)
            
            # Forcar intent=TECHNICAL (ja classificamos acima)
            plan = ExecutionPlan(
                intent="TECHNICAL",
                use_agent=use_agent,
                agent_commands=valid_commands,
                use_rag=use_rag,
                use_web=use_web,
                response_style=style,
                reasoning=plan_dict.get("reasoning", "")
            )
            
            logger.info(f"[REACT] Plano criado: {plan.to_dict()}")
            return plan
            
        except Exception as e:
            logger.error(f"[REACT] Erro ao criar plano: {e}")
            return self._fallback_plan(query)
    
    def _fallback_plan(self, query: str) -> ExecutionPlan:
        """
        Plano fallback SIMPLES quando LLM falha.
        
        FILOSOFIA ReAct: O fallback NAO deve tentar ser inteligente.
        Se o LLM Planner falhou, usamos RAG e deixamos o LLM decidir
        na geracao da resposta final.
        """
        logger.info(f"[FALLBACK] LLM Planner falhou, usando RAG como fallback ReAct")
        
        # Fallback simples: apenas RAG (respeita ReAct)
        return ExecutionPlan(
            intent="TECHNICAL",
            use_agent=False,
            agent_commands=[],
            use_rag=True,
            use_web=False,
            response_style="TUTORIAL",
            reasoning="Fallback: default RAG"
        )
    
    async def execute_plan(self, plan: ExecutionPlan, query: str) -> ExecutionContext:
        """
        ETAPA 2: Executa apenas o que o plano pede.
        """
        context = ExecutionContext()
        
        # Executar agent se necessario
        if plan.use_agent and plan.agent_commands:
            logger.info(f"[REACT] Executando agent: {plan.agent_commands}")
            context.agent_data = await execute_agent_commands(plan.agent_commands)
            if context.agent_data:
                context.sources.append("linux-agent")
        
        # Buscar RAG se necessario
        if plan.use_rag:
            logger.info("[REACT] Buscando no RAG...")
            rag_data, rag_sim = await search_rag(query)
            context.rag_data = rag_data
            context.rag_similarity = rag_sim
            if rag_data:
                context.sources.append("knowledge-base")
        
        # Buscar web se necessario
        if plan.use_web:
            logger.info("[REACT] Buscando na web...")
            context.web_data = await search_web(query)
            if context.web_data:
                context.sources.append("web-search")
        
        return context
    
    async def evaluate_context(self, query: str, context: ExecutionContext, plan: ExecutionPlan) -> ExecutionContext:
        """
        ETAPA 3: Avalia se precisa de mais dados.
        So executa se coletou dados do agent.
        """
        # Se nao coletou dados do agent, nao precisa avaliar
        if not context.agent_data:
            return context
        
        # Se ja tem RAG ou WEB, nao precisa avaliar
        if context.rag_data or context.web_data:
            return context
        
        logger.info("[REACT] Avaliando se precisa de mais dados...")
        
        try:
            prompt = build_evaluator_prompt(query, context.agent_data)
            response = await call_llm_classify(prompt, max_tokens=100)
            
            eval_dict = parse_json_response(response)
            logger.info(f"[REACT] Avaliacao: {eval_dict}")
            
            if not eval_dict.get("sufficient", True):
                # Precisa de mais dados
                if eval_dict.get("need_rag") and not context.rag_data:
                    logger.info("[REACT] Avaliador pediu RAG, buscando...")
                    rag_data, rag_sim = await search_rag(query)
                    context.rag_data = rag_data
                    context.rag_similarity = rag_sim
                    if rag_data:
                        context.sources.append("knowledge-base")
                
                if eval_dict.get("need_web") and not context.web_data:
                    logger.info("[REACT] Avaliador pediu WEB, buscando...")
                    context.web_data = await search_web(query)
                    if context.web_data:
                        context.sources.append("web-search")
        
        except Exception as e:
            logger.warning(f"[REACT] Erro na avaliacao (ignorando): {e}")
        
        return context
    
    async def generate_response(self, query: str, context: ExecutionContext, plan: ExecutionPlan) -> str:
        """
        ETAPA 4: Gera resposta final.
        """
        logger.info(f"[REACT] Gerando resposta (style={plan.response_style})...")
        
        # Respostas rapidas para GREETING
        if plan.intent == "GREETING":
            greetings = [
                "Ola! Sou Lanne, sua assistente especialista em Linux e Debian. Como posso ajudar?",
                "Oi! Estou aqui para ajudar com Linux e Debian. O que voce precisa?",
                "Ola! Pronto para responder suas perguntas sobre Linux."
            ]
            import random
            return random.choice(greetings)
        
        # Gerar resposta com LLM
        context_text = context.build_context()
        prompt = build_response_prompt(query, context_text, plan.response_style)
        
        try:
            response = await call_llm(prompt, max_tokens=600, temperature=0.3)
            return clean_response(response)
        except Exception as e:
            logger.error(f"[REACT] Erro ao gerar resposta: {e}")
            return "Desculpe, tive um problema ao processar sua pergunta. Pode tentar novamente?"
    
    async def process(self, query: str) -> ChatResponse:
        """
        Pipeline completo ReAct.
        """
        # Etapa 1: Criar plano
        plan = await self.create_plan(query)
        
        # Etapa 2: Executar plano
        context = await self.execute_plan(plan, query)
        
        # Etapa 3: Avaliar e complementar se necessario
        context = await self.evaluate_context(query, context, plan)
        
        # Etapa 4: Gerar resposta
        response_text = await self.generate_response(query, context, plan)
        
        # Validar resposta
        if len(response_text) < 20:
            response_text = "Desculpe, nao consegui gerar uma resposta adequada. Pode reformular?"
        
        return ChatResponse(
            response=response_text,
            intent=plan.intent,
            sources=context.sources,
            metadata={
                "plan": plan.to_dict(),
                "rag_similarity": context.rag_similarity,
                "used_agent": context.agent_data is not None,
                "used_rag": context.rag_data is not None,
                "used_web": context.web_data is not None,
            }
        )


# Instancia global do orquestrador
orchestrator = ReactOrchestrator()


# =============================================================================
# STREAMING
# =============================================================================

async def orchestrate_stream(query_text: str) -> AsyncGenerator[str, None]:
    """Generator de streaming NDJSON com ReAct."""
    
    def mk_event(event_type: str, data: dict) -> str:
        return json.dumps({"type": event_type, **data}, ensure_ascii=False) + "\n"
    
    try:
        # Etapa 1: Criar plano
        yield mk_event("status", {"msg": "Analisando sua pergunta..."})
        await asyncio.sleep(0.01)
        
        plan = await orchestrator.create_plan(query_text)
        
        yield mk_event("plan", {"data": plan.to_dict()})
        await asyncio.sleep(0.01)
        
        # Resposta rapida para GREETING
        if plan.intent == "GREETING":
            response = await orchestrator.generate_response(query_text, ExecutionContext(), plan)
            yield mk_event("final_response", {
                "data": {
                    "response": response,
                    "intent": "GREETING",
                    "sources": [],
                    "metadata": {"plan": plan.to_dict()}
                }
            })
            return
        
        # Resposta para CASUAL (sem recursos)
        if plan.intent == "CASUAL":
            yield mk_event("status", {"msg": "Processando..."})
            await asyncio.sleep(0.01)
            
            response = await orchestrator.generate_response(query_text, ExecutionContext(), plan)
            yield mk_event("final_response", {
                "data": {
                    "response": response,
                    "intent": "CASUAL",
                    "sources": [],
                    "metadata": {"plan": plan.to_dict()}
                }
            })
            return
        
        # TECHNICAL - executar plano
        context = ExecutionContext()
        
        # Agent
        if plan.use_agent and plan.agent_commands:
            yield mk_event("status", {"msg": f"Coletando dados: {', '.join(plan.agent_commands)}..."})
            await asyncio.sleep(0.01)
            
            context.agent_data = await execute_agent_commands(plan.agent_commands)
            if context.agent_data:
                context.sources.append("linux-agent")
        
        # RAG
        if plan.use_rag:
            yield mk_event("status", {"msg": "Buscando na base de conhecimento..."})
            await asyncio.sleep(0.01)
            
            rag_data, rag_sim = await search_rag(query_text)
            context.rag_data = rag_data
            context.rag_similarity = rag_sim
            if rag_data:
                context.sources.append("knowledge-base")
        
        # WEB
        if plan.use_web:
            yield mk_event("status", {"msg": "Buscando na web..."})
            await asyncio.sleep(0.01)
            
            context.web_data = await search_web(query_text)
            if context.web_data:
                context.sources.append("web-search")
        
        # Avaliar se precisa de mais (so se coletou agent e nao tem rag/web)
        if context.agent_data and not context.rag_data and not context.web_data:
            yield mk_event("status", {"msg": "Avaliando dados..."})
            await asyncio.sleep(0.01)
            
            context = await orchestrator.evaluate_context(query_text, context, plan)
        
        # Gerar resposta
        yield mk_event("status", {"msg": "Gerando resposta..."})
        await asyncio.sleep(0.01)
        
        response = await orchestrator.generate_response(query_text, context, plan)
        
        if len(response) < 20:
            response = "Desculpe, nao consegui gerar uma resposta adequada. Pode reformular?"
        
        yield mk_event("final_response", {
            "data": {
                "response": response,
                "intent": plan.intent,
                "sources": context.sources,
                "metadata": {
                    "plan": plan.to_dict(),
                    "rag_similarity": context.rag_similarity,
                    "used_agent": context.agent_data is not None,
                    "used_rag": context.rag_data is not None,
                    "used_web": context.web_data is not None,
                }
            }
        })
        
    except Exception as e:
        logger.error(f"[STREAM] Erro: {e}", exc_info=True)
        yield mk_event("error", {"msg": str(e)})


# =============================================================================
# ENDPOINTS
# =============================================================================

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "service": "orchestrator-service",
        "status": "running",
        "version": "4.0.0",
        "architecture": "ReAct",
        "features": [
            "llm_planner",
            "conditional_execution",
            "context_evaluation",
            "no_wasted_resources"
        ]
    }


@app.post("/internal/orchestrate")
async def orchestrate(query: ChatQuery):
    """
    Endpoint principal de orquestracao (STREAMING NDJSON)
    Usa arquitetura ReAct para decisoes inteligentes.
    """
    logger.info(f"[ORCH] Query: {query.text[:50]}...")
    return StreamingResponse(
        orchestrate_stream(query.text),
        media_type="application/x-ndjson"
    )


@app.post("/internal/orchestrate-sync")
async def orchestrate_sync(query: ChatQuery):
    """
    Endpoint sincrono (sem streaming) para testes.
    """
    logger.info(f"[ORCH_SYNC] Query: {query.text[:50]}...")
    result = await orchestrator.process(query.text)
    return result


@app.post("/internal/configure-agent")
async def configure_agent(config: dict):
    """Configura URL do agent dinamicamente."""
    try:
        global AGENT_CONFIG
        
        agent_url = config.get("agent_url")
        enabled = config.get("enabled", True)
        
        if not agent_url:
            raise HTTPException(status_code=400, detail="Campo 'agent_url' e obrigatorio")
        
        AGENT_CONFIG["url"] = agent_url
        AGENT_CONFIG["enabled"] = enabled
        
        logger.info(f"[CONFIG] Agent: {agent_url} (enabled={enabled})")
        
        return {
            "status": "ok",
            "agent_url": AGENT_CONFIG["url"],
            "enabled": AGENT_CONFIG["enabled"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[CONFIG] Erro: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/debug/plan")
async def debug_plan(query: str):
    """
    Endpoint de debug - mostra o plano sem executar.
    Util para testar o planner.
    """
    plan = await orchestrator.create_plan(query)
    return plan.to_dict()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)