/**
 * Login Service - Sistema de autenticação integrado com backend
 * Substitui Firebase por auth-service local
 */

// Configurações de IP (podem ser alteradas no login)
let SERVER_IP = localStorage.getItem('lanne_server_ip') || 'localhost';
let AGENT_IP = localStorage.getItem('lanne_agent_ip') || 'localhost';

// URLs dos serviços (atualizadas dinamicamente)
function getAuthUrl() {
    return `http://${SERVER_IP}:8007`;
}

function getGatewayUrl() {
    return `http://${SERVER_IP}:8000`;
}

function getConversationUrl() {
    return `http://${SERVER_IP}:8006`;
}

function getOrchestratorUrl() {
    return `http://${SERVER_IP}:8001`;
}

function getAgentUrl() {
    return `http://${AGENT_IP}:9000`;
}

// Função para atualizar IPs
function setServerIP(ip) {
    SERVER_IP = ip || 'localhost';
    localStorage.setItem('lanne_server_ip', SERVER_IP);
}

function setAgentIP(ip) {
    AGENT_IP = ip || 'localhost';
    localStorage.setItem('lanne_agent_ip', AGENT_IP);
}

function getServerIP() {
    return SERVER_IP;
}

function getAgentIP() {
    return AGENT_IP;
}

class AuthService {
    constructor() {
        this.currentUser = null;
        this.token = null;
        this.loadSession();
    }

    /**
     * Carrega sessão do localStorage
     */
    loadSession() {
        const savedUser = localStorage.getItem('lanne_user');
        const savedToken = localStorage.getItem('lanne_token');
        
        if (savedUser && savedToken) {
            this.currentUser = JSON.parse(savedUser);
            this.token = savedToken;
        }
    }

    /**
     * Salva sessão no localStorage
     */
    saveSession(user, token) {
        localStorage.setItem('lanne_user', JSON.stringify(user));
        localStorage.setItem('lanne_token', token);
        this.currentUser = user;
        this.token = token;
    }

    /**
     * Remove sessão do localStorage
     */
    clearSession() {
        localStorage.removeItem('lanne_user');
        localStorage.removeItem('lanne_token');
        this.currentUser = null;
        this.token = null;
    }

    /**
     * Login do usuário (cria conta se não existir)
     * @param {string} username - Nome de usuário
     * @returns {Promise<Object>} Dados do usuário
     */
    async login(username) {
        const API_BASE_URL = getAuthUrl();
        try {
            // Primeiro, tenta fazer login
            let response = await fetch(`${API_BASE_URL}/login`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ username: username.toLowerCase().trim() })
            });

            // Se usuário não existe, registra automaticamente
            if (response.status === 404) {
                console.log('Usuário não encontrado, registrando...');
                response = await fetch(`${API_BASE_URL}/register`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ 
                        username: username.toLowerCase().trim(),
                        admin: false
                    })
                });
            }

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Erro ao fazer login');
            }

            const userData = await response.json();
            
            // Salvar sessão
            this.saveSession({
                username: userData.username,
                user_id: userData.user_id,
                admin: userData.admin
            }, userData.token);

            console.log('Login bem-sucedido:', userData.username);
            return userData;

        } catch (error) {
            console.error('Erro no login:', error);
            throw error;
        }
    }

    /**
     * Logout do usuário
     */
    async logout() {
        const API_BASE_URL = getAuthUrl();
        try {
            if (this.token) {
                await fetch(`${API_BASE_URL}/logout`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ token: this.token })
                });
            }
        } catch (error) {
            console.error('Erro ao fazer logout:', error);
        } finally {
            this.clearSession();
        }
    }

    /**
     * Valida token atual
     * @returns {Promise<boolean>} True se válido
     */
    async validateToken() {
        if (!this.token) return false;
        const API_BASE_URL = getAuthUrl();

        try {
            const response = await fetch(`${API_BASE_URL}/validate`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ token: this.token })
            });

            return response.ok;
        } catch (error) {
            console.error('Erro ao validar token:', error);
            return false;
        }
    }

    /**
     * Obtém usuário atual
     */
    getCurrentUser() {
        return this.currentUser;
    }

    /**
     * Obtém token atual
     */
    getToken() {
        return this.token;
    }

    /**
     * Verifica se usuário está autenticado
     */
    isAuthenticated() {
        return this.currentUser !== null && this.token !== null;
    }
}

// Exportar instância global
const authService = new AuthService();

// Verificar autenticação ao carregar a página
window.addEventListener('DOMContentLoaded', async () => {
    // Se estiver em chat.html, verificar se está autenticado
    if (window.location.pathname.includes('chat.html')) {
        if (!authService.isAuthenticated()) {
            console.log('Usuário não autenticado, redirecionando...');
            window.location.href = 'index.html';
            return;
        }

        // Validar token
        const isValid = await authService.validateToken();
        if (!isValid) {
            console.log('Token inválido, redirecionando...');
            authService.clearSession();
            window.location.href = 'index.html';
        }
    }
});
