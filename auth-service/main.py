"""
Auth Service - Sistema de Autenticação para Lanne AI
Porta: 8007
MELHORADO: Endpoint /login adicionado, melhor gestão de sessão
"""

from fastapi import FastAPI, HTTPException, status, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, timedelta
import jwt
import logging
from pathlib import Path
import json
import os

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Inicializar FastAPI
app = FastAPI(
    title="Lanne AI Auth Service",
    description="Serviço de autenticação e gerenciamento de usuários",
    version="1.1.0"
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configurações JWT
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "lanne-ai-secret-key-2024-change-in-production")
ALGORITHM = "HS256"
TOKEN_EXPIRE_DAYS = 30

# Arquivo de persistência de usuários
USERS_FILE = Path(__file__).parent / "users.json"


# =============================================================================
# MODELOS PYDANTIC
# =============================================================================

class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=30)
    admin: bool = False

class UserLogin(BaseModel):
    username: str

class UserResponse(BaseModel):
    username: str
    token: str
    user_id: str
    created_at: datetime
    admin: bool

class TokenValidation(BaseModel):
    token: str

class UserInfo(BaseModel):
    username: str
    user_id: str
    admin: bool
    created_at: datetime
    last_seen: Optional[datetime] = None


# =============================================================================
# ARMAZENAMENTO
# =============================================================================

# Usuários ativos em memória
active_users = {}  # {username: last_seen_timestamp}


