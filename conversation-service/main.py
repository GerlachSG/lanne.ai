"""
Conversation Service - Gerenciamento de Conversas para Lanne AI
Porta: 8006
MELHORADO: PATCH para update, geração de título, melhor estrutura
"""

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from datetime import datetime
import uuid
import logging
from pathlib import Path
import json

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Inicializar FastAPI
app = FastAPI(
    title="Lanne AI Conversation Service",
    description="Serviço de gerenciamento de conversas e histórico",
    version="1.1.0"
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Arquivo de persistência
CONVERSATIONS_FILE = Path(__file__).parent / "conversations.json"


# =============================================================================
# MODELOS PYDANTIC
# =============================================================================

class ConversationCreate(BaseModel):
    user_id: str
    title: Optional[str] = "Nova Conversa"
    description: Optional[str] = ""

class ConversationUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None

class MessageCreate(BaseModel):
    role: str = Field(..., pattern="^(user|assistant|system)$")
    content: str

class ConversationResponse(BaseModel):
    id: str
    user_id: str
    title: str
    description: str
    message_count: int
    created_at: str
    updated_at: str

class MessageResponse(BaseModel):
    id: str
    role: str
    content: str
    timestamp: str


# =============================================================================
# ARMAZENAMENTO
# =============================================================================

def load_conversations() -> dict:
    """Carrega conversas do arquivo JSON"""
    if not CONVERSATIONS_FILE.exists():
        return {"conversations": {}}
    
    try:
        with open(CONVERSATIONS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Erro ao carregar conversas: {e}")
        return {"conversations": {}}


def save_conversations(data: dict):
    """Salva conversas no arquivo JSON"""
    try:
        with open(CONVERSATIONS_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Erro ao salvar conversas: {e}")


# =============================================================================
# EVENTOS
# =============================================================================

@app.on_event("startup")
async def startup_event():
    """Inicialização do serviço"""
    logger.info("Conversation Service v1.1.0 iniciado")
    
    if not CONVERSATIONS_FILE.exists():
        save_conversations({"conversations": {}})
        logger.info("Arquivo de conversas criado")


# =============================================================================
# ENDPOINTS - CONVERSAS
# =============================================================================

@app.get("/")
async def root():
    """Health check endpoint"""
    data = load_conversations()
    return {
        "service": "conversation-service",
        "status": "running",
        "version": "1.1.0",
        "total_conversations": len(data.get("conversations", {}))
    }


@app.post("/conversations", response_model=ConversationResponse)
async def create_conversation(conv: ConversationCreate):
    """
    Cria uma nova conversa
    """
    data = load_conversations()
    
    conv_id = str(uuid.uuid4())[:12]
    now = datetime.utcnow().isoformat()
    
    conversation = {
        "id": conv_id,
        "user_id": conv.user_id,
        "title": conv.title or "Nova Conversa",
        "description": conv.description or "",
        "messages": [],
        "created_at": now,
        "updated_at": now
    }
    
    data["conversations"][conv_id] = conversation
    save_conversations(data)
    
    logger.info(f"Conversa '{conv_id}' criada para usuário '{conv.user_id}'")
    
    return ConversationResponse(
        id=conv_id,
        user_id=conv.user_id,
        title=conversation["title"],
        description=conversation["description"],
        message_count=0,
        created_at=now,
        updated_at=now
    )


@app.get("/conversations")
async def list_conversations(user_id: str = None):
    """
    Lista conversas (opcionalmente filtradas por user_id)
    """
    data = load_conversations()
    conversations = data.get("conversations", {})
    
    result = []
    for conv_id, conv in conversations.items():
        # Filtrar por user_id se fornecido
        if user_id and conv.get("user_id") != user_id:
            continue
        
        result.append({
            "id": conv_id,
            "user_id": conv.get("user_id", ""),
            "title": conv.get("title", ""),
            "description": conv.get("description", ""),
            "message_count": len(conv.get("messages", [])),
            "created_at": conv.get("created_at", ""),
            "updated_at": conv.get("updated_at", "")
        })
    
    # Ordenar por updated_at (mais recentes primeiro)
    result.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
    
    return result


@app.get("/conversations/{conversation_id}")
async def get_conversation(conversation_id: str):
    """
    Busca detalhes de uma conversa
    """
    data = load_conversations()
    conversations = data.get("conversations", {})
    
    if conversation_id not in conversations:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversa '{conversation_id}' não encontrada"
        )
    
    conv = conversations[conversation_id]
    
    return {
        "id": conversation_id,
        "user_id": conv.get("user_id", ""),
        "title": conv.get("title", ""),
        "description": conv.get("description", ""),
        "message_count": len(conv.get("messages", [])),
        "created_at": conv.get("created_at", ""),
        "updated_at": conv.get("updated_at", "")
    }


@app.patch("/conversations/{conversation_id}")
async def update_conversation(conversation_id: str, update: ConversationUpdate):
    """
    Atualiza título e/ou descrição de uma conversa
    """
    data = load_conversations()
    conversations = data.get("conversations", {})
    
    if conversation_id not in conversations:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversa '{conversation_id}' não encontrada"
        )
    
    conv = conversations[conversation_id]
    
    if update.title is not None:
        conv["title"] = update.title
    if update.description is not None:
        conv["description"] = update.description
    
    conv["updated_at"] = datetime.utcnow().isoformat()
    
    save_conversations(data)
    
    logger.info(f"Conversa '{conversation_id}' atualizada")
    
    return {
        "id": conversation_id,
        "title": conv["title"],
        "description": conv["description"],
        "updated_at": conv["updated_at"]
    }


@app.delete("/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str):
    """
    Deleta uma conversa
    """
    data = load_conversations()
    conversations = data.get("conversations", {})
    
    if conversation_id not in conversations:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversa '{conversation_id}' não encontrada"
        )
    
    del conversations[conversation_id]
    save_conversations(data)
    
    logger.info(f"Conversa '{conversation_id}' deletada")
    
    return {"message": f"Conversa '{conversation_id}' deletada com sucesso"}


# =============================================================================
# ENDPOINTS - MENSAGENS
# =============================================================================

@app.get("/conversations/{conversation_id}/messages")
async def get_messages(conversation_id: str):
    """
    Lista mensagens de uma conversa
    """
    data = load_conversations()
    conversations = data.get("conversations", {})
    
    if conversation_id not in conversations:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversa '{conversation_id}' não encontrada"
        )
    
    messages = conversations[conversation_id].get("messages", [])
    
    return messages


