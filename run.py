#!/usr/bin/env python3
"""
Lanne AI - Inicializador Completo
Verifica requisitos, instala dependências e inicia todos os serviços
"""

import sys
import subprocess
import time
import os
import platform
from pathlib import Path

# Cores para terminal
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def print_header(text):
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}  {text}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'='*60}{Colors.ENDC}\n")

def print_success(text):
    print(f"{Colors.OKGREEN}✓ {text}{Colors.ENDC}")

def print_error(text):
    print(f"{Colors.FAIL}✗ {text}{Colors.ENDC}")

def print_warning(text):
    print(f"{Colors.WARNING}! {text}{Colors.ENDC}")

def print_info(text):
    print(f"{Colors.OKBLUE}ℹ {text}{Colors.ENDC}")

def check_python_version():
    """Verifica versão do Python"""
    print_info("Verificando versão do Python...")
    
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print_error(f"Python {version.major}.{version.minor} detectado")
        print_error("É necessário Python 3.8 ou superior!")
        print_info("Baixe em: https://www.python.org/downloads/")
        return False
    
    print_success(f"Python {version.major}.{version.minor}.{version.micro}")
    return True

def check_pip():
    """Verifica se pip está disponível"""
    print_info("Verificando pip...")
    
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "--version"],
            capture_output=True,
            text=True,
            check=True
        )
        print_success(f"pip instalado: {result.stdout.strip()}")
        return True
    except subprocess.CalledProcessError:
        print_error("pip não encontrado!")
        print_info("Instalando pip...")
        try:
            subprocess.run([sys.executable, "-m", "ensurepip", "--upgrade"], check=True)
            print_success("pip instalado com sucesso!")
            return True
        except:
            print_error("Falha ao instalar pip")
            return False

def check_dependencies():
    """Verifica se dependências críticas estão instaladas"""
    print_info("Verificando dependências críticas...")
    
    critical_packages = [
        'fastapi',
        'uvicorn',
        'httpx',
        'pydantic',
        'lanne_schemas'  # Pacote local essencial
    ]
    
    missing = []
    for package in critical_packages:
        try:
            __import__(package)
            print_success(f"{package} instalado")
        except ImportError:
            missing.append(package)
            print_warning(f"{package} não encontrado")
    
    return len(missing) == 0, missing

def install_dependencies():
    """Instala dependências do requirements.txt"""
    print_header("Instalando Dependências")
    
    requirements_file = Path(__file__).parent / "requirements.txt"
    lanne_schemas_dir = Path(__file__).parent / "lanne-schemas"
    
    if not requirements_file.exists():
        print_error(f"Arquivo requirements.txt não encontrado em {requirements_file}")
        return False
    
    try:
        # Atualizar pip primeiro
        print_info("Atualizando pip...")
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "--upgrade", "pip"],
            check=True,
            stdout=subprocess.DEVNULL
        )
        
        # Instalar lanne-schemas primeiro (pacote local)
        if lanne_schemas_dir.exists():
            print_info("Instalando lanne-schemas (pacote local)...")
            subprocess.run(
                [sys.executable, "-m", "pip", "install", "-e", str(lanne_schemas_dir)],
                check=True
            )
            print_success("lanne-schemas instalado!")
        
        # Instalar dependências do requirements.txt
        print_info(f"Instalando pacotes de {requirements_file}...")
        print_info("Isso pode levar alguns minutos...")
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", str(requirements_file)],
            check=True
        )
        
        print_success("Todas as dependências instaladas com sucesso!")
        return True
        
    except subprocess.CalledProcessError as e:
        print_error(f"Erro ao instalar dependências: {e}")
        return False

def start_backend():
    """Inicia cada serviço em janela separada"""
    print_header("Iniciando Servicos Backend")
    
    base_path = Path(__file__).parent
    
    # Lista de servicos com seus caminhos e portas
    services = [
        ("Gateway", "gateway-service/main.py", 8000),
        ("Orchestrator", "orchestrator-service/main.py", 8001),
        ("Inference", "inference-service/main.py", 8002),
        ("RAG", "rag-service/main.py", 8003),
        ("Web Search", "web-search-service/main.py", 8004),
        ("Metrics", "metrics-service/main.py", 8005),
        ("Conversation", "conversation-service/main.py", 8006),
        ("Auth", "auth-service/main.py", 8007),
    ]
    
    processes = []
    
    for name, path, port in services:
        service_path = base_path / path
        
        if not service_path.exists():
            print_warning(f"{name} nao encontrado em {service_path}")
            continue
        
        print_info(f"Iniciando {name} na porta {port}...")
        
        try:
            if platform.system() == "Windows":
                # Cada servico em janela CMD separada com titulo
                process = subprocess.Popen(
                    f'start "{name} - Porta {port}" cmd /k {sys.executable} "{service_path}"',
                    shell=True,
                    cwd=str(base_path)
                )
            else:
                # Linux/Mac - usar gnome-terminal ou xterm se disponivel
                process = subprocess.Popen(
                    [sys.executable, str(service_path)],
                    cwd=str(base_path)
                )
            
            processes.append(process)
            print_success(f"{name} iniciado na porta {port}")
            time.sleep(0.5)  # Pequeno delay entre cada servico
            
        except Exception as e:
            print_error(f"Erro ao iniciar {name}: {e}")
    
    if not processes:
        print_error("Nenhum servico foi iniciado")
        return None
    
    print_success(f"{len(processes)} servicos iniciados!")
    return processes

