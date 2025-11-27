"""
Modelos Pydantic para contratos de API entre microsserviços Lanne AI
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


# ==========================================
# Gateway Service Models
# ==========================================

class ChatQuery(BaseModel):
    """Requisição de chat do usuário via Gateway"""
    text: str = Field(..., min_length=1, max_length=2000, description="Texto da consulta do usuário")
    user_id: Optional[str] = Field(None, description="ID do usuário (opcional)")
    session_id: Optional[str] = Field(None, description="ID da sessão de chat")
    
    class Config:
        json_schema_extra = {
            "example": {
                "text": "Como instalar um pacote .deb no Debian?",
                "user_id": "user123",
                "session_id": "session456"
            }
        }


class ChatResponse(BaseModel):
    """Resposta de chat retornada pelo Gateway"""
    response: str = Field(..., description="Resposta gerada pela IA")
    intent: Optional[str] = Field(None, description="Intenção classificada (TECHNICAL, CASUAL, GREETING)")
    sources: Optional[List[str]] = Field(None, description="Fontes usadas (se RAG foi acionado)")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Metadados adicionais")
    
    class Config:
        json_schema_extra = {
            "example": {
                "response": "Para instalar um pacote .deb no Debian, use: sudo dpkg -i arquivo.deb",
                "intent": "TECHNICAL",
                "sources": ["debian_manual.txt"],
                "metadata": {"latency_ms": 1250}
            }
        }


# ==========================================
# Inference Service Models
# ==========================================

class LLMRequest(BaseModel):
    """Requisição para inferência do LLM"""
    prompt: str = Field(..., min_length=1, description="Prompt para o LLM")
    max_tokens: int = Field(default=512, ge=1, le=2048, description="Número máximo de tokens a gerar")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0, description="Temperatura para sampling")
    top_p: float = Field(default=0.9, ge=0.0, le=1.0, description="Top-p para nucleus sampling")
    
    class Config:
        json_schema_extra = {
            "example": {
                "prompt": "Classifique a intenção: 'Como configurar o ufw?'",
                "max_tokens": 50,
                "temperature": 0.1,
                "top_p": 0.9
            }
        }


class LLMResponse(BaseModel):
    """Resposta da inferência do LLM"""
    generated_text: str = Field(..., description="Texto gerado pelo LLM")
    tokens_generated: int = Field(..., description="Número de tokens gerados")
    inference_time_ms: float = Field(..., description="Tempo de inferência em milissegundos")
    
    class Config:
        json_schema_extra = {
            "example": {
                "generated_text": "TECHNICAL",
                "tokens_generated": 5,
                "inference_time_ms": 450.5
            }
        }


# ==========================================
# Orchestrator Service Models
# ==========================================

class IntentClassification(BaseModel):
    """Classificação de intenção"""
    intent: str = Field(..., description="Intenção classificada: TECHNICAL, CASUAL, GREETING")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confiança da classificação")
    
    class Config:
        json_schema_extra = {
            "example": {
                "intent": "TECHNICAL",
                "confidence": 0.95
            }
        }


# ==========================================
# RAG Service Models
# ==========================================

class RAGDocument(BaseModel):
    """Documento retornado pela busca RAG"""
    text: str = Field(..., description="Texto do documento")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadados do documento")
    similarity_score: float = Field(..., ge=0.0, le=1.0, description="Score de similaridade")
    
    class Config:
        json_schema_extra = {
            "example": {
                "text": "O UFW (Uncomplicated Firewall) é uma ferramenta...",
                "metadata": {"source": "debian_security.txt", "page": 5},
                "similarity_score": 0.87
            }
        }


class RAGSearchRequest(BaseModel):
    """Requisição de busca no RAG"""
    query: str = Field(..., min_length=1, description="Query de busca")
    top_k: int = Field(default=5, ge=1, le=20, description="Número de documentos a retornar")
    threshold: float = Field(default=0.0, ge=0.0, le=1.0, description="Score mínimo de similaridade")
    
    class Config:
        json_schema_extra = {
            "example": {
                "query": "como configurar firewall ufw",
                "top_k": 3,
                "threshold": 0.7
            }
        }


class RAGSearchResponse(BaseModel):
    """Resposta da busca no RAG"""
    documents: List[RAGDocument] = Field(..., description="Documentos encontrados")
    total_found: int = Field(..., description="Total de documentos encontrados")
    max_similarity: float = Field(..., ge=0.0, le=1.0, description="Maior score de similaridade")
    
    class Config:
        json_schema_extra = {
            "example": {
                "documents": [],
                "total_found": 3,
                "max_similarity": 0.87
            }
        }


class RAGAddDocumentRequest(BaseModel):
    """Requisição para adicionar documento ao índice FAISS"""
    text: str = Field(..., min_length=1, description="Texto do documento")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadados do documento")
    chunk_size: int = Field(default=512, ge=100, le=2000, description="Tamanho dos chunks")
    
    class Config:
        json_schema_extra = {
            "example": {
                "text": "Manual completo do Debian...",
                "metadata": {"source": "debian_manual.pdf", "author": "Debian Team"},
                "chunk_size": 512
            }
        }


# ==========================================
# Web Search Service Models
# ==========================================

class WebSearchRequest(BaseModel):
    """Requisição de busca web (Tavily API)"""
    query: str = Field(..., min_length=1, description="Query de busca")
    max_results: int = Field(default=5, ge=1, le=10, description="Número máximo de resultados")
    
    class Config:
        json_schema_extra = {
            "example": {
                "query": "linux kernel 6.10 latest news",
                "max_results": 3
            }
        }


class WebSearchResponse(BaseModel):
    """Resposta da busca web"""
    results: List[Dict[str, Any]] = Field(..., description="Resultados da busca web")
    total_found: int = Field(..., description="Total de resultados encontrados")
    
    class Config:
        json_schema_extra = {
            "example": {
                "results": [
                    {
                        "title": "Linux Kernel 6.10 Released",
                        "url": "https://example.com/kernel-6.10",
                        "snippet": "The latest Linux kernel version..."
                    }
                ],
                "total_found": 5
            }
        }


# ==========================================
# Linux Agent Models
# ==========================================

class AgentExecuteRequest(BaseModel):
    """Requisição para executar comando no agent Linux"""
    command: str = Field(..., description="Comando a executar (da whitelist)")
    params: Optional[Dict[str, Any]] = Field(None, description="Parâmetros do comando")
    
    class Config:
        json_schema_extra = {
            "example": {
                "command": "journalctl",
                "params": {"lines": "50"}
            }
        }


class AgentExecuteResponse(BaseModel):
    """Resposta da execução de comando no agent Linux"""
    status: str = Field(..., description="Status da execução")
    command: str = Field(..., description="Comando executado")
    exit_code: int = Field(..., description="Código de saída")
    stdout: str = Field(..., description="Saída padrão")
    stderr: str = Field(..., description="Saída de erro")
    
    class Config:
        json_schema_extra = {
            "example": {
                "status": "success",
                "command": "journalctl",
                "exit_code": 0,
                "stdout": "Nov 05 10:30:00 debian systemd[1]: Started Apache...",
                "stderr": ""
            }
        }


# ==========================================
# Orchestrator Context Models
# ==========================================

class OrchestrationContext(BaseModel):
    """Contexto completo de orquestração de uma query"""
    query: str = Field(..., description="Query original do usuário")
    intent: str = Field(..., description="Intenção classificada")
    intent_confidence: float = Field(..., description="Confiança da classificação")
    rag_documents: Optional[List[RAGDocument]] = Field(None, description="Documentos do RAG local")
    web_results: Optional[List[Dict[str, Any]]] = Field(None, description="Resultados da web")
    agent_logs: Optional[str] = Field(None, description="Logs coletados do agent Linux")
    context_source: str = Field(..., description="Fonte do contexto: 'rag', 'web', 'hybrid', 'agent'")
    
    class Config:
        json_schema_extra = {
            "example": {
                "query": "Apache não está iniciando",
                "intent": "TECHNICAL",
                "intent_confidence": 0.95,
                "rag_documents": [],
                "web_results": None,
                "agent_logs": "systemd[1]: apache2.service: Failed with result 'exit-code'",
                "context_source": "hybrid"
            }
        }


# ==========================================
# Metrics Service Models
# ==========================================

class MetricsLog(BaseModel):
    """Log de métricas do sistema"""
    timestamp: datetime = Field(default_factory=datetime.now, description="Timestamp do log")
    service: str = Field(..., description="Nome do microsserviço")
    endpoint: str = Field(..., description="Endpoint chamado")
    method: str = Field(..., description="Método HTTP")
    status_code: int = Field(..., description="Código de status HTTP")
    latency_ms: float = Field(..., description="Latência em milissegundos")
    payload: Optional[Dict[str, Any]] = Field(None, description="Payload da requisição (opcional)")
    error: Optional[str] = Field(None, description="Mensagem de erro (se houver)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "timestamp": "2025-11-04T10:30:00",
                "service": "inference-service",
                "endpoint": "/internal/generate",
                "method": "POST",
                "status_code": 200,
                "latency_ms": 1250.5,
                "payload": {"prompt": "..."},
                "error": None
            }
        }