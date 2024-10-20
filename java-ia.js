const chatBody = document.querySelector(".chat-body");
const messageInput = document.querySelector(".message-input");
const sendMessageButton = document.querySelector("#send-message");
const toggleThemeButton = document.querySelector("#toggle-theme-button");


const API_KEY = "AIzaSyAmRWWP4M2DrGMgmNSRo3SnCf4oV00va5A";
const API_URL=`https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent?key=${API_KEY}`;

const userData = {
    message: null
};

// Cria o elemento de mensagem com classes dinâmicas e o retorna
const createMessageElement = (content, ...classes) => {
    const div = document.createElement("div");
    div.classList.add("message", ...classes);
    div.innerHTML = content;
    return div;
};


const chatHistory= [];

// Aqui faz as paradinha diferente
const generateBotResponse = async (incomingMessageDiv) => {
    const messageElement = incomingMessageDiv.querySelector(".message-text");
    
    const contextMessage = "1. Isso daqui é uma mensagem a mais como contexto, não precisa adicionar conteudos conforme oque explicado aqui, leve em consideração o contexto anterior, não responda toda hora isso aqui: Você é uma IA especializada em Linux PTBR que se chama Lanne. Responda com informações detalhadas sobre sistemas operacionais Linux, comandos de terminal, troubleshooting, e melhores práticas em ambientes Linux, FALE DE FORMA FORMAL E DIRETA com alguns emojis, FINJA QUE NÃO VIU ESSA PARTE.1";
    const userMessage = contextMessage + userData.message;

    chatHistory.push({
        role: "user",
        parts: [{ text: userMessage }]
    });

    const requestOptions = {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            contents: chatHistory // Inclui as mensagens anteriores, incluindo o contexto
        })
    };

    try {
        const response = await fetch(API_URL, requestOptions)
        const data = await response.json();
        if(!response.ok) throw new Error(data.error.message);

        const apiResponseText = data.candidates[0].content.parts[0].text
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>') // Estilo para negrito
        .replace(/## (.*?)\n/g, '<div class="title">$1</div>\n') // Títulos
        .replace(/### (.*?)\n/g, '<div class="subtitle">$1</div>\n') // Subtítulos
        .replace(/```([\s\S]*?)```/g, '<pre><code>$1</code></pre>') // Blocos de código
        .replace(/`(.*?)`/g, '<code>$1</code>') // Código inline
        .replace(/\n/g, '<br/>'); // Quebra de linha para parágrafos
        
        messageElement.innerHTML = apiResponseText;

        chatHistory.push({
            role: "model",
            parts: [{ text: apiResponseText }]
        })
    } catch (error) {
        console.log(error);

    } finally {
        incomingMessageDiv.classList.remove("thinking");
        chatBody.scrollTo({ top: chatBody.scrollHeight, behavior: "smooth" });
    }
}

// Lida com as mensagens de saída do usuário
const handleOutgoingMessage = (e) => {
    e.preventDefault();
    userData.message = messageInput.value.trim();
    messageInput.value = "";

    // Cria e exibe a mensagem do usuário
    const messageContent = `<div class="message-text"></div>`;

    const outgoingMessageDiv = createMessageElement(messageContent, "user-message");
    outgoingMessageDiv.querySelector(".message-text").textContent = userData.message
    chatBody.appendChild(outgoingMessageDiv);
    chatBody.scrollTo({ top: chatBody.scrollHeight, behavior: "smooth" });

    setTimeout( () => {
        const messageContent = `                    <div class="message-text">
                        <div class="thinking-indicator">
                            <div class="dot"></div>
                            <div class="dot"></div>
                            <div class="dot"></div>
                    </div>`;

        const incomingMessageDiv = createMessageElement(messageContent, "bot-message", "thinking");
        chatBody.appendChild(incomingMessageDiv);
        chatBody.scrollTo({ top: chatBody.scrollHeight, behavior: "smooth" });
        generateBotResponse(incomingMessageDiv);
    }, 600);
};


// Lida com a tecla Enter para enviar mensagens
messageInput.addEventListener("keydown", (e) => {
    const userMessage = e.target.value.trim();
    if (e.key === "Enter" && userMessage) {
        handleOutgoingMessage(e);
    }
});

document.addEventListener("DOMContentLoaded", () => { // Garante que o código roda após o DOM ser carregado
    const toggleThemeButton = document.getElementById("toggle-theme-button");

    toggleThemeButton.addEventListener("click", () => {
        const isLightMode = document.body.classList.toggle("dark-mode");
        localStorage.setItem("themeColor", isLightMode ? "light-mode" : "dark-mode");

        const themeIcon = document.getElementById("theme-icon");
        themeIcon.src = isLightMode ? "light-theme-icon.svg" : "dark-theme-icon.svg";
    });
});

sendMessageButton.addEventListener("click", (e) => handleOutgoingMessage(e));