def load_users() -> dict:
    """Carrega usuários do arquivo JSON"""
    if not USERS_FILE.exists():
        return {}
    
    try:
        with open(USERS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Erro ao carregar usuários: {e}")
        return {}


def save_users(users: dict):
    """Salva usuários no arquivo JSON"""
    try:
        with open(USERS_FILE, 'w', encoding='utf-8') as f:
            json.dump(users, f, indent=2, ensure_ascii=False, default=str)
    except Exception as e:
        logger.error(f"Erro ao salvar usuários: {e}")


# =============================================================================
# FUNÇÕES JWT
# =============================================================================

def create_token(username: str, admin: bool = False) -> str:
    """Cria um token JWT"""
    expire = datetime.utcnow() + timedelta(days=TOKEN_EXPIRE_DAYS)
    payload = {
        "sub": username,
        "admin": admin,
        "exp": expire,
        "iat": datetime.utcnow()
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    return token


def verify_token(token: str) -> Optional[dict]:
    """Verifica e decodifica um token JWT"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        logger.warning("Token expirado")
        return None
    except jwt.JWTError as e:
        logger.warning(f"Token inválido: {e}")
        return None


# =============================================================================
# EVENTOS
# =============================================================================

@app.on_event("startup")
async def startup_event():
    """Inicialização do serviço"""
    logger.info("Auth Service v1.1.0 iniciado")
    logger.info(f"Arquivo de usuários: {USERS_FILE}")
    
    if not USERS_FILE.exists():
        save_users({})
        logger.info("Arquivo de usuários criado")


# =============================================================================
# ENDPOINTS
# =============================================================================

@app.get("/")
async def root():
    """Health check endpoint"""
    users = load_users()
    return {
        "service": "auth-service",
        "status": "running",
        "version": "1.1.0",
        "total_users": len(users),
        "active_users": len(active_users)
    }


@app.post("/register", response_model=UserResponse)
async def register_user(user: UserCreate):
    """
    Registra um novo usuário e retorna um token JWT
    """
    users = load_users()
    
    # Sanitizar username
    username = user.username.strip().lower()
    
    # Verificar se usuário já existe
    if username in users:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Usuário '{username}' já existe. Use /login para conectar."
        )
    
    # Criar token
    token = create_token(username, user.admin)
    
    # Salvar usuário
    users[username] = {
        "username": username,
        "user_id": username,  # Por simplicidade, user_id = username
        "token": token,
        "admin": user.admin,
        "created_at": datetime.utcnow().isoformat()
    }
    save_users(users)
    
    # Marcar como ativo
    active_users[username] = datetime.utcnow()
    
    logger.info(f"Usuário '{username}' registrado com sucesso")
    
    return UserResponse(
        username=username,
        user_id=username,
        token=token,
        created_at=datetime.utcnow(),
        admin=user.admin
    )


@app.post("/login", response_model=UserResponse)
async def login_user(user: UserLogin):
    """
    Login de usuário existente - gera novo token
    """
    users = load_users()
    username = user.username.strip().lower()
    
    # Verificar se usuário existe
    if username not in users:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Usuário '{username}' não encontrado. Use /register para criar."
        )
    
    user_data = users[username]
    
    # Gerar novo token
    is_admin = user_data.get("admin", False)
    new_token = create_token(username, is_admin)
    
    # Atualizar token no armazenamento
    users[username]["token"] = new_token
    users[username]["last_login"] = datetime.utcnow().isoformat()
    save_users(users)
    
    # Marcar como ativo
    active_users[username] = datetime.utcnow()
    
    logger.info(f"Usuário '{username}' logado com sucesso")
    
    return UserResponse(
        username=username,
        user_id=username,
        token=new_token,
        created_at=datetime.fromisoformat(user_data["created_at"]),
        admin=is_admin
    )


@app.post("/validate")
async def validate_token(validation: TokenValidation):
    """
    Valida um token JWT
    """
    payload = verify_token(validation.token)
    
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido ou expirado"
        )
    
    username = payload.get("sub")
    
    # Atualizar last_seen
    active_users[username] = datetime.utcnow()
    
    logger.info(f"Token validado para usuário '{username}'")
    
    return {
        "valid": True,
        "username": username,
        "user_id": username,
        "admin": payload.get("admin", False)
    }


@app.get("/users", response_model=List[UserInfo])
async def list_users():
    """
    Lista todos os usuários registrados
    """
    users = load_users()
    
    user_list = []
    for username, data in users.items():
        user_list.append(UserInfo(
            username=username,
            user_id=username,
            admin=data.get("admin", False),
            created_at=datetime.fromisoformat(data["created_at"]),
            last_seen=active_users.get(username)
        ))
    
    return user_list


@app.get("/users/{username}")
async def get_user(username: str):
    """
    Busca informações de um usuário específico
    """
    users = load_users()
    username = username.lower()
    
    if username not in users:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Usuário '{username}' não encontrado"
        )
    
    data = users[username]
    return {
        "username": username,
        "user_id": username,
        "admin": data.get("admin", False),
        "created_at": data["created_at"],
        "last_seen": active_users.get(username, {})
    }


@app.get("/users/active")
async def list_active_users():
    """
    Lista usuários ativos (conectados nos últimos 5 minutos)
    """
    now = datetime.utcnow()
    threshold = timedelta(minutes=5)
    
    active = []
    for username, last_seen in active_users.items():
        if now - last_seen < threshold:
            active.append({
                "username": username,
                "last_seen": last_seen.isoformat()
            })
    
    return {
        "active_count": len(active),
        "users": active
    }


@app.delete("/users/{username}")
async def delete_user(username: str):
    """
    Remove um usuário do sistema
    """
    users = load_users()
    username = username.lower()
    
    if username not in users:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Usuário '{username}' não encontrado"
        )
    
    del users[username]
    save_users(users)
    
    # Remover de usuários ativos
    if username in active_users:
        del active_users[username]
    
    logger.info(f"Usuário '{username}' removido")
    
    return {"message": f"Usuário '{username}' removido com sucesso"}


@app.post("/logout")
async def logout(validation: TokenValidation):
    """
    Desconecta um usuário (remove de active_users)
    """
    payload = verify_token(validation.token)
    
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido"
        )
    
    username = payload.get("sub")
    
    if username in active_users:
        del active_users[username]
        logger.info(f"Usuário '{username}' desconectado")
    
    return {"message": f"Usuário '{username}' desconectado"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8007)