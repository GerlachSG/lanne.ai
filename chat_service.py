import warnings
import torch
import re
import os
import logging
from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline, GenerationConfig, StoppingCriteria, StoppingCriteriaList
from peft import PeftModel, PeftConfig
from typing import List, Dict, Optional
import sqlite3
import random
import time


# Remove warnings
warnings.filterwarnings('ignore')
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'
os.environ['TOKENIZERS_PARALLELISM'] = 'false'

logging.getLogger('transformers').setLevel(logging.ERROR)
logging.getLogger('torch').setLevel(logging.ERROR)
logging.getLogger('peft').setLevel(logging.ERROR)


# Base de respsotas

RELIABLE_ANSWERS = {
    # Identidade
    "identidade": [
        "Sou a Lanne, assistente especializada em Linux Debian! Posso ajudar com comandos, configuração e troubleshooting. No que precisa?",
        "Olá! Eu sou a Lanne, sua assistente para Linux Debian. Manda sua dúvida!",
        "Lanne aqui! Especialista em Debian à disposição. Qual sua pergunta?",
    ],
    
    # IP
    "ip_config": [
        "Para configurar IP estático:\n\nsudo nano /etc/network/interfaces\n\nAdicione:\nauto eth0\niface eth0 inet static\n    address 192.168.1.100\n    netmask 255.255.255.0\n    gateway 192.168.1.1\n\nDepois: sudo systemctl restart networking",
        "IP estático no Debian:\n\n1. Edita: sudo nano /etc/network/interfaces\n2. Configura:\n   auto eth0\n   iface eth0 inet static\n       address 192.168.1.100\n       netmask 255.255.255.0\n       gateway 192.168.1.1\n3. Reinicia: sudo systemctl restart networking",
    ],
    
    "ip_ver": [
        "Para ver o IP:\n\nip addr show\n\nou mais simples:\n\nhostname -I",
        "Comandos para ver IP:\n\nip a\nip addr show\nhostname -I",
    ],
    
    # Hostname
    "hostname": [
        "Para alterar o hostname:\n\nsudo hostnamectl set-hostname novo-nome\n\nMuda imediatamente, sem precisar reiniciar!",
        "Mudar hostname:\n\nsudo hostnamectl set-hostname seu-novo-nome\n\nJá aplica na hora.",
    ],
    
    # Atualizar
    "atualizar": [
        "Para atualizar o sistema:\n\nsudo apt update && sudo apt upgrade -y\n\nIsso atualiza a lista de pacotes e instala as atualizações.",
        "Atualizar Debian:\n\nsudo apt update\nsudo apt upgrade -y\n\nO -y confirma tudo automaticamente.",
    ],
    
    # SSH
    "ssh_instalar": [
        "Para instalar SSH:\n\nsudo apt install openssh-server -y\nsudo systemctl enable ssh\nsudo systemctl start ssh",
        "Instalar servidor SSH:\n\nsudo apt install openssh-server\nsudo systemctl enable --now ssh",
    ],
    
    "ssh_conectar": [
        "Para conectar via SSH:\n\nssh usuario@ip-do-servidor\n\nExemplo: ssh root@192.168.1.100",
        "Conectar SSH:\n\nssh usuario@endereco_ip\n\nSe tiver porta diferente:\nssh -p 2222 usuario@ip",
    ],
    
    # Sistema
    "memoria": [
        "Ver uso de memória:\n\nfree -h\n\nO -h mostra em formato legível (GB/MB).",
        "Memória RAM:\n\nfree -h",
    ],
    
    "disco": [
        "Ver espaço em disco:\n\ndf -h\n\nMostra uso de todas as partições.",
        "Uso de disco:\n\ndf -h  (geral)\ndu -sh /*  (por diretório)",
    ],
    
    "processos": [
        "Ver processos rodando:\n\ntop\n\nOu mais visual (precisa instalar):\n\nhtop",
        "Processos:\n\ntop - padrão\nhtop - mais bonito (instala com: sudo apt install htop)",
    ],
}


# Erros específicos
ERROR_SOLUTIONS = {
    "address already in use": """A porta já está ocupada!

Veja o que está usando a porta:
sudo lsof -i :80

ou

sudo netstat -tulpn | grep :80

Para matar o processo:
sudo kill [PID]

Ou para o serviço:
sudo systemctl stop apache2
sudo systemctl stop nginx""",

    "networking.service failed": """Erro no serviço de rede. Causas comuns:

1. Sintaxe errada no /etc/network/interfaces
   Confere o formato com espaços corretos!

2. Nome da interface errado
   Vê o nome: ip link show

3. Tenta manualmente:
   sudo ifdown eth0
   sudo ifup eth0

Vê os logs: journalctl -xe | tail -30""",

    "permission denied": """Falta permissão!

Usa: sudo [seu-comando]

Se não funcionar, verifica se tá no grupo sudo:
groups

Adiciona ao grupo:
su -
usermod -aG sudo seu_usuario""",

    "command not found": """Comando não instalado.

Procura o pacote:
apt search nome

Instala:
sudo apt install nome-do-pacote""",
}


