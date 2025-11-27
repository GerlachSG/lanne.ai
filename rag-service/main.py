"""
RAG Service - Serviço de Retrieval-Augmented Generation
Porta: 8003
Responsabilidades:
- Gerenciar índice vetorial FAISS
- Endpoint /internal/search para busca por similaridade
- Endpoint /internal/add_document para ingestão de documentos
- Pipeline de chunking e embedding
"""

from fastapi import FastAPI, HTTPException, status, UploadFile, File
import faiss
import numpy as np
import pickle
from pathlib import Path
from typing import List, Dict, Any, Optional
import logging
import hashlib
from sentence_transformers import SentenceTransformer

from lanne_schemas import (
    RAGSearchRequest,
    RAGSearchResponse,
    RAGDocument,
    RAGAddDocumentRequest
)

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Inicializar FastAPI
app = FastAPI(
    title="Lanne AI RAG Service",
    description="Serviço de busca vetorial com FAISS",
    version="1.0.0"
)

# Configuração de paths
DATA_DIR = Path(__file__).parent / "data"
FAISS_INDEX_PATH = DATA_DIR / "faiss_index.bin"
METADATA_PATH = DATA_DIR / "metadata.pkl"


class RAGService:
    """
    Serviço de gerenciamento do índice FAISS
    """
    
    def __init__(self):
        self.index: Optional[faiss.Index] = None
        self.metadata: List[Dict[str, Any]] = []
        self.dimension = 384  # Dimension padrão para embeddings
        self.embedding_model = None
        
    def load_or_create_index(self):
        """
        Carrega índice FAISS existente ou cria um novo
        """
        try:
            # Criar diretório se não existir
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            
            # Carregar modelo de embeddings
            logger.info("Loading embedding model (sentence-transformers)...")
            self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
            logger.info("Embedding model loaded")
            
            if FAISS_INDEX_PATH.exists() and METADATA_PATH.exists():
                # Carregar índice existente
                logger.info("Loading existing FAISS index")
                self.index = faiss.read_index(str(FAISS_INDEX_PATH))
                
                with open(METADATA_PATH, 'rb') as f:
                    self.metadata = pickle.load(f)
                
                logger.info(f"Loaded index with {self.index.ntotal} vectors")
            else:
                # Criar novo índice
                logger.info("Creating new FAISS index")
                self.index = faiss.IndexFlatL2(self.dimension)
                self.metadata = []
                self.save_index()
                logger.info("New FAISS index created")
                
        except Exception as e:
            logger.error(f"Error loading/creating index: {e}")
            raise
    
    def save_index(self):
        """
        Salva índice FAISS e metadados em disco
        """
        try:
            faiss.write_index(self.index, str(FAISS_INDEX_PATH))
            
            with open(METADATA_PATH, 'wb') as f:
                pickle.dump(self.metadata, f)
            
            logger.info(f"Index saved with {self.index.ntotal} vectors")
            
        except Exception as e:
            logger.error(f"Error saving index: {e}")
            raise
    
    def get_embedding(self, text: str) -> np.ndarray:
        """
        Gera embedding para um texto usando sentence-transformers
        """
        if self.embedding_model is None:
            raise RuntimeError("Embedding model not loaded")
        
        # Gerar embedding
        embedding = self.embedding_model.encode(text, convert_to_numpy=True)
        return embedding.astype('float32')
    
    def search(
        self,
        query: str,
        top_k: int = 5,
        threshold: float = 0.0
    ) -> RAGSearchResponse:
        """
        Busca por similaridade no índice FAISS
        """
        if self.index is None or self.index.ntotal == 0:
            logger.warning("Index is empty")
            return RAGSearchResponse(
                documents=[],
                total_found=0,
                max_similarity=0.0
            )
        
        try:
            # Gerar embedding da query
            query_embedding = self.get_embedding(query)
            query_embedding = query_embedding.reshape(1, -1)
            
            # Buscar k vizinhos mais próximos
            k = min(top_k, self.index.ntotal)
            distances, indices = self.index.search(query_embedding, k)
            
            # Converter distâncias L2 para scores de similaridade [0, 1]
            # Score = 1 / (1 + distance)
            similarities = 1.0 / (1.0 + distances[0])
            
            # Filtrar por threshold
            documents = []
            for i, (idx, similarity) in enumerate(zip(indices[0], similarities)):
                if similarity >= threshold and idx < len(self.metadata):
                    doc = RAGDocument(
                        text=self.metadata[idx]["text"],
                        metadata=self.metadata[idx].get("metadata", {}),
                        similarity_score=float(similarity)
                    )
                    documents.append(doc)
            
            max_similarity = float(similarities[0]) if len(similarities) > 0 else 0.0
            
            logger.info(f"Search returned {len(documents)} documents (max similarity: {max_similarity:.4f})")
            
            return RAGSearchResponse(
                documents=documents,
                total_found=len(documents),
                max_similarity=max_similarity
            )
            
        except Exception as e:
            logger.error(f"Error during search: {e}")
            raise
    
    def add_document(
        self,
        text: str,
        metadata: Dict[str, Any] = None,
        chunk_size: int = 512
    ):
        """
        Adiciona documento ao índice
        Divide em chunks e gera embeddings
        """
        try:
            if metadata is None:
                metadata = {}
            
            # Dividir texto em chunks
            chunks = self._chunk_text(text, chunk_size)
            logger.info(f"Document divided into {len(chunks)} chunks")
            
            # Gerar embeddings e adicionar ao índice
            for i, chunk in enumerate(chunks):
                embedding = self.get_embedding(chunk)
                embedding = embedding.reshape(1, -1)
                
                # Adicionar ao índice
                self.index.add(embedding)
                
                # Adicionar metadados
                chunk_metadata = metadata.copy()
                chunk_metadata["chunk_index"] = i
                chunk_metadata["total_chunks"] = len(chunks)
                
                self.metadata.append({
                    "text": chunk,
                    "metadata": chunk_metadata
                })
            
            # Salvar índice atualizado
            self.save_index()
            
            logger.info(f"Added {len(chunks)} chunks to index")
            
        except Exception as e:
            logger.error(f"Error adding document: {e}")
            raise
    
    def _chunk_text(self, text: str, chunk_size: int) -> List[str]:
        """
        Divide texto em chunks de tamanho aproximado
        """
        words = text.split()
        chunks = []
        current_chunk = []
        current_length = 0
        
        for word in words:
            current_chunk.append(word)
            current_length += len(word) + 1
            
            if current_length >= chunk_size:
                chunks.append(' '.join(current_chunk))
                current_chunk = []
                current_length = 0
        
        # Adicionar último chunk se houver
        if current_chunk:
            chunks.append(' '.join(current_chunk))
        
        return chunks if chunks else [text]


