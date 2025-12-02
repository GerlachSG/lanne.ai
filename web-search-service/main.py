"""
Web Search Service - Integração com Tavily API
Porta: 8004

MELHORIAS APLICADAS:
- Query optimization para Linux/Debian
- Filtro de fontes confiáveis
- Fallback mais inteligente
- Melhor formatação de snippets
"""

from fastapi import FastAPI, HTTPException, status
import httpx
import os
from typing import List, Dict, Any, Optional
import logging
import re

from lanne_schemas import WebSearchRequest, WebSearchResponse

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Inicializar FastAPI
app = FastAPI(
    title="Lanne AI Web Search Service",
    description="Serviço de busca web com Tavily API - Otimizado para Linux/Debian",
    version="1.1.0"
)

# Configuração da API Tavily
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "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")
TAVILY_API_URL = "https://api.tavily.com/search"

# =============================================================================
# MELHORIA: FONTES CONFIÁVEIS PARA LINUX
# =============================================================================

# Domínios prioritários para busca Linux
TRUSTED_DOMAINS = [
    "wiki.debian.org",
    "wiki.archlinux.org", 
    "help.ubuntu.com",
    "manpages.debian.org",
    "linux.die.net",
    "man7.org",
    "tldp.org",
    "linuxize.com",
    "digitalocean.com",
    "linode.com",
    "cyberciti.biz",
    "tecmint.com",
    "howtoforge.com",
    "baeldung.com",
    "stackoverflow.com",
    "unix.stackexchange.com",
    "askubuntu.com",
    "serverfault.com",
    "kernel.org",
    "gnu.org",
    "freedesktop.org",
]

# Domínios a evitar (baixa qualidade ou irrelevantes)
BLOCKED_DOMAINS = [
    "pinterest.com",
    "facebook.com",
    "twitter.com",
    "instagram.com",
    "tiktok.com",
    "youtube.com",  # Vídeos não são úteis para texto
    "reddit.com",   # Pode ter info desatualizada
]


def optimize_query_for_linux(query: str) -> str:
    """
    Otimiza a query para buscar documentação Linux de qualidade.
    """
    query_lower = query.lower()
    
    # Remover palavras muito genéricas
    filler_words = ["como", "fazer", "eu", "posso", "pra", "para", "mim", "me", "o", "a", "de", "do", "da"]
    words = query.split()
    filtered_words = [w for w in words if w.lower() not in filler_words]
    
    # Adicionar contexto Linux se não presente
    linux_terms = ["linux", "debian", "ubuntu", "comando", "terminal", "bash", "shell"]
    has_linux_context = any(term in query_lower for term in linux_terms)
    
    optimized = " ".join(filtered_words)
    
    if not has_linux_context:
        # Adicionar "Linux" ou "Debian" baseado no conteúdo
        if any(term in query_lower for term in ["apt", "dpkg", ".deb", "systemd"]):
            optimized = f"Debian {optimized}"
        else:
            optimized = f"Linux {optimized}"
    
    # Adicionar termos de qualidade para comandos
    command_indicators = ["comando", "executar", "rodar", "instalar", "configurar"]
    if any(ind in query_lower for ind in command_indicators):
        optimized = f"{optimized} command line tutorial"
    
    logger.info(f"🔍 Query otimizada: '{query}' → '{optimized}'")
    return optimized


def score_result(result: Dict, query: str) -> float:
    """
    Pontua um resultado baseado em qualidade e relevância.
    """
    score = result.get("score", 0.5)
    url = result.get("url", "").lower()
    title = result.get("title", "").lower()
    snippet = result.get("content", result.get("snippet", "")).lower()
    
    # Boost para domínios confiáveis
    for domain in TRUSTED_DOMAINS:
        if domain in url:
            score += 0.2
            break
    
    # Penalizar domínios bloqueados
    for domain in BLOCKED_DOMAINS:
        if domain in url:
            score -= 0.5
            break
    
    # Boost para conteúdo relevante
    relevance_terms = ["debian", "ubuntu", "linux", "command", "terminal", "bash"]
    for term in relevance_terms:
        if term in snippet or term in title:
            score += 0.05
    
    # Boost para páginas de documentação oficial
    if any(doc in url for doc in ["wiki", "manual", "docs", "documentation", "man"]):
        score += 0.15
    
    return min(score, 1.0)  # Cap at 1.0


def clean_snippet(snippet: str, max_length: int = 400) -> str:
    """
    Limpa e formata o snippet para melhor legibilidade.
    """
    if not snippet:
        return ""
    
    # Remover múltiplos espaços/newlines
    snippet = re.sub(r'\s+', ' ', snippet).strip()
    
    # Remover caracteres especiais problemáticos
    snippet = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', snippet)
    
    # Truncar de forma inteligente (não cortar palavras)
    if len(snippet) > max_length:
        snippet = snippet[:max_length].rsplit(' ', 1)[0] + "..."
    
    return snippet


