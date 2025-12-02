"""
Metrics Service - Coleta de logs e métricas (Windows Server -> Linux Agent via HTTP)
Porta: 8005
Responsabilidades:
- Coletar e armazenar logs de todos os microsserviços
- Endpoint /internal/log para registrar métricas
- Endpoint /internal/read_syslog para acesso a logs de sistemas Linux via Lanne Agent
- Análise de performance e diagnóstico
"""

from fastapi import FastAPI, HTTPException, status
from pathlib import Path
import json
import httpx
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

from lanne_schemas import MetricsLog
from pydantic import BaseModel

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Inicializar FastAPI
app = FastAPI(
    title="Lanne AI Metrics Service",
    description="Serviço de coleta de logs e métricas",
    version="1.0.0"
)

# Configuração de paths
METRICS_DIR = Path("data")  # Funciona no Windows
METRICS_FILE = METRICS_DIR / "metrics.jsonl"

# Configuração do Lanne Agent (cliente Linux)
AGENT_CONFIG = {
    "enabled": False,
    "url": "",  # Ex: http://192.168.1.100:9000
    "token": ""  # Token de autenticação
}


class AgentConfig(BaseModel):
    """Schema para configuração do agente"""
    url: str
    token: Optional[str] = None


def init_metrics_storage():
    """
    Inicializa armazenamento de métricas
    """
    METRICS_DIR.mkdir(parents=True, exist_ok=True)
    if not METRICS_FILE.exists():
        METRICS_FILE.touch()


@app.on_event("startup")
async def startup_event():
    """
    Inicializar armazenamento na startup
    """
    logger.info("Starting Metrics Service...")
    try:
        init_metrics_storage()
        logger.info("Metrics Service ready")
    except Exception as e:
        logger.error(f"Failed to start service: {e}")
        raise


@app.get("/")
async def root():
    """Health check endpoint"""
    try:
        metrics_count = sum(1 for _ in open(METRICS_FILE))
    except:
        metrics_count = 0
    
    return {
        "service": "metrics-service",
        "status": "running",
        "total_metrics": metrics_count,
        "agent_enabled": AGENT_CONFIG["enabled"],
        "agent_url": AGENT_CONFIG["url"] if AGENT_CONFIG["enabled"] else None,
        "platform": "windows-server",
        "version": "1.0.0"
    }


@app.post("/internal/configure_agent")
async def configure_agent(config: AgentConfig):
    """
    Configura conexão com Lanne Agent rodando no Linux do usuário
    
    Exemplo:
    {
        "url": "http://192.168.1.100:9000",
        "token": "meu-token-secreto"
    }
    """
    try:
        url = config.url
        token = config.token
        
        # Testar conexão com o agente
        headers = {}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{url}/ping", headers=headers)
            response.raise_for_status()
        
        # Salvar configuração
        AGENT_CONFIG["enabled"] = True
        AGENT_CONFIG["url"] = url
        AGENT_CONFIG["token"] = token or ""
        
        logger.info(f"Lanne Agent configured: {url}")
        
        return {
            "status": "success",
            "message": f"Lanne Agent configured successfully: {url}",
            "agent_status": response.json()
        }
        
    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Agent connection failed: HTTP {e.response.status_code}"
        )
    except httpx.RequestError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Agent connection failed: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Error configuring agent: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@app.post("/internal/log")
