"""
Lanne AI Shared Schemas
Modelos Pydantic compartilhados entre todos os microsserviços
"""

from .models import (
    ChatQuery,
    ChatResponse,
    LLMRequest,
    LLMResponse,
    RAGSearchRequest,
    RAGSearchResponse,
    RAGDocument,
    RAGAddDocumentRequest,
    WebSearchRequest,
    WebSearchResponse,
    MetricsLog,
    IntentClassification,
    AgentExecuteRequest,
    AgentExecuteResponse,
    OrchestrationContext,
    # Conversation models
    Message,
    Conversation,
    ConversationCreate,
    MessageCreate,
    ConversationSummary,
    ConversationContext,
    ConversationListItem,
)

__all__ = [
    "ChatQuery",
    "ChatResponse",
    "LLMRequest",
    "LLMResponse",
    "RAGSearchRequest",
    "RAGSearchResponse",
    "RAGDocument",
    "RAGAddDocumentRequest",
    "WebSearchRequest",
    "WebSearchResponse",
    "MetricsLog",
    "IntentClassification",
    "AgentExecuteRequest",
    "AgentExecuteResponse",
    "OrchestrationContext",
    "Message",
    "Conversation",
    "ConversationCreate",
    "MessageCreate",
    "ConversationSummary",
    "ConversationContext",
    "ConversationListItem",
]