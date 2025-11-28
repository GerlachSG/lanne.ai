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
  
  // Reset card style to ensure proper flex layout
  card.style.display = 'flex';
  card.style.flexDirection = 'column';
  card.style.justifyContent = 'center';
  card.style.alignItems = 'center';

  card.innerHTML = `
    <style>
      .login-title {
        font-size: 2.5vw;
        color: #1F203F;
        margin-bottom: 2rem;
        font-weight: 700;
        text-align: center;
        position: relative; /* Override any absolute positioning */
      }
      .login-container {
        width: 100%;
        max-width: 400px;
        display: flex;
        flex-direction: column;
        gap: 1.5rem;
      }
      .input-group {
        display: flex;
        flex-direction: column;
        text-align: left;
      }
      .input-label {
        font-size: 1rem;
        font-weight: 600;
        color: #1F203F;
        margin-bottom: 0.5rem;
        margin-left: 0.5rem;
      }
      .custom-input {
        box-sizing: border-box;
        width: 100%;
        padding: 1rem 1.2rem;
        border-radius: 1rem;
        border: 2px solid #E0E0E0;
        background: #F8F9FA;
        font-size: 1rem;
        color: #1F203F;
        outline: none;
        transition: all 0.3s ease;
        font-family: 'Ubuntu', sans-serif;
      }
      .custom-input:focus {
        border-color: #1F203F;
        background: #FFFFFF;
        box-shadow: 0 4px 12px rgba(31, 32, 63, 0.1);
      }
      .custom-login-btn {
        box-sizing: border-box;
        width: 100%;
        padding: 1rem;
        background-color: #1F203F;
        color: #FFFFFF;
        border: none;
        border-radius: 1rem;
        font-size: 1.1rem;
        font-weight: 600;
        cursor: pointer;
        transition: transform 0.2s, box-shadow 0.2s;
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 0.5rem;
        font-family: 'Ubuntu', sans-serif;
      }
      .custom-login-btn:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 15px rgba(31, 32, 63, 0.2);
        background-color: #2A2C55;
      }
      .custom-login-btn:active {
        transform: translateY(0);
      }
      /* Spinner animation */
      @keyframes spin {
        to { transform: rotate(360deg); }
      }
      .spinner {
        width: 16px;
        height: 16px;
        border: 2px solid #ffffff;
        border-top-color: transparent;
        border-radius: 50%;
        animation: spin 0.8s linear infinite;
      }
    </style>

    <img src="../imagens/seta_vetor.svg" alt="Voltar" id="backButton" class="card-icon" style="cursor: pointer;">
    
    <div class="login-title">Bem-vindo de volta!</div>
    
    <div class="login-container">
      <div class="input-group">
        <label class="input-label" for="username-input">Como podemos te chamar?</label>
        <input type="text" id="username-input" class="custom-input" placeholder="Digite seu nome de usuário" autocomplete="off">
      </div>
      
      <button id="login-btn" class="custom-login-btn">
        <span>Entrar</span>
      </button>
    </div>
  `;

  // Re-attach Back Button Logic
  document.getElementById('backButton').addEventListener('click', function() {
    const card = document.getElementById('card');
    card.classList.remove('show');
    document.getElementById('title').classList.remove('hide');
    document.getElementById('subtitle').classList.remove('hide');
    document.getElementById('showCardBtn').classList.remove('hide');
    document.getElementById('left-title').classList.remove('show');
    document.getElementById('left-title').classList.add('hide');
    
    // Reload to reset state
    setTimeout(() => {
        location.reload();
    }, 500);
  });

  // Login Logic
  const loginBtn = document.getElementById('login-btn');
  const usernameInput = document.getElementById('username-input');
  
  // Auto-focus input
  setTimeout(() => usernameInput.focus(), 100);

  const handleLogin = async () => {
    const username = usernameInput.value.trim();
    
    if (!username) {
      usernameInput.style.borderColor = '#ff4444';
      setTimeout(() => usernameInput.style.borderColor = '#E0E0E0', 2000);
      return;
    }

    loginBtn.disabled = true;
    loginBtn.innerHTML = '<div class="spinner"></div><span>Conectando...</span>';

    try {
      await authService.login(username);
      window.location.href = "chat.html";
    } catch (error) {
      console.error('Erro no login:', error);
      alert('Erro ao fazer login: ' + error.message);
      loginBtn.disabled = false;
      loginBtn.innerHTML = '<span>Entrar</span>';
    }
  };

  loginBtn.addEventListener('click', handleLogin);

  usernameInput.addEventListener('keypress', function(e) {
    if (e.key === 'Enter') {
      handleLogin();
    }
  });
});