async def log_metric(metric: MetricsLog):
    """
    Registra uma métrica no sistema
    Armazena em formato JSONL para fácil processamento
    """
    try:
        logger.info(f"Logging metric from {metric.service}: {metric.endpoint}")
        
        # Converter para dict e adicionar ao arquivo
        metric_dict = metric.model_dump()
        metric_dict["timestamp"] = metric.timestamp.isoformat()
        
        with open(METRICS_FILE, 'a') as f:
            f.write(json.dumps(metric_dict) + '\n')
        
        return {"status": "success", "message": "Metric logged"}
        
    except Exception as e:
        logger.error(f"Error logging metric: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@app.get("/internal/read_metrics")
async def read_metrics(
    service: Optional[str] = None,
    limit: int = 100
) -> List[Dict[str, Any]]:
    """
    Lê métricas armazenadas
    Opcionalmente filtra por serviço
    """
    try:
        logger.info(f"Reading metrics (service={service}, limit={limit})")
        
        metrics = []
        with open(METRICS_FILE, 'r') as f:
            for line in f:
                try:
                    metric = json.loads(line.strip())
                    
                    # Filtrar por serviço se especificado
                    if service and metric.get("service") != service:
                        continue
                    
                    metrics.append(metric)
                    
                    # Limitar resultados
                    if len(metrics) >= limit:
                        break
                        
                except json.JSONDecodeError:
                    continue
        
        # Retornar mais recentes primeiro
        metrics.reverse()
        
        return metrics
        
    except FileNotFoundError:
        return []
    except Exception as e:
        logger.error(f"Error reading metrics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@app.get("/internal/read_syslog")
async def read_syslog(lines: int = 100) -> Dict[str, Any]:
    """
    Lê logs do sistema Linux via Lanne Agent
    O agent deve estar rodando na máquina Linux do usuário
    """
    if not AGENT_CONFIG["enabled"]:
        return {
            "status": "error",
            "message": "Lanne Agent not configured. Use /internal/configure_agent first",
            "logs": ""
        }
    
    try:
        logger.info(f"Reading syslog from Linux agent ({lines} lines)")
        
        # Preparar headers de autenticação
        headers = {}
        if AGENT_CONFIG["token"]:
            headers["Authorization"] = f"Bearer {AGENT_CONFIG['token']}"
        
        # Tentar journalctl primeiro
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.post(
                    f"{AGENT_CONFIG['url']}/execute",
                    json={
                        "command": "journalctl",
                        "params": {"lines": str(lines)}
                    },
                    headers=headers
                )
                
                logger.info(f"Journalctl response status: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    logger.info(f"Journalctl exit_code: {data.get('exit_code')}")
                    
                    if data.get("exit_code") == 0:
                        return {
                            "status": "success",
                            "logs": data.get("stdout", ""),
                            "lines": lines,
                            "source": "journalctl (via Lanne Agent)",
                            "agent_url": AGENT_CONFIG["url"]
                        }
            except Exception as e:
                logger.error(f"Journalctl failed: {e}")
        
        # Fallback: tentar syslog
        logger.info("journalctl failed, trying syslog")
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.post(
                    f"{AGENT_CONFIG['url']}/execute",
                    json={
                        "command": "syslog",
                        "params": {"lines": str(lines)}
                    },
                    headers=headers
                )
                
                logger.info(f"Syslog response status: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    logger.info(f"Syslog exit_code: {data.get('exit_code')}")
                    
                    if data.get("exit_code") == 0:
                        return {
                            "status": "success",
                            "logs": data.get("stdout", ""),
                            "lines": lines,
                            "source": "/var/log/syslog (via Lanne Agent)",
                            "agent_url": AGENT_CONFIG["url"]
                        }
            except Exception as e:
                logger.error(f"Syslog failed: {e}")
        
        # Nenhum método funcionou
        return {
            "status": "error",
            "message": "Could not read logs from Linux system",
            "logs": "",
            "debug": "Both journalctl and syslog failed. Check agent logs."
        }
        
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error from agent: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Error from Lanne Agent: {e}"
        )
    except httpx.RequestError as e:
        logger.error(f"Connection error to agent: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Lanne Agent unavailable"
        )
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@app.get("/internal/service_status")
async def check_service_status() -> Dict[str, Any]:
    """
    Verifica status dos serviços no Linux via Lanne Agent
    """
    if not AGENT_CONFIG["enabled"]:
        return {
            "status": "error",
            "message": "Lanne Agent not configured",
            "output": ""
        }
    
    try:
        logger.info("Checking service status via agent")
        
        # Preparar headers
        headers = {}
        if AGENT_CONFIG["token"]:
            headers["Authorization"] = f"Bearer {AGENT_CONFIG['token']}"
        
        # Chamar o agent
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{AGENT_CONFIG['url']}/execute",
                json={"command": "systemctl_status"},
                headers=headers
            )
            response.raise_for_status()
            data = response.json()
        
        return {
            "status": "success",
            "output": data.get("stdout", ""),
            "agent_url": AGENT_CONFIG["url"]
        }
        
    except Exception as e:
        logger.error(f"Error checking service status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@app.get("/internal/stats")
async def get_statistics(service: Optional[str] = None) -> Dict[str, Any]:
    """
    Calcula estatísticas de performance
    Análise de latência, taxa de erro, etc.
    """
    try:
        metrics = await read_metrics(service=service, limit=1000)
        
        if not metrics:
            return {
                "total_requests": 0,
                "avg_latency_ms": 0,
                "error_rate": 0
            }
        
        # Calcular estatísticas
        latencies = [m.get("latency_ms", 0) for m in metrics]
        status_codes = [m.get("status_code", 0) for m in metrics]
        
        total_requests = len(metrics)
        avg_latency = sum(latencies) / total_requests if latencies else 0
        errors = sum(1 for code in status_codes if code >= 400)
        error_rate = (errors / total_requests) * 100 if total_requests > 0 else 0
        
        return {
            "total_requests": total_requests,
            "avg_latency_ms": round(avg_latency, 2),
            "min_latency_ms": min(latencies) if latencies else 0,
            "max_latency_ms": max(latencies) if latencies else 0,
            "error_rate": round(error_rate, 2),
            "total_errors": errors
        }
        
    except Exception as e:
        logger.error(f"Error calculating statistics: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@app.get("/internal/system_info")
async def get_system_info() -> Dict[str, Any]:
    """
    Obtém informações gerais do sistema Linux
    """
    if not AGENT_CONFIG["enabled"]:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Lanne Agent not configured"
        )
    
    try:
        headers = {}
        if AGENT_CONFIG["token"]:
            headers["Authorization"] = f"Bearer {AGENT_CONFIG['token']}"
        
        info = {}
        
        # Coletar várias informações
        commands = {
            "os": "os_release",
            "kernel": "kernel_version",
            "uptime": "uptime",
            "hostname": "hostname",
            "cpu": "cpu_info",
            "memory": "memory_usage",
            "disk": "disk_usage"
        }
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            for key, cmd in commands.items():
                try:
                    response = await client.post(
                        f"{AGENT_CONFIG['url']}/execute",
                        json={"command": cmd},
                        headers=headers
                    )
                    if response.status_code == 200:
                        data = response.json()
                        if data.get("exit_code") == 0:
                            info[key] = data.get("stdout", "").strip()
                except:
                    info[key] = "Error fetching"
        
        return info
        
    except Exception as e:
        logger.error(f"Error getting system info: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@app.get("/internal/linux_command")
async def execute_linux_command(command: str, params: Optional[str] = None) -> Dict[str, Any]:
    """
    Executa um comando específico no Linux
    
    Exemplo: /internal/linux_command?command=disk_usage
    """
    if not AGENT_CONFIG["enabled"]:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Lanne Agent not configured"
        )
    
    try:
        headers = {}
        if AGENT_CONFIG["token"]:
            headers["Authorization"] = f"Bearer {AGENT_CONFIG['token']}"
        
        # Preparar payload
        payload = {"command": command}
        if params:
            import json
            try:
                payload["params"] = json.loads(params)
            except:
                payload["params"] = {"value": params}
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{AGENT_CONFIG['url']}/execute",
                json=payload,
                headers=headers
            )
            response.raise_for_status()
            return response.json()
        
    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=e.response.status_code,
            detail=f"Agent error: {e}"
        )
    except Exception as e:
        logger.error(f"Error executing command: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8005)