#!/usr/bin/env python3
"""
Lanne Agent - Cliente Linux para Lanne AI
Roda na máquina do usuário Linux e permite que o servidor Windows
execute comandos autorizados via HTTP

Instalação:
    pip install fastapi uvicorn pydantic

Uso:
    python lanne_agent.py --token SEU_TOKEN_AQUI --port 9000
"""

from fastapi import FastAPI, HTTPException, status, Depends, Header
from pydantic import BaseModel
from typing import Optional, List
import subprocess
import argparse
import logging
import os

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Token de autenticação (será definido via argumento)
AUTH_TOKEN = ""

# Inicializar FastAPI
app = FastAPI(
    title="Lanne Agent",
    description="Cliente Linux para Lanne AI - Executa comandos autorizados",
    version="1.0.0"
)

# Comandos permitidos (whitelist de segurança)
ALLOWED_COMMANDS = {
    # Logs e Sistema
    "journalctl": ["journalctl", "-n", "{lines}", "--no-pager"],
    "syslog": ["tail", "-n", "{lines}", "/var/log/syslog"],
    "dmesg": ["dmesg", "--human", "--color=never", "-T"],
    "systemctl_status": ["systemctl", "status", "--no-pager"],
    "systemctl_failed": ["systemctl", "--failed", "--no-pager"],
    "systemctl_list": ["systemctl", "list-units", "--type=service", "--no-pager"],
    
    # Hardware e Recursos
    "disk_usage": ["df", "-h"],
    "disk_usage_inodes": ["df", "-i"],
    "disk_io": ["iostat", "-x", "1", "1"],
    "memory_usage": ["free", "-h"],
    "memory_detailed": ["cat", "/proc/meminfo"],
    "cpu_info": ["lscpu"],
    "cpu_usage": ["top", "-bn1", "-o", "%CPU"],
    "load_average": ["cat", "/proc/loadavg"],
    
    # Rede
    "network_info": ["ip", "addr", "show"],
    "network_routes": ["ip", "route", "show"],
    "network_stats": ["ss", "-tunap"],
    "network_connections": ["netstat", "-tulpn"],
    "ping_test": ["ping", "-c", "4", "{host}"],
    
    # Processos
    "processes_top": ["ps", "aux", "--sort=-%mem"],
    "processes_tree": ["pstree", "-p"],
    "processes_count": ["ps", "aux", "|", "wc", "-l"],
    
    # Sistema de Arquivos
    "mount_points": ["mount"],
    "block_devices": ["lsblk", "-f"],
    "file_systems": ["cat", "/proc/filesystems"],
    
    # Usuários e Segurança
    "logged_users": ["who"],
    "last_logins": ["last", "-n", "20"],
    "failed_logins": ["lastb", "-n", "20"],
    "users_list": ["cat", "/etc/passwd"],
    
    # Kernel e Boot
    "kernel_version": ["uname", "-a"],
    "boot_log": ["journalctl", "-b", "-n", "{lines}", "--no-pager"],
    "kernel_modules": ["lsmod"],
    
    # Pacotes (Debian/Ubuntu)
    "apt_updates": ["apt", "list", "--upgradable"],
    "dpkg_list": ["dpkg", "-l"],
    "apt_history": ["tail", "-n", "50", "/var/log/apt/history.log"],
    
    # Tempo e Data
    "uptime": ["uptime"],
    "date": ["date"],
    "timezone": ["timedatectl"],
    
    # Diversos
    "environment": ["env"],
    "hostname": ["hostname", "-f"],
    "os_release": ["cat", "/etc/os-release"],
    "debian_version": ["cat", "/etc/debian_version"],
}


class ExecuteRequest(BaseModel):
    """Request para executar comando"""
    command: str
    params: Optional[dict] = None


class CustomCommandRequest(BaseModel):
    """Request para comando customizado"""
    command: str
    args: List[str] = []


def verify_token(authorization: Optional[str] = Header(None)):
    """
    Verifica token de autenticação
    """
    if not AUTH_TOKEN:
        # Modo desenvolvimento - sem autenticação
        return True
    
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header missing"
        )
    
    # Formato: Bearer TOKEN
    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise ValueError()
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format. Use: Bearer TOKEN"
        )
    
    if token != AUTH_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
    
    return True


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "service": "lanne-agent",
        "status": "running",
        "platform": "linux",
        "authenticated": len(AUTH_TOKEN) > 0,
        "version": "1.0.0"
    }


@app.get("/ping")
async def ping():
    """Ping endpoint - sem autenticação"""
    return {"status": "pong"}


