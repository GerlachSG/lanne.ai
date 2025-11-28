/**
 * Chat Integration - Integração completa com backend Lanne AI
 * Substitui java-ia.js com suporte a conversation-service e gateway-service
 */

const chatBody = document.querySelector(".chat-body");
const messageInput = document.querySelector(".message-input");
const sendMessageButton = document.querySelector("#send-message");
const toggleThemeButton = document.querySelector("#toggle-theme-button");
const chatList = document.querySelector(".chat-list");
const plusButton = document.querySelector(".sidebar-button.plus");

// Estado global
let isWaitingForResponse = false;

/**
 * Cria elemento de mensagem
 */
const createMessageElement = (content, ...classes) => {
    const div = document.createElement("div");
    div.classList.add("message", ...classes);
    div.innerHTML = content;
    return div;
};

/**
 * Formata resposta do bot com markdown
 */
const formatBotResponse = (text) => {
    return text
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/## (.*?)\n/g, '<div class="title">$1</div>\n')
        .replace(/### (.*?)\n/g, '<div class="subtitle">$1</div>\n')
        .replace(/```([\s\S]*?)```/g, '<pre><code>$1</code></pre>')
        .replace(/`(.*?)`/g, '<code>$1</code>')
        .replace(/\n/g, '<br/>');
};

/**
 * Gera resposta do bot usando o backend
 */
const generateBotResponse = async (incomingMessageDiv, userMessage) => {
    const messageElement = incomingMessageDiv.querySelector(".message-text");
    
    try {
        const user = authService.getCurrentUser();
        if (!user) {
            throw new Error('Usuário não autenticado');
        }

        // Enviar mensagem através do conversation service
        const response = await conversationService.sendChatMessage(userMessage, user.user_id);
        
        // Formatar e exibir resposta
        const formattedResponse = formatBotResponse(response.response);
        messageElement.innerHTML = formattedResponse;

        // Badge simples para identificar modo leve/fallback
        const isFallback = response?.metadata?.fallback || response?.metadata?.route === 'direct_inference';
        if (isFallback) {
            const badge = document.createElement('div');
            badge.textContent = 'Modo leve';
            badge.title = 'Resposta gerada sem o pipeline completo (orchestrator/RAG)';
            badge.style.cssText = [
                'display:block',
                'width:max-content',
                'margin:0 0 6px 0',
                'padding:2px 8px',
                'border-radius:10px',
                'background:#FFD54F',
                'color:#222',
                'font-size:11px',
                'font-weight:700',
                'text-align:left'
            ].join(';');
            // Inserir o badge no topo da mensagem do bot (acima do texto), alinhado à esquerda
            incomingMessageDiv.insertBefore(badge, incomingMessageDiv.firstChild);
        }

        // Atualizar lista de conversas
        await loadConversationHistory();

    } catch (error) {
        console.error('Erro ao gerar resposta:', error);
        messageElement.innerHTML = '❌ Erro ao processar mensagem. Verifique se os serviços estão rodando.';
    } finally {
        incomingMessageDiv.classList.remove("thinking");
        chatBody.scrollTo({ top: chatBody.scrollHeight, behavior: "smooth" });
        isWaitingForResponse = false;
    }
};

/**
 * Lida com mensagens enviadas pelo usuário
 */
const handleOutgoingMessage = (e) => {
    e.preventDefault();
    
    if (isWaitingForResponse) return;
    
    const userMessage = messageInput.value.trim();
    if (!userMessage) return;

    messageInput.value = "";
    isWaitingForResponse = true;

    // Exibir mensagem do usuário
    const messageContent = `<div class="message-text"></div>`;
    const outgoingMessageDiv = createMessageElement(messageContent, "user-message");
    outgoingMessageDiv.querySelector(".message-text").textContent = userMessage;
    chatBody.appendChild(outgoingMessageDiv);
    chatBody.scrollTo({ top: chatBody.scrollHeight, behavior: "smooth" });

    // Exibir indicador de "pensando"
    setTimeout(() => {
        const thinkingContent = `
            <div class="message-text">
                <div class="thinking-indicator">
                    <div class="dot"></div>
                    <div class="dot"></div>
                    <div class="dot"></div>
                </div>
            </div>`;

        const incomingMessageDiv = createMessageElement(thinkingContent, "bot-message", "thinking");
        chatBody.appendChild(incomingMessageDiv);
        chatBody.scrollTo({ top: chatBody.scrollHeight, behavior: "smooth" });
        
        generateBotResponse(incomingMessageDiv, userMessage);
    }, 600);
};

/**
 * Carrega histórico de conversas do usuário
 */
const loadConversationHistory = async () => {
    try {
        const user = authService.getCurrentUser();
        if (!user) return;

        const conversations = await conversationService.loadUserConversations(user.user_id);
        
        // Limpar lista atual
        chatList.innerHTML = '';

        // Se não há conversas, mostrar mensagem
        if (conversations.length === 0) {
            chatList.innerHTML = '<p style="text-align: center; color: var(--item-color); padding: 20px;">Nenhuma conversa ainda. Comece uma nova!</p>';
            return;
        }

        // Renderizar conversas (apenas para Debian)
        conversations.forEach((conv, index) => {
            const colors = ['blue', 'green', 'orange', 'red'];
            const color = colors[index % colors.length];
            
            // Calcular tempo desde criação
            const createdDate = new Date(conv.created_at);
            const now = new Date();
            const diffDays = Math.floor((now - createdDate) / (1000 * 60 * 60 * 24));
            const timeStr = diffDays === 0 ? 'hoje' : `${diffDays}d`;

            const chatItem = document.createElement('div');
            chatItem.className = `chat-item ${color}`;
            chatItem.innerHTML = `
                <img src="../imagens/ubuntu.svg" alt="Debian Icon" style="position: absolute; top: 10px; left: -24px;">
                <h2>${conv.title}</h2>
                <p>${conv.description || `${conv.message_count} mensagens`}</p>
                <span class="date">${timeStr}</span>
            `;

            // Clicar para carregar conversa
            chatItem.addEventListener('click', () => loadConversation(conv.id));
            
            chatList.appendChild(chatItem);
        });

    } catch (error) {
        console.error('Erro ao carregar histórico:', error);
        chatList.innerHTML = '<p style="text-align: center; color: red; padding: 20px;">Erro ao carregar conversas</p>';
    }
};

/**
 * Carrega mensagens de uma conversa específica
 */
const loadConversation = async (conversationId) => {
    try {
        conversationService.setCurrentConversation(conversationId);
        
        const messages = await conversationService.loadMessages(conversationId);
        
        // Limpar chat atual
        chatBody.innerHTML = '';

        // Renderizar mensagens
        messages.forEach(msg => {
            const isUser = msg.role === 'user';
            const messageContent = `<div class="message-text"></div>`;
            const messageDiv = createMessageElement(
                messageContent, 
                isUser ? "user-message" : "bot-message"
            );
            
            if (isUser) {
                messageDiv.querySelector(".message-text").textContent = msg.content;
            } else {
                messageDiv.querySelector(".message-text").innerHTML = formatBotResponse(msg.content);
            }
            
            chatBody.appendChild(messageDiv);
        });

        chatBody.scrollTo({ top: chatBody.scrollHeight, behavior: "smooth" });

    } catch (error) {
        console.error('Erro ao carregar conversa:', error);
    }
};

/**
 * Cria nova conversa
 */
const createNewConversation = async () => {
    try {
        const user = authService.getCurrentUser();
        if (!user) return;

        // Limpar conversa atual
        conversationService.setCurrentConversation(null);
        
        // Limpar chat
        chatBody.innerHTML = `
            <div class="message bot-message">
                <div class="message-text">Olá! Como posso te ajudar hoje?</div>
            </div>
        `;

        // Atualizar lista
        await loadConversationHistory();

    } catch (error) {
        console.error('Erro ao criar nova conversa:', error);
    }
};

/**
 * Configura tema escuro/claro
 */
const setupThemeToggle = () => {
    toggleThemeButton.addEventListener("click", () => {
        const isLightMode = document.body.classList.toggle("dark-mode");
        localStorage.setItem("themeColor", isLightMode ? "light-mode" : "dark-mode");

        const themeIcon = document.getElementById("theme-icon");
        themeIcon.src = isLightMode ? "../imagens/light-theme-icon.svg" : "../imagens/dark-theme-icon.svg";
    });

    // Carregar tema salvo
    const savedTheme = localStorage.getItem("themeColor");
    if (savedTheme === "light-mode") {
        document.body.classList.add("dark-mode");
        document.getElementById("theme-icon").src = "../imagens/light-theme-icon.svg";
    }
};

/**
 * Configura foto de perfil
 */
const setupUserProfile = () => {
    const user = authService.getCurrentUser();
    if (user) {
        const profilePicture = document.getElementById("userProfilePicture");
        if (profilePicture) {
            // Usar primeira letra do username como avatar
            const letter = user.username.charAt(0).toUpperCase();
            profilePicture.src = `https://ui-avatars.com/api/?name=${letter}&background=1D2142&color=fff&size=128`;
            profilePicture.alt = user.username;
        }
    }
};

/**
 * Inicialização
 */
document.addEventListener("DOMContentLoaded", async () => {
    // Verificar autenticação
    if (!authService.isAuthenticated()) {
        window.location.href = 'index.html';
        return;
    }

    // Configurar tema
    setupThemeToggle();

    // Configurar perfil
    setupUserProfile();

    // Carregar histórico de conversas
    await loadConversationHistory();

    // Event listeners
    sendMessageButton.addEventListener("click", handleOutgoingMessage);
    
    messageInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter" && !e.shiftKey && messageInput.value.trim()) {
            handleOutgoingMessage(e);
        }
    });

    plusButton.addEventListener("click", createNewConversation);

    console.log('Chat integrado carregado com sucesso');
});
