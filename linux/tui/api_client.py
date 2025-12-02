"""
API Client para comunicação com backend Lanne AI
ATUALIZADO: Suporte a Streaming (NDJSON) e Timeouts Altos
"""

import httpx
import os
from typing import Optional, Dict, List, AsyncGenerator
from pathlib import Path
import json
from datetime import datetime


class LanneAPIClient:
    """Cliente HTTP para backend Lanne AI"""
    
    def __init__(self, base_url: str = None):
        # URL do backend
        self.base_url = base_url or os.getenv("LANNE_BACKEND", "http://localhost")
        self._update_service_urls()
        
        # Sessão
        self.token: Optional[str] = None
        self.username: Optional[str] = None
        self.user_id: Optional[str] = None
        self.is_admin: bool = False
        
        # Estado
        self.conversation_id: Optional[str] = None
        self.conversation_title: Optional[str] = None
        
        # Config
        self.config_path = Path.home() / ".lanne" / "config.json"
        self.load_config()
    
    def _update_service_urls(self):
        self.gateway_url = f"{self.base_url}:8000"
        self.auth_url = f"{self.base_url}:8007"
        self.conversation_url = f"{self.base_url}:8006"
        self.orchestrator_url = f"{self.base_url}:8001"
    
    def set_base_url(self, url: str):
        self.base_url = url
        self._update_service_urls()
    
    # ... (Métodos load_config, save_config, clear_session, check_backend, check_agent mantidos iguais) ...
    # Vou replicar os métodos essenciais para manter o arquivo completo e funcional
    
    def load_config(self):
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    self.token = config.get("token")
                    self.username = config.get("username")
                    self.user_id = config.get("user_id")
                    self.is_admin = config.get("is_admin", False)
                    self.conversation_id = config.get("conversation_id")
                    if config.get("backend_url"):
                        self.base_url = config["backend_url"]
                        self._update_service_urls()
            except: pass
    
    def save_config(self):
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump({
                "token": self.token,
                "username": self.username,
                "user_id": self.user_id,
                "is_admin": self.is_admin,
                "conversation_id": self.conversation_id,
                "backend_url": self.base_url,
                "last_login": datetime.now().isoformat()
            }, f, indent=2)

    def clear_session(self):
        self.token = None
        self.username = None
        self.conversation_id = None
        self.conversation_title = None
        if self.config_path.exists(): self.config_path.unlink()

    @property
    def is_logged_in(self) -> bool:
        return self.token is not None and self.username is not None

    async def check_backend(self) -> Dict:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{self.gateway_url}/")
                return {"status": "ok", "data": resp.json()} if resp.status_code == 200 else {"status": "error"}
        except Exception as e: return {"status": "error", "message": str(e)}

    async def configure_agent(self, agent_url: str) -> Dict:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    f"{self.orchestrator_url}/internal/configure-agent",
                    json={"agent_url": agent_url, "enabled": True}
                )
                return resp.json()
        except Exception as e: return {"status": "error", "message": str(e)}

    # ... (Login e Register mantidos iguais, omitindo para brevidade se já funcionam, mas o foco é o chat) ...
    # Se precisar deles completos me avise, mas vou focar na mudança do CHAT abaixo

    async def register(self, username: str, admin: bool = False) -> Dict:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(f"{self.auth_url}/register", json={"username": username, "admin": admin})
            if resp.status_code == 400: return await self.login(username)
            resp.raise_for_status()
            data = resp.json()
            self._set_session(data)
            return {"status": "registered", "data": data}

    async def login(self, username: str) -> Dict:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(f"{self.auth_url}/login", json={"username": username})
            if resp.status_code == 404: raise Exception("Usuario nao encontrado")
            resp.raise_for_status()
            data = resp.json()
            self._set_session(data)
            return {"status": "logged_in", "data": data}
            
    def _set_session(self, data):
        self.username = data["username"]
        self.token = data["token"]
        self.user_id = data.get("user_id", self.username)
        self.save_config()

    async def logout(self):
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                await client.post(f"{self.auth_url}/logout", json={"token": self.token})
        except: pass
        self.clear_session()

    # =========================================================================
    # CHAT & STREAMING (A PARTE IMPORTANTE)
    # =========================================================================
    
    async def send_message_stream(self, text: str) -> AsyncGenerator[Dict, None]:
        """
        Envia mensagem e recebe stream de eventos (NDJSON).
        Processa status em tempo real e salva resposta final.
        """
        # Salva mensagem do usuário imediatamente
        await self._save_message_to_history(text, role="user")
        
        # Timeout alto (5 min) para suportar LLM local
        timeout = httpx.Timeout(300.0, connect=10.0)
        
        async with httpx.AsyncClient(timeout=timeout) as client:
            async with client.stream(
                "POST",
                f"{self.orchestrator_url}/internal/orchestrate",
                json={
                    "text": text,
                    "conversation_id": self.conversation_id,
                    "user_id": self.username
                },
                headers={"Accept-Charset": "utf-8"}
            ) as response:
                
                async for line in response.aiter_lines():
                    if not line.strip():
                        continue
                        
                    try:
                        data = json.loads(line)
                        yield data
                        
                        # Se for a resposta final, salva no histórico
                        if data.get("type") == "final_response":
                            response_content = data["data"].get("response", "")
                            await self._save_message_to_history(response_content, role="assistant")
                            
                    except json.JSONDecodeError:
                        continue

    async def _save_message_to_history(self, content: str, role: str):
        """Salva mensagem no banco de dados"""
        if not self.conversation_id:
            return
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                await client.post(
                    f"{self.conversation_url}/conversations/{self.conversation_id}/messages",
                    json={"role": role, "content": content}
                )
        except: pass # Falha silenciosa no histórico para não travar chat

    # Métodos auxiliares de conversa
    async def create_conversation(self, title: str = None) -> str:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"{self.conversation_url}/conversations",
                json={"user_id": self.username, "title": title or "Nova Conversa"}
            )
            data = resp.json()
            self.conversation_id = data["id"]
            self.conversation_title = data.get("title")
            self.save_config()
            return data["id"]

    async def list_conversations(self) -> List[Dict]:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{self.conversation_url}/conversations", params={"user_id": self.username})
            return resp.json()

    async def get_messages(self, conversation_id: str) -> List[Dict]:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{self.conversation_url}/conversations/{conversation_id}/messages")
            return resp.json()
            
    async def get_conversation(self, conversation_id: str) -> Dict:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{self.conversation_url}/conversations/{conversation_id}")
            return resp.json()

    async def update_conversation(self, conversation_id: str, title: str = None, description: str = None) -> Dict:
        payload = {}
        if title: payload["title"] = title
        if description: payload["description"] = description
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.patch(f"{self.conversation_url}/conversations/{conversation_id}", json=payload)
            return resp.json()

    async def delete_conversation(self, conversation_id: str):
        async with httpx.AsyncClient(timeout=10.0) as client:
            await client.delete(f"{self.conversation_url}/conversations/{conversation_id}")
        if self.conversation_id == conversation_id:
            self.conversation_id = None
            self.conversation_title = None
            self.save_config()

    # Título Automático
    async def auto_update_title(self):
        if not self.conversation_id: return
        try:
            msgs = await self.get_messages(self.conversation_id)
            user_msgs = [m for m in msgs if m.get("role") == "user"]
            
            # Gera título apenas se tiver mensagens suficientes e título for padrão
            if len(user_msgs) >= 1:
                conv = await self.get_conversation(self.conversation_id)
                if conv.get("title") in ["Nova Conversa", "", None]:
                    # Usa Orchestrator para gerar título
                    try:
                        prompt = f"Gere um título de 3 palavras para esta conversa: {user_msgs[0]['content'][:100]}"
                        async with httpx.AsyncClient(timeout=10.0) as client:
                            # Usa endpoint de geração simples para título
                            resp = await client.post(
                                f"{self.orchestrator_url}/internal/generate",
                                json={"prompt": prompt, "max_tokens": 15}
                            )
                            new_title = resp.json()["generated_text"].strip().replace('"', '')
                            await self.update_conversation(self.conversation_id, title=new_title)
                            self.conversation_title = new_title
                    except:
                        # Fallback simples
                        simple_title = user_msgs[0]['content'][:30] + "..."
                        await self.update_conversation(self.conversation_id, title=simple_title)
                        self.conversation_title = simple_title
        except: pass