# Detectar intenção
def detect_intent(query: str) -> Optional[str]:
    """Detecta a intenção da pergunta com precisão"""
    q = query.lower().strip()
    q = re.sub(r'[?!.,;:]', '', q)
    
    # Identidade
    if any(phrase in q for phrase in ["quem é você", "quem e voce", "quem é vc", "qual seu nome", "o que você faz", "quem eh voce"]):
        return "identidade"
    
    # IP - configurar
    if any(phrase in q for phrase in ["alterar ip", "mudar ip", "configurar ip", "config ip", "setar ip", "ip estatico", "ip fixo", "trocar ip", "definir ip", "muda ip", "como ip"]):
        return "ip_config"
    
    # IP - ver
    if any(phrase in q for phrase in ["ver ip", "mostrar ip", "qual ip", "meu ip", "ip atual"]):
        return "ip_ver"
    
    # Hostname
    if any(phrase in q for phrase in ["alterar hostname", "mudar hostname", "muda hostname", "trocar hostname", "hostname novo", "config hostname"]):
        return "hostname"
    
    # Atualizar
    if any(word in q for word in ["atualizar", "update", "upgrade"]) and "sistema" in q or q in ["atualizar", "update"]:
        return "atualizar"
    
    # SSH
    if "instalar ssh" in q or "ssh server" in q or "openssh" in q:
        return "ssh_instalar"
    
    if "conectar ssh" in q or "acessar ssh" in q or ("ssh" in q and ("como" in q or "conectar" in q)):
        return "ssh_conectar"
    
    # Sistema
    if any(phrase in q for phrase in ["ver memoria", "memoria ram", "uso memoria", "free"]):
        return "memoria"
    
    if any(phrase in q for phrase in ["espaco disco", "ver disco", "uso disco", "df"]):
        return "disco"
    
    if "processos" in q or q in ["top", "htop"]:
        return "processos"
    
    return None


def detect_error_pattern(query: str, history: List[Dict[str, str]]) -> Optional[str]:
    """Detecta padrões de erro nas últimas mensagens"""
    recent = " ".join([
        msg.get('content', '') 
        for msg in history[-3:] 
        if msg.get('sender') == 'user'
    ]).lower()
    
    for pattern, solution in ERROR_SOLUTIONS.items():
        if pattern in recent:
            return solution
    
    return None


def casual_reply(query: str) -> Optional[str]:
    """Respostas casuais/conversacionais"""
    q = query.lower().strip()
    
    replies = {
        "oi": "Oi! Qual sua dúvida sobre Linux?",
        "olá": "Olá! Como posso ajudar?",
        "ola": "Olá! Como posso ajudar?",
        "e ai": "E aí! Manda sua pergunta.",
        "caraca": "Relaxa! Me fala o erro completo.",
        "que bo": "Calma! Qual o erro?",
        "e agora": "Me diz o problema que tá tendo.",
        "socorro": "Tranquilo! Qual o erro?",
        "ajuda": "Claro! Qual sua dúvida?",
        "valeu": "De nada! Precisa de mais alguma coisa?",
        "obrigado": "Por nada! Qualquer coisa é só chamar.",
        "obrigada": "Por nada! Qualquer coisa é só chamar.",
    }
    
    for trigger, reply in replies.items():
        if q == trigger or q.startswith(trigger + " "):
            return reply
    
    return None


# Configurações
PEFT_MODEL_PATH = "./lanne-ai-final"