@app.get("/")
async def root():
    """Health check endpoint"""
    api_key_configured = len(TAVILY_API_KEY) > 0
    return {
        "service": "web-search-service",
        "status": "running",
        "tavily_api_configured": api_key_configured,
        "version": "1.1.0",
        "improvements": ["query_optimization", "trusted_sources", "better_scoring"]
    }


@app.post("/internal/web_search", response_model=WebSearchResponse)
async def web_search(request: WebSearchRequest):
    """
    Busca web usando Tavily API
    MELHORADO: Query optimization e scoring de resultados
    """
    
    if not TAVILY_API_KEY:
        logger.warning("Tavily API key not configured, returning mock results")
        return _get_mock_results(request.query, request.max_results)
    
    try:
        # Otimizar query
        optimized_query = optimize_query_for_linux(request.query)
        
        logger.info(f"Web search request: {request.query} → {optimized_query}")
        
        # Preparar payload para Tavily
        payload = {
            "api_key": TAVILY_API_KEY,
            "query": optimized_query,
            "search_depth": "advanced",  # Usar advanced para melhor qualidade
            "include_answer": True,
            "include_raw_content": False,
            "max_results": request.max_results + 3,  # Pegar mais para filtrar depois
            "include_domains": TRUSTED_DOMAINS[:10],  # Top 10 domínios confiáveis
            "exclude_domains": BLOCKED_DOMAINS,
        }
        
        # Fazer requisição à API Tavily
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                TAVILY_API_URL,
                json=payload
            )
            response.raise_for_status()
            data = response.json()
        
        # Processar e pontuar resultados
        results = []
        for result in data.get("results", []):
            scored_result = {
                "title": result.get("title", ""),
                "url": result.get("url", ""),
                "snippet": clean_snippet(result.get("content", "")),
                "score": score_result(result, request.query)
            }
            results.append(scored_result)
        
        # Ordenar por score e pegar top N
        results.sort(key=lambda x: x["score"], reverse=True)
        results = results[:request.max_results]
        
        # Adicionar resposta direta do Tavily se disponível (alta qualidade)
        if "answer" in data and data["answer"]:
            direct_answer = {
                "title": "📌 Resposta Direta",
                "url": "",
                "snippet": clean_snippet(data["answer"], 500),
                "score": 1.0
            }
            results.insert(0, direct_answer)
        
        logger.info(f"Web search returned {len(results)} results (after scoring)")
        
        return WebSearchResponse(
            results=results,
            total_found=len(results)
        )
        
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error from Tavily API: {e}")
        # Tentar busca simplificada como fallback
        return await _fallback_search(request.query, request.max_results)
        
    except httpx.RequestError as e:
        logger.error(f"Connection error to Tavily API: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Tavily API unavailable"
        )
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


async def _fallback_search(query: str, max_results: int) -> WebSearchResponse:
    """
    Busca simplificada caso a busca principal falhe.
    """
    try:
        payload = {
            "api_key": TAVILY_API_KEY,
            "query": query,
            "search_depth": "basic",
            "include_answer": False,
            "max_results": max_results
        }
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(TAVILY_API_URL, json=payload)
            response.raise_for_status()
            data = response.json()
        
        results = []
        for result in data.get("results", []):
            results.append({
                "title": result.get("title", ""),
                "url": result.get("url", ""),
                "snippet": clean_snippet(result.get("content", "")),
                "score": result.get("score", 0.5)
            })
        
        return WebSearchResponse(results=results, total_found=len(results))
        
    except Exception as e:
        logger.error(f"Fallback search also failed: {e}")
        return _get_mock_results(query, max_results)


def _get_mock_results(query: str, max_results: int) -> WebSearchResponse:
    """
    Retorna resultados mock quando a API Tavily não está configurada.
    """
    mock_results = [
        {
            "title": f"Documentação Linux para: {query}",
            "url": "https://wiki.debian.org/",
            "snippet": f"Para '{query}', consulte a documentação oficial do Debian. A API de busca web não está configurada. Configure TAVILY_API_KEY para habilitar buscas reais.",
            "score": 0.5
        },
        {
            "title": "Como obter API Key Tavily",
            "url": "https://tavily.com",
            "snippet": "Visite tavily.com para obter uma API key gratuita. A Tavily oferece busca otimizada para IA/RAG com snippets limpos.",
            "score": 0.4
        }
    ]
    
    return WebSearchResponse(
        results=mock_results[:max_results],
        total_found=len(mock_results[:max_results])
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8004)