# Instância global do serviço
rag_service = RAGService()


@app.on_event("startup")
async def startup_event():
    """
    Carregar ou criar índice FAISS na inicialização
    """
    logger.info("Starting RAG Service...")
    try:
        rag_service.load_or_create_index()
        logger.info("RAG Service ready")
    except Exception as e:
        logger.error(f"Failed to start service: {e}")
        raise


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "service": "rag-service",
        "status": "running",
        "index_size": rag_service.index.ntotal if rag_service.index else 0,
        "version": "1.0.0"
    }


@app.post("/internal/search", response_model=RAGSearchResponse)
async def search(request: RAGSearchRequest):
    """
    Busca por similaridade vetorial no índice FAISS
    """
    try:
        logger.info(f"Search request: {request.query[:50]}...")
        
        response = rag_service.search(
            query=request.query,
            top_k=request.top_k,
            threshold=request.threshold
        )
        
        return response
        
    except Exception as e:
        logger.error(f"Error in search: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@app.post("/internal/add_document")
async def add_document(request: RAGAddDocumentRequest):
    """
    Adiciona documento ao índice FAISS
    """
    try:
        logger.info(f"Adding document (length: {len(request.text)} chars)")
        
        rag_service.add_document(
            text=request.text,
            metadata=request.metadata,
            chunk_size=request.chunk_size
        )
        
        return {
            "status": "success",
            "message": "Document added to index",
            "index_size": rag_service.index.ntotal
        }
        
    except Exception as e:
        logger.error(f"Error adding document: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)