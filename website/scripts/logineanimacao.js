/**
 * Login e Animações - Sistema integrado com backend Lanne AI
 * Substitui Firebase por auth-service local
 */

// Importar AuthService do login.js (deve estar carregado antes)
// const authService já está disponível globalmente

// Adiciona o listener no botão "entrar" para exibir os botões de login
document.querySelector('.card-button').addEventListener('click', function() {
  // Altera o conteúdo do card ao clicar no botão "entrar"
  const card = document.querySelector('.card');
  card.innerHTML = `
    <h5>Bem Vindo!</h5>
    <img src="../imagens/seta_vetor.svg" alt="Icone" id="backButton" class="card-icon">
    <div class="button-wrapper2">
      <input type="text" id="username-input" placeholder="Digite seu nome de usuário" 
             style="padding: 12px; margin: 20px 0; width: 80%; border-radius: 8px; border: 1px solid #ccc; font-size: 16px;">
      <button class="login-button google" id="login-btn">
        <img src="../imagens/google-icon.svg" alt="Login" class="icon">
        Entrar com<span class="bold-text">Lanne AI</span>
      </button>
    </div>
  `;
 // Animação de voltar do card
  document.getElementById('backButton').addEventListener('click', function() {
    document.getElementById('card').classList.toggle('show');
    document.getElementById('title').classList.remove('hide');
    document.getElementById('subtitle').classList.remove('hide');
    document.getElementById('showCardBtn').classList.remove('hide');

    // Oculta o título "Lanne.ai" no lado esquerdo
    document.getElementById('left-title').classList.remove('show');
    document.getElementById('left-title').classList.add('hide');
  });

  // Botão de login com novo sistema
  const loginBtn = document.getElementById('login-btn');
  const usernameInput = document.getElementById('username-input');
  
  loginBtn.addEventListener('click', async function() {
    const username = usernameInput.value.trim();
    
    if (!username) {
      alert('Por favor, digite um nome de usuário');
      return;
    }

    loginBtn.classList.add('active-login');
    loginBtn.disabled = true;
    loginBtn.innerHTML = '<span class="bold-text">Conectando...</span>';

    try {
      // Login usando o novo sistema
      await authService.login(username);
      
      // Redireciona para página de chat de forma relativa
      window.location.href = "chat.html";
      
    } catch (error) {
      console.error('Erro no login:', error);
      alert('Erro ao fazer login: ' + error.message);
      loginBtn.classList.remove('active-login');
      loginBtn.disabled = false;
      loginBtn.innerHTML = 'Entrar com<span class="bold-text">Lanne AI</span>';
    }
  });

  // Permitir login com Enter
  usernameInput.addEventListener('keypress', function(e) {
    if (e.key === 'Enter') {
      loginBtn.click();
    }
  });
});