# Classes auxiliares
class MemoryDatabase:
    def __init__(self, db_path="lanne_memory.db"):
        self.db_path = db_path
        self._initialize_database()

    def _initialize_database(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS memory (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    key TEXT NOT NULL,
                    value TEXT NOT NULL
                )
                """
            )
            conn.commit()

    def save_memory(self, key: str, value: str):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO memory (key, value) VALUES (?, ?)", (key, value))
            conn.commit()

    def get_memory(self, key: str) -> Optional[str]:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM memory WHERE key = ?", (key,))
            result = cursor.fetchone()
            return result[0] if result else None


# Sistema híbrido funcionando
class ChatService:
    """
    Sistema HÍBRIDO DEFINITIVO:
    - Respostas diretas para comandos conhecidos (confiável)
    - Modelo desativado (está gerando lixo)
    - Fallback útil para casos não cobertos
    """
    
    def __init__(self, simulate_thinking: bool = True):
        print("[Lanne.AI] Inicializando...")
        
        self.simulate_thinking = simulate_thinking
        self.memory_db = MemoryDatabase()
        
        print("[Lanne.AI] Sistema ativo (modo otimizado)")


    def _simulate_thinking(self):
        """Delay para parecer natural"""
        if self.simulate_thinking:
            time.sleep(random.uniform(0.4, 1.1))


    def get_lanne_response(self, history: List[Dict[str, str]]) -> str:
        """
        Fluxo de resposta:
        1. Detecção de intenção (comandos conhecidos)
        2. Detecção de erros
        3. Respostas casuais
        4. Fallback útil
        """
        
        if not history or history[-1].get('sender') != 'user':
            return ""
        
        user_query = history[-1].get('content', '').strip()
        
        # Simula pensamento
        self._simulate_thinking()
        
        # 1. Intenções claras
        intent = detect_intent(user_query)
        if intent and intent in RELIABLE_ANSWERS:
            return random.choice(RELIABLE_ANSWERS[intent])
        
        # 2. Erros específicos
        error_solution = detect_error_pattern(user_query, history)
        if error_solution:
            return error_solution
        
        # 3. Respostas casuais
        casual = casual_reply(user_query)
        if casual:
            return casual
        
        # 4. Fallback inteligente
        return self._smart_fallback(user_query, history)


    def _smart_fallback(self, query: str, history: List[Dict[str, str]]) -> str:
        """Fallback que tenta ajudar baseado no contexto"""
        q_lower = query.lower()
        
        # Detecta tema geral
        if any(word in q_lower for word in ["erro", "problema", "falha", "deu ruim"]):
            return """Entendi que deu erro. Para eu ajudar melhor, me fala:

• Qual comando você usou?
• Qual a mensagem de erro completa?
• O que você estava tentando fazer?

Comandos úteis para debug:
journalctl -xe | tail -30
systemctl status nome-servico"""
        
        if any(word in q_lower for word in ["instalar", "install"]):
            return """Para instalar pacotes no Debian:

sudo apt install nome-do-pacote

Procurar pacotes:
apt search termo

Exemplo: sudo apt install nginx"""
        
        if any(word in q_lower for word in ["remover", "deletar", "desinstalar"]):
            return """Para remover pacotes:

sudo apt remove nome-do-pacote

Remove com configs:
sudo apt purge nome-do-pacote

Limpa dependências:
sudo apt autoremove"""
        
        if any(word in q_lower for word in ["porta", "firewall", "ufw"]):
            return """Gerenciar firewall (UFW):

sudo ufw enable
sudo ufw allow 80/tcp
sudo ufw status

Exemplo: sudo ufw allow 22  (libera SSH)"""
        
        if any(word in q_lower for word in ["servico", "serviço", "service"]):
            return """Gerenciar serviços:

sudo systemctl start nome
sudo systemctl stop nome
sudo systemctl status nome
sudo systemctl enable nome  (inicia no boot)

Listar: systemctl list-units --type=service"""
        
        # Fallback genérico
        return """Não tenho certeza do que você precisa. Posso ajudar com:

📌 Configurações:
• IP estático e rede
• Hostname
• SSH

📦 Pacotes:
• Instalar/remover
• Atualizar sistema

🔧 Sistema:
• Ver memória/disco
• Gerenciar serviços
• Solucionar erros

Me fala mais especificamente o que precisa!"""


    # Métodos auxiliares
    def save_to_memory(self, key: str, value: str):
        self.memory_db.save_memory(key, value)
    
    def get_from_memory(self, key: str) -> Optional[str]:
        return self.memory_db.get_memory(key)

    def get_random_introduction(self) -> str:
        return random.choice(RELIABLE_ANSWERS["identidade"])

    def generate_title(self, user_input: str) -> str:
        q = user_input.lower()
        
        if "ip" in q:
            return "Configuração de IP"
        elif "hostname" in q:
            return "Hostname"
        elif "ssh" in q:
            return "SSH"
        elif "erro" in q:
            return "Solução de Erro"
        elif "atualiz" in q:
            return "Atualização"
        else:
            return f"{user_input[:30]}..."



# Sistema de teste 
if __name__ == "__main__":
    chat = ChatService(simulate_thinking=False)
    
    print("\n" + "="*70)
    print("TESTE - SISTEMA HÍBRIDO DEFINITIVO")
    print("="*70)
    
    history = []
    
    testes = [
        "quem é você",
        "como alterar o ip",
        "como configurar o ip",
        "como muda o hostname",
        "instalar ssh",
        "deu erro quando tentei mudar o ip",
    ]
    
    for msg in testes:
        history.append({"sender": "user", "content": msg})
        resposta = chat.get_lanne_response(history)
        print(f"\n👤 {msg}")
        print(f"🤖 {resposta}")
        history.append({"sender": "assistant", "content": resposta})
        print("-" * 70)