def wait_for_services(timeout=30):
    """Aguarda serviços ficarem disponíveis"""
    print_header("Aguardando Serviços Ficarem Disponíveis")
    
    services = [
        ("Auth Service", "http://localhost:8007/"),
        ("Conversation Service", "http://localhost:8006/"),
        ("Gateway Service", "http://localhost:8000/"),
    ]
    
    print_info(f"Aguardando até {timeout} segundos...")
    
    import httpx
    
    for elapsed in range(timeout):
        all_ready = True
        
        for service_name, url in services:
            try:
                response = httpx.get(url, timeout=1.0)
                if response.status_code == 200:
                    if elapsed > 0:  # Só mostra após primeira tentativa
                        print_success(f"{service_name} disponível")
                else:
                    all_ready = False
            except:
                all_ready = False
        
        if all_ready:
            print_success(f"\nTodos os serviços disponíveis após {elapsed+1} segundos!")
            return True
        
        # Mostrar progresso
        if elapsed % 5 == 0 and elapsed > 0:
            print_info(f"Aguardando... ({elapsed}s)")
        
        time.sleep(1)
    
    print_warning("Timeout atingido, mas continuando...")
    return False

def start_web_server():
    """Inicia servidor HTTP para o website com CORS e no-cache"""
    print_header("Iniciando Servidor Web")
    
    website_path = Path(__file__).parent / "website"
    
    if not website_path.exists():
        print_error(f"Pasta website não encontrada")
        return None
    
    print_info("Iniciando servidor HTTP na porta 3000...")
    
    # Criar um script temporário para servidor com headers corretos
    server_script = Path(__file__).parent / "_temp_server.py"
    server_code = '''
import http.server
import socketserver
import os
import sys

PORT = 3000
DIRECTORY = sys.argv[1] if len(sys.argv) > 1 else "."

class NoCacheHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)
    
    def end_headers(self):
        # Headers para evitar cache
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        # CORS headers
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        super().end_headers()
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

with socketserver.TCPServer(("", PORT), NoCacheHandler) as httpd:
    print(f"Servidor rodando em http://localhost:{PORT}")
    httpd.serve_forever()
'''
    
    try:
        # Escrever script temporário
        with open(server_script, 'w', encoding='utf-8') as f:
            f.write(server_code)
        
        # Windows
        if platform.system() == "Windows":
            process = subprocess.Popen(
                ["start", "cmd", "/k", sys.executable, str(server_script), str(website_path)],
                shell=True
            )
        # Linux/Mac
        else:
            process = subprocess.Popen(
                [sys.executable, str(server_script), str(website_path)]
            )
        
        time.sleep(2)  # Aguardar servidor iniciar
        print_success("Servidor web iniciado em http://localhost:3000")
        return process
        
    except Exception as e:
        print_error(f"Erro ao iniciar servidor web: {e}")
        return None

def open_browser():
    """Abre o navegador"""
    print_info("Abrindo navegador...")
    
    import webbrowser
    try:
        webbrowser.open("http://localhost:3000/pages/index.html")
        print_success("Navegador aberto!")
        return True
    except Exception as e:
        print_warning(f"Não foi possível abrir o navegador automaticamente: {e}")
        print_info("Abra manualmente: http://localhost:3000/pages/index.html")
        return False

def main():
    """Função principal"""
    print_header("Lanne AI - Inicializador Completo")
    
    # Verificar Python
    if not check_python_version():
        input("\nPressione Enter para sair...")
        sys.exit(1)
    
    # Verificar pip
    if not check_pip():
        input("\nPressione Enter para sair...")
        sys.exit(1)
    
    # Verificar dependências
    deps_ok, missing = check_dependencies()
    
    if not deps_ok:
        print_warning(f"Faltam {len(missing)} dependências")
        response = input("\nDeseja instalar as dependências agora? (S/n): ").strip().lower()
        
        if response in ['', 's', 'sim', 'y', 'yes']:
            if not install_dependencies():
                print_error("Falha ao instalar dependências")
                input("\nPressione Enter para sair...")
                sys.exit(1)
        else:
            print_error("Dependências são necessárias para continuar")
            input("\nPressione Enter para sair...")
            sys.exit(1)
    else:
        print_success("Todas as dependências estão instaladas!")
    
    # Iniciar backend
    backend_processes = start_backend()
    if not backend_processes:
        print_error("Falha ao iniciar backend")
        input("\nPressione Enter para sair...")
        sys.exit(1)
    
    # Aguardar serviços
    wait_for_services(timeout=20)
    
    # Iniciar servidor web
    web_process = start_web_server()
    if not web_process:
        print_error("Falha ao iniciar servidor web")
        input("\nPressione Enter para sair...")
        sys.exit(1)
    
    # Abrir navegador
    open_browser()
    
    # Mensagem final
    print_header("Sistema Iniciado com Sucesso!")
    print_success("Website: http://localhost:3000/pages/index.html")
    print_success("Backend: Rodando em segundo plano")
    print()
    print_info("Para parar tudo: Feche as janelas dos serviços ou pressione Ctrl+C")
    print()
    
    try:
        input("Pressione Enter para encerrar e parar todos os serviços...\n")
    except KeyboardInterrupt:
        print("\n")
    
    print_info("Encerrando servicos...")
    
    # Tentar encerrar processos do backend
    if backend_processes:
        for proc in backend_processes:
            try:
                proc.terminate()
            except:
                pass
    
    if web_process:
        try:
            web_process.terminate()
        except:
            pass
    
    # Limpar arquivo temporário do servidor
    temp_server = Path(__file__).parent / "_temp_server.py"
    if temp_server.exists():
        try:
            temp_server.unlink()
        except:
            pass
    
    print_success("Serviços encerrados!")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{Colors.WARNING}Interrompido pelo usuário{Colors.ENDC}")
        sys.exit(0)
    except Exception as e:
        print_error(f"Erro inesperado: {e}")
        import traceback
        traceback.print_exc()
        input("\nPressione Enter para sair...")
        sys.exit(1)
