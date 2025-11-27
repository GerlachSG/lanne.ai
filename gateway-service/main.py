"""
Gateway Service - Ponto de entrada público da arquitetura Lanne AI
Porta: 8000
Responsabilidades:
- Roteamento de requisições para serviços internos
- Validação de entrada com Pydantic
- Autenticação OAuth2 e rate limiting
- Proxy reverso para microsserviços
"""

from fastapi import FastAPI, HTTPException, Depends, status, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
import httpx
from typing import Optional, List
import logging

from lanne_schemas import ChatQuery, ChatResponse, RAGAddDocumentRequest

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Inicializar FastAPI
app = FastAPI(
    title="Lanne AI Gateway Service",
    description="API Gateway para o sistema Lanne AI",
    version="1.0.0"
)

# Configurar encoding UTF-8 para respostas
@app.middleware("http")
async def add_charset(request, call_next):
    response = await call_next(request)
    response.headers["Content-Type"] = "application/json; charset=utf-8"
    return response

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Em produção, especificar domínios
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# OAuth2 (placeholder - implementar autenticação real)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token", auto_error=False)

# URLs dos serviços internos
ORCHESTRATOR_URL = "http://localhost:8001"
RAG_SERVICE_URL = "http://localhost:8003"
METRICS_SERVICE_URL = "http://localhost:8005"


async def get_current_user(token: Optional[str] = Depends(oauth2_scheme)):
    """
    Validação de token OAuth2
    TODO: Implementar autenticação real com JWT
    """
    # Por enquanto, aceita qualquer token ou None
    return {"user_id": "default_user"}


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "service": "gateway-service",
        "status": "running",
        "version": "1.0.0"
    }


@app.post("/api/v1/chat", response_model=ChatResponse)
async def chat(
    query: ChatQuery,
    current_user: dict = Depends(get_current_user)
):
    """
    Endpoint principal de chat
    Usa Agente Autônomo ReAct (LLM raciocina e decide tudo)
    """
    try:
        logger.info(f"Chat request from user {current_user['user_id']}: {query.text[:50]}...")
        
        # Encaminhar para o agente autônomo
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{ORCHESTRATOR_URL}/agent",
                json=query.model_dump()
            )
            response.raise_for_status()
            
        logger.info(f"Chat response sent successfully")
        return response.json()
        
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error from orchestrator: {e}")
        raise HTTPException(
            status_code=e.response.status_code,
            detail=f"Error from orchestrator service: {str(e)}"
        )
    except httpx.RequestError as e:
        logger.error(f"Connection error to orchestrator: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Orchestrator service unavailable"
        )
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@app.post("/api/v1/upload_rag")
async def upload_rag(
    files: List[UploadFile] = File(...),
    current_user: dict = Depends(get_current_user)
):
    """
    Endpoint para upload de documentos ao índice FAISS
    Aceita múltiplos arquivos de texto (.txt, .md)
    """
    try:
        results = []
        
        for file in files:
            # Validar tipo de arquivo
            if not file.filename.endswith(('.txt', '.md')):
                logger.warning(f"Skipping unsupported file: {file.filename}")
                continue
            
            # Ler conteúdo
            content = await file.read()
            text = content.decode('utf-8')
            
            # Preparar requisição para rag-service
            rag_request = RAGAddDocumentRequest(
                text=text,
                metadata={
                    "filename": file.filename,
                    "uploaded_by": current_user["user_id"]
                },
                chunk_size=512
            )
            
            # Enviar para rag-service
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{RAG_SERVICE_URL}/internal/add_document",
                    json=rag_request.model_dump()
                )
                response.raise_for_status()
                
            results.append({
                "filename": file.filename,
                "status": "success",
                "size": len(text)
            })
            
            logger.info(f"Document uploaded: {file.filename}")
        
        return {
            "status": "completed",
            "files_processed": len(results),
            "results": results
        }
        
    except Exception as e:
        logger.error(f"Error uploading documents: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@app.get("/api/v1/metrics")
async def get_metrics(
    current_user: dict = Depends(get_current_user)
):
    """
    Endpoint para acesso a métricas do sistema
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{METRICS_SERVICE_URL}/internal/read_syslog")
            response.raise_for_status()
            return response.json()
    except Exception as e:
        logger.error(f"Error fetching metrics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not fetch metrics"
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)