@app.post("/execute")
async def execute_command(
    request: ExecuteRequest,
    authenticated: bool = Depends(verify_token)
):
    """
    Executa um comando autorizado da whitelist
    
    Exemplo:
    POST /execute
    {
        "command": "journalctl",
        "params": {"lines": "100"}
    }
    """
    try:
        command = request.command
        params = request.params
        
        # Verificar se comando está na whitelist
        if command not in ALLOWED_COMMANDS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Command '{command}' not allowed. Allowed: {list(ALLOWED_COMMANDS.keys())}"
            )
        
        # Construir comando
        cmd_template = ALLOWED_COMMANDS[command]
        if params:
            # Substituir parâmetros no template
            cmd = []
            for part in cmd_template:
                if "{" in part and "}" in part:
                    # Extrair nome do parâmetro
                    param_name = part.strip("{}")
                    if param_name in params:
                        cmd.append(str(params[param_name]))
                    else:
                        # Usar valor padrão
                        cmd.append("100" if param_name == "lines" else part)
                else:
                    cmd.append(part)
        else:
            cmd = cmd_template
        
        logger.info(f"Executing command: {' '.join(cmd)}")
        
        # Executar comando de forma segura (lista de argumentos, não shell)
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False,
            timeout=30  # Timeout de 30 segundos
        )
        
        return {
            "status": "success",
            "command": command,
            "exit_code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr
        }
        
    except subprocess.TimeoutExpired:
        logger.error(f"Command timeout: {command}")
        raise HTTPException(
            status_code=status.HTTP_408_REQUEST_TIMEOUT,
            detail="Command execution timeout (30s)"
        )
    except Exception as e:
        logger.error(f"Error executing command: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@app.get("/commands")
async def list_commands(authenticated: bool = Depends(verify_token)):
    """
    Lista comandos disponíveis
    """
    return {
        "allowed_commands": list(ALLOWED_COMMANDS.keys()),
        "commands": {
            name: {
                "template": cmd,
                "description": _get_command_description(name)
            }
            for name, cmd in ALLOWED_COMMANDS.items()
        }
    }


def _get_command_description(command: str) -> str:
    """Retorna descrição do comando"""
    descriptions = {
        # Logs e Sistema
        "journalctl": "Lê logs do systemd (journalctl)",
        "syslog": "Lê arquivo /var/log/syslog",
        "dmesg": "Mensagens do kernel (buffer de log)",
        "systemctl_status": "Verifica status dos serviços systemd",
        "systemctl_failed": "Lista serviços que falharam",
        "systemctl_list": "Lista todos os serviços",
        
        # Hardware e Recursos
        "disk_usage": "Mostra uso de disco",
        "disk_usage_inodes": "Mostra uso de inodes",
        "disk_io": "Estatísticas de I/O de disco",
        "memory_usage": "Mostra uso de memória",
        "memory_detailed": "Informações detalhadas de memória",
        "cpu_info": "Informações da CPU",
        "cpu_usage": "Processos ordenados por uso de CPU",
        "load_average": "Load average do sistema",
        
        # Rede
        "network_info": "Informações de interfaces de rede",
        "network_routes": "Tabela de rotas",
        "network_stats": "Estatísticas de rede (sockets)",
        "network_connections": "Conexões de rede ativas",
        "ping_test": "Testa conectividade (4 pings)",
        
        # Processos
        "processes_top": "Processos ordenados por uso de memória",
        "processes_tree": "Árvore de processos",
        "processes_count": "Conta processos ativos",
        
        # Sistema de Arquivos
        "mount_points": "Lista pontos de montagem",
        "block_devices": "Lista dispositivos de bloco",
        "file_systems": "Lista sistemas de arquivos suportados",
        
        # Usuários e Segurança
        "logged_users": "Usuários logados atualmente",
        "last_logins": "Últimos logins bem-sucedidos",
        "failed_logins": "Tentativas de login falhadas",
        "users_list": "Lista todos os usuários do sistema",
        
        # Kernel e Boot
        "kernel_version": "Versão do kernel",
        "boot_log": "Logs da última inicialização",
        "kernel_modules": "Módulos do kernel carregados",
        
        # Pacotes
        "apt_updates": "Pacotes com atualizações disponíveis",
        "dpkg_list": "Lista pacotes instalados (dpkg)",
        "apt_history": "Histórico de instalações apt",
        
        # Tempo e Data
        "uptime": "Tempo de atividade do sistema",
        "date": "Data e hora atual",
        "timezone": "Informações de fuso horário",
        
        # Diversos
        "environment": "Variáveis de ambiente",
        "hostname": "Nome do host",
        "os_release": "Informações da distribuição",
        "debian_version": "Versão do Debian",
    }
    return descriptions.get(command, "No description")


@app.post("/custom")
async def custom_command(
    request: CustomCommandRequest,
    authenticated: bool = Depends(verify_token)
):
    """
    Executa comando customizado (CUIDADO: apenas para admin)
    
    Requer autenticação e é desabilitado por padrão
    """
    # DESABILITADO por segurança
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Custom commands are disabled for security reasons"
    )


def main():
    """Inicializa o Lanne Agent"""
    parser = argparse.ArgumentParser(
        description="Lanne Agent - Cliente Linux para Lanne AI"
    )
    parser.add_argument(
        "--token",
        type=str,
        help="Token de autenticação (opcional no desenvolvimento)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=9000,
        help="Porta para o agente (padrão: 9000)"
    )
    parser.add_argument(
        "--host",
        type=str,
        default="0.0.0.0",
        help="Host para bind (padrão: 0.0.0.0)"
    )
    
    args = parser.parse_args()
    
    global AUTH_TOKEN
    AUTH_TOKEN = args.token or ""
    
    if AUTH_TOKEN:
        logger.info(f"✓ Authentication enabled with token")
    else:
        logger.warning("⚠ Running without authentication (development mode)")
    
    logger.info(f"Starting Lanne Agent on {args.host}:{args.port}")
    logger.info(f"Allowed commands: {list(ALLOWED_COMMANDS.keys())}")
    
    import uvicorn
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
