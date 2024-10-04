// Função para enviar a mensagem do chat para a API
async function enviarMensagem() {
    const mensagem = document.getElementById("mensagem").value;

    // Verifica se há histórico anterior no localStorage
    let historico = JSON.parse(localStorage.getItem('historico')) || [];

    const response = await fetch('/chat', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            mensagem: mensagem,
            historico: historico // envia o histórico anterior junto
        })
    });

    const data = await response.json();

    // Adiciona a nova resposta ao histórico e armazena no localStorage
    historico.push({ role: 'user', content: mensagem });
    historico.push({ role: 'assistant', content: data.resposta });
    localStorage.setItem('historico', JSON.stringify(historico));

    // Exibe a resposta no chat
    document.getElementById("chat-output").innerHTML += `<p><strong>Você:</strong> ${mensagem}</p>`;
    document.getElementById("chat-output").innerHTML += `<p><strong>Chatbot:</strong> ${data.resposta}</p>`;
}

// Função para carregar o histórico quando o usuário logar novamente
function carregarHistorico() {
    let historico = JSON.parse(localStorage.getItem('historico')) || [];
    let chatOutput = document.getElementById("chat-output");

    // Exibe o histórico no chat
    historico.forEach(mensagem => {
        let userRole = mensagem.role === 'user' ? "Você" : "Chatbot";
        chatOutput.innerHTML += `<p><strong>${userRole}:</strong> ${mensagem.content}</p>`;
    });
}

// Carrega o histórico automaticamente ao abrir a página
window.onload = carregarHistorico;
