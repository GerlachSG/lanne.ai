/**
 * Conversation Service - Gerenciamento de conversas e histórico
 * Integra com conversation-service backend
 * Usa IPs dinâmicos configurados no login
 */

// Funções para obter URLs dinâmicas (definidas em login.js)
// getConversationUrl() e getGatewayUrl()

class ConversationService {
    constructor() {
        this.currentConversationId = null;
        this.conversations = [];
    }

    /**
     * Carrega todas as conversas do usuário
     * @param {string} userId - ID do usuário
     * @returns {Promise<Array>} Lista de conversas
     */
    async loadUserConversations(userId) {
        try {
            const response = await fetch(`${getConversationUrl()}/conversations?user_id=${userId}`);
            
            if (!response.ok) {
                throw new Error('Erro ao carregar conversas');
            }

            this.conversations = await response.json();
            return this.conversations;

        } catch (error) {
            console.error('Erro ao carregar conversas:', error);
            return [];
        }
    }

    /**
     * Cria uma nova conversa
     * @param {string} userId - ID do usuário
     * @param {string} title - Título da conversa (opcional)
     * @returns {Promise<Object>} Conversa criada
     */
    async createConversation(userId, title = 'Nova Conversa') {
        try {
            const response = await fetch(`${getConversationUrl()}/conversations`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    user_id: userId,
                    title: title,
                    description: 'Conversa sobre Debian'
                })
            });

            if (!response.ok) {
                throw new Error('Erro ao criar conversa');
            }

            const conversation = await response.json();
            this.currentConversationId = conversation.id;
            
            // Atualizar lista de conversas
            await this.loadUserConversations(userId);
            
            return conversation;

        } catch (error) {
            console.error('Erro ao criar conversa:', error);
            throw error;
        }
    }

    /**
     * Carrega mensagens de uma conversa
     * @param {string} conversationId - ID da conversa
     * @returns {Promise<Array>} Lista de mensagens
     */
    async loadMessages(conversationId) {
        try {
            const response = await fetch(`${getConversationUrl()}/conversations/${conversationId}/messages`);
            
            if (!response.ok) {
                throw new Error('Erro ao carregar mensagens');
            }

            return await response.json();

        } catch (error) {
            console.error('Erro ao carregar mensagens:', error);
            return [];
        }
    }

    /**
     * Adiciona uma mensagem a uma conversa
     * @param {string} conversationId - ID da conversa
     * @param {string} role - 'user' ou 'assistant'
     * @param {string} content - Conteúdo da mensagem
     * @returns {Promise<Object>} Mensagem adicionada
     */
    async addMessage(conversationId, role, content) {
        try {
            const response = await fetch(`${getConversationUrl()}/conversations/${conversationId}/messages`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    role: role,
                    content: content
                })
            });

            if (!response.ok) {
                throw new Error('Erro ao adicionar mensagem');
            }

            return await response.json();

        } catch (error) {
            console.error('Erro ao adicionar mensagem:', error);
            throw error;
        }
    }

    /**
     * Envia mensagem para o chatbot e recebe resposta
     * @param {string} userMessage - Mensagem do usuário
     * @param {string} userId - ID do usuário
     * @returns {Promise<Object>} Resposta do bot
     */
    async sendChatMessage(userMessage, userId) {
        try {
            // Se não há conversa ativa, criar uma nova
            if (!this.currentConversationId) {
                await this.createConversation(userId, userMessage.substring(0, 50));
            }

            // Adicionar mensagem do usuário ao histórico
            await this.addMessage(this.currentConversationId, 'user', userMessage);

            // Enviar para o gateway
            const response = await fetch(`${getGatewayUrl()}/api/v1/chat`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    text: userMessage,
                    conversation_id: this.currentConversationId,
                    user_id: userId,
                    distro: 'debian'
                })
            });

            if (!response.ok) {
                throw new Error('Erro ao enviar mensagem para o chatbot');
            }

            const botResponse = await response.json();

            // Adicionar resposta do bot ao histórico
            await this.addMessage(this.currentConversationId, 'assistant', botResponse.response);

            return botResponse;

        } catch (error) {
            console.error('Erro ao enviar mensagem:', error);
            throw error;
        }
    }

    /**
     * Deleta uma conversa
     * @param {string} conversationId - ID da conversa
     */
    async deleteConversation(conversationId) {
        try {
            const response = await fetch(`${getConversationUrl()}/conversations/${conversationId}`, {
                method: 'DELETE'
            });

            if (!response.ok) {
                throw new Error('Erro ao deletar conversa');
            }

            // Se era a conversa atual, limpar
            if (this.currentConversationId === conversationId) {
                this.currentConversationId = null;
            }

            return true;

        } catch (error) {
            console.error('Erro ao deletar conversa:', error);
            return false;
        }
    }

    /**
     * Define a conversa atual
     * @param {string} conversationId - ID da conversa
     */
    setCurrentConversation(conversationId) {
        this.currentConversationId = conversationId;
    }

    /**
     * Obtém a conversa atual
     */
    getCurrentConversation() {
        return this.currentConversationId;
    }

    /**
     * Gera título automaticamente para uma conversa
     * @param {string} conversationId - ID da conversa
     */
    async generateTitle(conversationId) {
        try {
            const response = await fetch(`${getConversationUrl()}/conversations/${conversationId}/generate-title`, {
                method: 'POST'
            });

            if (!response.ok) {
                throw new Error('Erro ao gerar título');
            }

            return await response.json();

        } catch (error) {
            console.error('Erro ao gerar título:', error);
            return null;
        }
    }
}

// Exportar instância global
const conversationService = new ConversationService();
