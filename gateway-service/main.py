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
ORCHESTRATOR_URL = "http://127.0.0.1:8001"
RAG_SERVICE_URL = "http://127.0.0.1:8003"
METRICS_SERVICE_URL = "http://127.0.0.1:8005"
INFERENCE_SERVICE_URL = "http://127.0.0.1:8002"


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
    Encaminha para o Orchestrator que gerencia o pipeline
    """
    try:
        logger.info(f"Chat request from user {current_user['user_id']}: {query.text[:50]}...")
        
        # Encaminhar para o orchestrator (streaming NDJSON)
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{ORCHESTRATOR_URL}/internal/orchestrate",
                json=query.model_dump()
            )
            # Nao levantar excecao aqui; lidamos com fallback amigavel abaixo
            
            # O orchestrator retorna streaming NDJSON
            # Precisamos processar e extrair a resposta final
            lines = (response.text or "").strip().split('\n')
            for line in reversed(lines):
                if line.strip():
                    try:
                        import json
                        data = json.loads(line)
                        if data.get("type") == "final_response":
                            logger.info(f"Chat response sent successfully")
                            return data.get("data", {})
                        elif data.get("type") == "error":
                            # Fallback amigavel quando orchestrator reporta erro
                            logger.warning(f"Orchestrator error: {data.get('msg', '')}")
                            return ChatResponse(
                                response="Erro ao processar mensagem. Verifique se os serviços de IA (inference/rag) estão rodando.",
                                intent="TECHNICAL",
                                sources=[],
                                metadata={"error": data.get("msg", "orchestrator_error"), "fallback": True}
                            )
                    except json.JSONDecodeError:
                        continue
            
            # Se nao veio resposta processavel, verificar status HTTP
            if response.status_code != 200:
                logger.warning(f"Orchestrator HTTP {response.status_code}; tentando fallback direto no inference")
                # Tentar fallback direto no inference-service
                try:
                    from lanne_schemas import LLMRequest
                    llm_req = LLMRequest(
                        prompt=f"<|im_start|>system\nVoce e Lanne, responda em portugues brasileiro de forma objetiva.\n<|im_end|>\n<|im_start|>user\n{query.text}\n<|im_end|>\n<|im_start|>assistant\n",
                        max_tokens=300,
                        temperature=0.4,
                        top_p=0.9
                    )
                    async with httpx.AsyncClient(timeout=20.0) as client2:
                        r2 = await client2.post(f"{INFERENCE_SERVICE_URL}/internal/generate", json=llm_req.model_dump())
                        if r2.status_code == 200:
                            data2 = r2.json()
                            return ChatResponse(
                                response=data2.get("generated_text", ""),
                                intent="TECHNICAL",
                                sources=[],
                                metadata={"fallback": True, "route": "direct_inference"}
                            )
                except Exception as fe:
                    logger.warning(f"Direct inference fallback failed: {fe}")
                # Fallback final
                return ChatResponse(
                    response="Erro ao processar mensagem. Verifique se os serviços de IA (inference/rag) estão rodando.",
                    intent="TECHNICAL",
                    sources=[],
                    metadata={"error": f"http_{response.status_code}", "fallback": True}
                )

            # Sem linhas validas mas status 200: fallback generico
            return ChatResponse(
                response="Não foi possível obter uma resposta da IA no momento.",
                intent="TECHNICAL",
                sources=[],
                metadata={"error": "empty_stream", "fallback": True}
            )
        
    except httpx.RequestError as e:
        # Conexao falhou (orchestrator offline) -> tentar fallback direto no inference
        logger.error(f"Connection error to orchestrator: {e}")
        try:
            from lanne_schemas import LLMRequest
            llm_req = LLMRequest(
                prompt=f"<|im_start|>system\nVoce e Lanne, responda em portugues brasileiro de forma objetiva.\n<|im_end|>\n<|im_start|>user\n{query.text}\n<|im_end|>\n<|im_start|>assistant\n",
                max_tokens=300,
                temperature=0.4,
                top_p=0.9
            )
            async with httpx.AsyncClient(timeout=20.0) as client2:
                r2 = await client2.post(f"{INFERENCE_SERVICE_URL}/internal/generate", json=llm_req.model_dump())
                if r2.status_code == 200:
                    data2 = r2.json()
                    return ChatResponse(
                        response=data2.get("generated_text", ""),
                        intent="TECHNICAL",
                        sources=[],
                        metadata={"fallback": True, "route": "direct_inference"}
                    )
        except Exception as fe:
            logger.warning(f"Direct inference fallback failed: {fe}")
        return ChatResponse(
            response="Serviço de orquestração indisponível. Verifique se o orchestrator está rodando (porta 8001).",
            intent="TECHNICAL",
            sources=[],
            metadata={"error": "orchestrator_unavailable", "fallback": True}
        )
    except Exception as e:
        # Qualquer outro erro -> resposta amigavel
        logger.error(f"Unexpected error: {e}")
        return ChatResponse(
            response="Ocorreu um erro ao processar sua mensagem.",
            intent="TECHNICAL",
            sources=[],
            metadata={"error": str(e), "fallback": True}
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