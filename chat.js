// 1. Seleção de elementos HTML
const messageInput = document.getElementById("message-input");
const sendButton = document.getElementById("send-button");
const chatContainer = document.getElementById("chat-container");

// 2. Função para enviar mensagem
async function sendMessage() {
    const message = messageInput.value.trim();
    if (!message) return; // Verifica se há uma mensagem

    try {
        const response = await fetch("/api/send_message", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ message })
        });
        const data = await response.json();

        // 3. Atualiza a interface com a resposta
        addMessageToChat("User", message);
        addMessageToChat("Bot", data.response);
        messageInput.value = ""; // Limpa o campo de entrada
    } catch (error) {
        console.error("Erro ao enviar mensagem:", error);
    }
}

// 4. Adiciona mensagens ao chat
function addMessageToChat(sender, text) {
    const messageElement = document.createElement("div");
    messageElement.classList.add("message", sender.toLowerCase());
    messageElement.innerText = `${sender}: ${text}`;
    chatContainer.appendChild(messageElement);
}

// 5. Configurações de eventos
sendButton.addEventListener("click", sendMessage);
messageInput.addEventListener("keypress", (event) => {
    if (event.key === "Enter") {
        sendMessage();
    }
});
