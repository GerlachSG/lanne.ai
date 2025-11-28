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
    """Inicia o start_all.py em processo separado"""
    print_header("Iniciando Serviços Backend")
    
    start_all_path = Path(__file__).parent / "start_all.py"
    
    if not start_all_path.exists():
        print_error(f"start_all.py não encontrado em {start_all_path}")
        return None
    
    print_info("Iniciando serviços backend...")
    print_warning("Uma nova janela será aberta com os logs dos serviços")
    
    try:
        # Windows
        if platform.system() == "Windows":
            process = subprocess.Popen(
                ["start", "cmd", "/k", sys.executable, str(start_all_path)],
                shell=True
            )
        # Linux/Mac
        else:
            process = subprocess.Popen(
                [sys.executable, str(start_all_path)]
            )
        
        print_success("Backend iniciado!")
        return process
        
    except Exception as e:
        print_error(f"Erro ao iniciar backend: {e}")
        return None

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
    """Inicia servidor HTTP para o website"""
    print_header("Iniciando Servidor Web")
    
    website_path = Path(__file__).parent / "website"
    
    if not website_path.exists():
        print_error(f"Pasta website não encontrada")
        return None
    
    print_info("Iniciando servidor HTTP na porta 3000...")
    
    try:
        # Windows
        if platform.system() == "Windows":
            process = subprocess.Popen(
                ["start", "cmd", "/k", sys.executable, "-m", "http.server", "3000", "--directory", str(website_path)],
                shell=True
            )
        # Linux/Mac
        else:
            process = subprocess.Popen(
                [sys.executable, "-m", "http.server", "3000", "--directory", str(website_path)]
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
    backend_process = start_backend()
    if not backend_process:
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
    
    print_info("Encerrando serviços...")
    
    # Tentar encerrar processos gracefully
    if backend_process:
        try:
            backend_process.terminate()
        except:
            pass
    
    if web_process:
        try:
            web_process.terminate()
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