@app.post("/conversations/{conversation_id}/messages")
async def add_message(conversation_id: str, message: MessageCreate):
    """
    Adiciona uma mensagem a uma conversa
    """
    data = load_conversations()
    conversations = data.get("conversations", {})
    
    if conversation_id not in conversations:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversa '{conversation_id}' não encontrada"
        )
    
    msg_id = str(uuid.uuid4())[:8]
    now = datetime.utcnow().isoformat()
    
    msg = {
        "id": msg_id,
        "role": message.role,
        "content": message.content,
        "timestamp": now
    }
    
    conversations[conversation_id]["messages"].append(msg)
    conversations[conversation_id]["updated_at"] = now
    
    save_conversations(data)
    
    return msg


# =============================================================================
# ENDPOINTS - UTILIDADES
# =============================================================================

@app.post("/conversations/{conversation_id}/generate-title")
async def generate_title_endpoint(conversation_id: str):
    """
    Gera título automaticamente baseado nas mensagens
    (Este endpoint pode chamar o LLM ou usar heurística simples)
    """
    data = load_conversations()
    conversations = data.get("conversations", {})
    
    if conversation_id not in conversations:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversa '{conversation_id}' não encontrada"
        )
    
    conv = conversations[conversation_id]
    messages = conv.get("messages", [])
    
    if len(messages) < 2:
        return {"title": "Nova Conversa", "description": ""}
    
    # Heurística simples: usar primeira mensagem do usuário como título
    user_messages = [m for m in messages if m.get("role") == "user"]
    
    if user_messages:
        first_msg = user_messages[0].get("content", "")[:50]
        title = first_msg + ("..." if len(first_msg) >= 50 else "")
    else:
        title = "Conversa"
    
    # Descrição baseada no contexto
    description = f"Conversa com {len(messages)} mensagens"
    
    # Atualizar conversa
    conv["title"] = title
    conv["description"] = description
    conv["updated_at"] = datetime.utcnow().isoformat()
    
    save_conversations(data)
    
    return {"title": title, "description": description}


@app.get("/stats")
async def get_stats():
    """
    Estatísticas gerais do serviço
    """
    data = load_conversations()
    conversations = data.get("conversations", {})
    
    total_messages = sum(
        len(conv.get("messages", []))
        for conv in conversations.values()
    )
    
    return {
        "total_conversations": len(conversations),
        "total_messages": total_messages,
        "avg_messages_per_conversation": total_messages / max(len(conversations), 1)
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8006)