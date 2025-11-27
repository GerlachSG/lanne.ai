"""
Start All Services - Orquestrador que inicia todos os microsserviços Lanne AI
Execute: python start_all.py

Inicia todos os 8 microsserviços em processos separados:
- Gateway (8000)
- Orchestrator (8001)
- Inference (8002)
- RAG (8003)
- Web Search (8004)
- Metrics (8005)
- Conversation (8006)
- Auth (8007)
"""

import subprocess
import sys
import os
import time
import signal
from pathlib import Path

# Cores para terminal
COLORS = {
    "GREEN": "\033[92m",
    "CYAN": "\033[96m",
    "YELLOW": "\033[93m",
    "MAGENTA": "\033[95m",
    "BLUE": "\033[94m",
    "RED": "\033[91m",
    "RESET": "\033[0m",
    "BOLD": "\033[1m",
}

# Configuração dos serviços
SERVICES = [
    {
        "name": "Gateway",
        "dir": "gateway-service",
        "port": 8000,
        "color": "CYAN"
    },
    {
        "name": "Orchestrator",
        "dir": "orchestrator-service",
        "port": 8001,
        "color": "MAGENTA"
    },
    {
        "name": "Inference",
        "dir": "inference-service",
        "port": 8002,
        "color": "BLUE"
    },
    {
        "name": "RAG",
        "dir": "rag-service",
        "port": 8003,
        "color": "YELLOW"
    },
    {
        "name": "Web Search",
        "dir": "web-search-service",
        "port": 8004,
        "color": "GREEN"
    },
    {
        "name": "Metrics",
        "dir": "metrics-service",
        "port": 8005,
        "color": "CYAN"
    },
    {
        "name": "Conversation",
        "dir": "conversation-service",
        "port": 8006,
        "color": "MAGENTA"
    },
    {
        "name": "Auth",
        "dir": "auth-service",
        "port": 8007,
        "color": "GREEN"
    }
]

# Lista de processos em execução
running_processes = []


def print_colored(text, color="RESET", bold=False):
    """Imprime texto colorido"""
    color_code = COLORS.get(color, COLORS["RESET"])
    bold_code = COLORS["BOLD"] if bold else ""
    print(f"{bold_code}{color_code}{text}{COLORS['RESET']}")


def print_banner():
    """Imprime banner inicial"""
    print("\n" + "=" * 60)
    print_colored("Lanne AI - Windows Server", "CYAN", bold=True)
    print_colored("Starting all microservices...", "CYAN")
    print("=" * 60 + "\n")


def check_dependencies():
    """Verifica se as dependências estão instaladas"""
    try:
        import fastapi
        import uvicorn
        import httpx
        print_colored("Dependencies OK", "GREEN")
        return True
    except ImportError as e:
        print_colored(f"Missing dependencies: {e}", "RED")
        print_colored("\nPlease install dependencies first:", "YELLOW")
        print_colored("pip install -r requirements.txt", "YELLOW")
        return False


def start_service(service):
    """Inicia um microsserviço"""
    service_name = service["name"]
    service_dir = Path(service["dir"]).absolute()
    port = service["port"]
    
    if not service_dir.exists():
        print_colored(f"{service_name}: Directory not found: {service_dir}", "RED")
        return None
    
    main_py = service_dir / "main.py"
    if not main_py.exists():
        print_colored(f"{service_name}: main.py not found", "RED")
        return None
    
    print_colored(f"Starting {service_name} on port {port}...", service["color"])
    
    try:
        process = subprocess.Popen(
            [sys.executable, "main.py"],
            cwd=str(service_dir),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == 'nt' else 0,
            text=True,
            bufsize=1,
            env=os.environ.copy()
        )
        
        time.sleep(2)
        
        if process.poll() is not None:
            stdout, _ = process.communicate()
            print_colored(f"{service_name}: Process exited immediately", "RED")
            print_colored(f"Output:\n{stdout}", "RED")
            return None
        
        return process
        
    except Exception as e:
        print_colored(f"{service_name}: Failed to start: {e}", "RED")
        return None


def stop_all_services(signum=None, frame=None):
    """Para todos os serviços em execução"""
    print_colored("\n\nStopping all services...", "YELLOW", bold=True)
    
    for process in running_processes:
        try:
            if process.poll() is None:
                if os.name == 'nt':
                    subprocess.run(['taskkill', '/F', '/T', '/PID', str(process.pid)],
                                 capture_output=True)
                else:
                    process.terminate()
                    process.wait(timeout=5)
        except Exception as e:
            print_colored(f"Error stopping process: {e}", "RED")
    
    print_colored("All services stopped.", "GREEN")
    sys.exit(0)


def main():
    """Função principal"""
    print_banner()
    
    if not check_dependencies():
        sys.exit(1)
    
    signal.signal(signal.SIGINT, stop_all_services)
    if hasattr(signal, 'SIGTERM'):
        signal.signal(signal.SIGTERM, stop_all_services)
    
    print_colored("\nStarting services...\n", "CYAN", bold=True)
    
    for service in SERVICES:
        process = start_service(service)
        if process:
            running_processes.append(process)
            time.sleep(3)
        else:
            print_colored(f"\nFailed to start {service['name']}", "RED", bold=True)
            print_colored("Stopping all services...", "YELLOW")
            stop_all_services()
            sys.exit(1)
    
    print_colored("\nWaiting for services to initialize...", "YELLOW")
    for i in range(15):
        time.sleep(1)
        print(".", end="", flush=True)
    print()
    
    all_started = True
    print_colored("\nService Status:", "CYAN", bold=True)
    for service, process in zip(SERVICES, running_processes):
        if process.poll() is None:
            print_colored(
                f"{service['name']:15} - Running on port {service['port']}",
                "GREEN"
            )
        else:
            print_colored(
                f"{service['name']:15} - Failed to start",
                "RED"
            )
            all_started = False
    
    if all_started:
        print("\n" + "=" * 60)
        print_colored("All services started successfully!", "GREEN", bold=True)
        print_colored("Press Ctrl+C to stop all services", "YELLOW")
        print("=" * 60 + "\n")
        
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            stop_all_services()
    else:
        print_colored("\nSome services failed to start!", "RED", bold=True)
        stop_all_services()
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\nFatal error: {e}")
        sys.exit(1)