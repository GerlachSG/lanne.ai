/**
 * Login e Animações - Sistema integrado com backend Lanne AI
 * Wizard de login com configuração de IP do Servidor e Agente
 */

// Importar AuthService do login.js (deve estar carregado antes)
// const authService já está disponível globalmente

// Estado do wizard
let wizardStep = 1;
let wizardData = {
  username: '',
  serverType: 'localhost',
  serverIP: localStorage.getItem('lanne_server_ip') || '',
  agentType: 'localhost', 
  agentIP: localStorage.getItem('lanne_agent_ip') || ''
};

// Adiciona o listener no botão "entrar" para exibir os botões de login
document.querySelector('.card-button').addEventListener('click', function() {
  wizardStep = 1;
  renderWizardStep();
});

function renderWizardStep() {
  const card = document.querySelector('.card');
  
  // Reset card style
  card.style.display = 'flex';
  card.style.flexDirection = 'column';
  card.style.justifyContent = 'center';
  card.style.alignItems = 'center';

  const baseStyles = `
    <style>
      .login-title {
        font-size: 2.2vw;
        color: #1F203F;
        margin-bottom: 1.5rem;
        font-weight: 700;
        text-align: center;
      }
      .step-indicator {
        display: flex;
        justify-content: center;
        gap: 0.5rem;
        margin-bottom: 1.5rem;
      }
      .step-dot {
        width: 12px;
        height: 12px;
        border-radius: 50%;
        background: #E0E0E0;
        transition: all 0.3s ease;
      }
      .step-dot.active {
        background: #1F203F;
        transform: scale(1.2);
      }
      .step-dot.completed {
        background: #4CAF50;
      }
      .login-container {
        width: 100%;
        max-width: 450px;
        display: flex;
        flex-direction: column;
        gap: 1.2rem;
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
      .custom-input:disabled {
        background: #E8E8E8;
        color: #888;
      }
      .radio-group {
        display: flex;
        gap: 1rem;
        margin-bottom: 0.5rem;
      }
      .radio-option {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        padding: 0.8rem 1.2rem;
        border: 2px solid #E0E0E0;
        border-radius: 0.8rem;
        cursor: pointer;
        transition: all 0.3s ease;
        flex: 1;
        justify-content: center;
      }
      .radio-option:hover {
        border-color: #1F203F;
      }
      .radio-option.selected {
        border-color: #1F203F;
        background: #F0F0FF;
      }
      .radio-option input {
        display: none;
      }
      .button-row {
        display: flex;
        gap: 1rem;
        margin-top: 1rem;
      }
      .custom-btn {
        box-sizing: border-box;
        flex: 1;
        padding: 1rem;
        border: none;
        border-radius: 1rem;
        font-size: 1rem;
        font-weight: 600;
        cursor: pointer;
        transition: transform 0.2s, box-shadow 0.2s;
        font-family: 'Ubuntu', sans-serif;
      }
      .btn-primary {
        background-color: #1F203F;
        color: #FFFFFF;
      }
      .btn-primary:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 15px rgba(31, 32, 63, 0.2);
        background-color: #2A2C55;
      }
      .btn-secondary {
        background-color: #E0E0E0;
        color: #1F203F;
      }
      .btn-secondary:hover {
        background-color: #D0D0D0;
      }
      .btn-success {
        background-color: #4CAF50;
        color: #FFFFFF;
      }
      .btn-success:hover {
        background-color: #45a049;
      }
      .summary-box {
        background: #F8F9FA;
        border: 2px solid #E0E0E0;
        border-radius: 1rem;
        padding: 1.5rem;
        text-align: left;
      }
      .summary-item {
        margin-bottom: 1rem;
      }
      .summary-item:last-child {
        margin-bottom: 0;
      }
      .summary-label {
        font-size: 0.85rem;
        color: #666;
        margin-bottom: 0.2rem;
      }
      .summary-value {
        font-size: 1.1rem;
        color: #1F203F;
        font-weight: 600;
      }
      .status-message {
        text-align: center;
        padding: 0.8rem;
        border-radius: 0.5rem;
        font-weight: 500;
        display: none;
      }
      .status-error {
        display: block;
        background: #ffebee;
        color: #c62828;
      }
      .status-success {
        display: block;
        background: #e8f5e9;
        color: #2e7d32;
      }
      .status-warning {
        display: block;
        background: #fff3e0;
        color: #ef6c00;
      }
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
        display: inline-block;
        margin-right: 0.5rem;
      }
      .ip-input-section {
        margin-top: 0.5rem;
        display: none;
      }
      .ip-input-section.visible {
        display: block;
      }
    </style>
  `;

  let stepContent = '';
  
  if (wizardStep === 1) {
    stepContent = renderStep1();
  } else if (wizardStep === 2) {
    stepContent = renderStep2();
  } else if (wizardStep === 3) {
    stepContent = renderStep3();
  } else if (wizardStep === 4) {
    stepContent = renderStep4();
  }

  card.innerHTML = `
    ${baseStyles}
    <img src="../imagens/seta_vetor.svg" alt="Voltar" id="backButton" class="card-icon" style="cursor: pointer;">
    
    <div class="step-indicator">
      <div class="step-dot ${wizardStep >= 1 ? (wizardStep > 1 ? 'completed' : 'active') : ''}"></div>
      <div class="step-dot ${wizardStep >= 2 ? (wizardStep > 2 ? 'completed' : 'active') : ''}"></div>
      <div class="step-dot ${wizardStep >= 3 ? (wizardStep > 3 ? 'completed' : 'active') : ''}"></div>
      <div class="step-dot ${wizardStep >= 4 ? 'active' : ''}"></div>
    </div>
    
    ${stepContent}
    
    <div id="status-message" class="status-message"></div>
  `;

  attachEventListeners();
}

function renderStep1() {
  return `
    <div class="login-title">Como podemos te chamar?</div>
    <div class="login-container">
      <div class="input-group">
        <label class="input-label">Nome de Usuário</label>
        <input type="text" id="username-input" class="custom-input" 
               placeholder="Digite seu nome de usuário" 
               value="${wizardData.username}" autocomplete="off">
      </div>
      <div class="button-row">
        <button id="next-btn" class="custom-btn btn-primary">Proximo</button>
      </div>
    </div>
  `;
}

function renderStep2() {
  return `
    <div class="login-title">IP do Servidor (Backend)</div>
    <div class="login-container">
      <div class="input-group">
        <label class="input-label">Onde está o servidor da IA?</label>
        <div class="radio-group">
          <label class="radio-option ${wizardData.serverType === 'localhost' ? 'selected' : ''}" id="server-localhost">
            <input type="radio" name="server-type" value="localhost" ${wizardData.serverType === 'localhost' ? 'checked' : ''}>
            Este PC (localhost)
          </label>
          <label class="radio-option ${wizardData.serverType === 'remote' ? 'selected' : ''}" id="server-remote">
            <input type="radio" name="server-type" value="remote" ${wizardData.serverType === 'remote' ? 'checked' : ''}>
            Outro PC (IP)
          </label>
        </div>
      </div>
      <div class="input-group ip-input-section ${wizardData.serverType === 'remote' ? 'visible' : ''}" id="server-ip-section">
        <label class="input-label">IP do Servidor</label>
        <input type="text" id="server-ip-input" class="custom-input" 
               placeholder="Ex: 192.168.1.100" 
               value="${wizardData.serverIP}">
      </div>
      <div class="button-row">
        <button id="back-btn" class="custom-btn btn-secondary">Voltar</button>
        <button id="next-btn" class="custom-btn btn-primary">Proximo</button>
      </div>
    </div>
  `;
}

function renderStep3() {
  return `
    <div class="login-title">IP do Agente Linux</div>
    <div class="login-container">
      <div class="input-group">
        <label class="input-label">Onde está o Agente Linux?</label>
        <div class="radio-group">
          <label class="radio-option ${wizardData.agentType === 'localhost' ? 'selected' : ''}" id="agent-localhost">
            <input type="radio" name="agent-type" value="localhost" ${wizardData.agentType === 'localhost' ? 'checked' : ''}>
            Este PC (localhost)
          </label>
          <label class="radio-option ${wizardData.agentType === 'remote' ? 'selected' : ''}" id="agent-remote">
            <input type="radio" name="agent-type" value="remote" ${wizardData.agentType === 'remote' ? 'checked' : ''}>
            Outro PC (IP)
          </label>
        </div>
      </div>
      <div class="input-group ip-input-section ${wizardData.agentType === 'remote' ? 'visible' : ''}" id="agent-ip-section">
        <label class="input-label">IP do Agente</label>
        <input type="text" id="agent-ip-input" class="custom-input" 
               placeholder="Ex: 172.17.1.1" 
               value="${wizardData.agentIP}">
      </div>
      <div class="button-row">
        <button id="back-btn" class="custom-btn btn-secondary">Voltar</button>
        <button id="next-btn" class="custom-btn btn-primary">Proximo</button>
      </div>
    </div>
  `;
}

function renderStep4() {
  const serverDisplay = wizardData.serverType === 'localhost' ? 'localhost' : wizardData.serverIP;
  const agentDisplay = wizardData.agentType === 'localhost' ? 'localhost' : wizardData.agentIP;
  
  return `
    <div class="login-title">Confirmar Configuracao</div>
    <div class="login-container">
      <div class="summary-box">
        <div class="summary-item">
          <div class="summary-label">Usuario</div>
          <div class="summary-value">${wizardData.username}</div>
        </div>
        <div class="summary-item">
          <div class="summary-label">Servidor (Backend)</div>
          <div class="summary-value">${serverDisplay}:8000</div>
        </div>
        <div class="summary-item">
          <div class="summary-label">Agente Linux</div>
          <div class="summary-value">${agentDisplay}:9000</div>
        </div>
      </div>
      <div class="button-row">
        <button id="back-btn" class="custom-btn btn-secondary">Voltar</button>
        <button id="connect-btn" class="custom-btn btn-success">Conectar</button>
      </div>
    </div>
  `;
}

function attachEventListeners() {
  // Botão voltar para o card inicial
  document.getElementById('backButton').addEventListener('click', function() {
    if (wizardStep > 1) {
      wizardStep--;
      renderWizardStep();
    } else {
      const card = document.getElementById('card');
      card.classList.remove('show');
      document.getElementById('title').classList.remove('hide');
      document.getElementById('subtitle').classList.remove('hide');
      document.getElementById('showCardBtn').classList.remove('hide');
      document.getElementById('left-title').classList.remove('show');
      document.getElementById('left-title').classList.add('hide');
      setTimeout(() => location.reload(), 500);
    }
  });

  // Botão voltar do wizard
  const backBtn = document.getElementById('back-btn');
  if (backBtn) {
    backBtn.addEventListener('click', () => {
      wizardStep--;
      renderWizardStep();
    });
  }

  // Botão próximo
  const nextBtn = document.getElementById('next-btn');
  if (nextBtn) {
    nextBtn.addEventListener('click', handleNext);
  }

  // Botão conectar
  const connectBtn = document.getElementById('connect-btn');
  if (connectBtn) {
    connectBtn.addEventListener('click', handleConnect);
  }

  // Radio buttons do servidor
  const serverLocalhost = document.getElementById('server-localhost');
  const serverRemote = document.getElementById('server-remote');
  if (serverLocalhost && serverRemote) {
    serverLocalhost.addEventListener('click', () => {
      wizardData.serverType = 'localhost';
      serverLocalhost.classList.add('selected');
      serverRemote.classList.remove('selected');
      document.getElementById('server-ip-section').classList.remove('visible');
    });
    serverRemote.addEventListener('click', () => {
      wizardData.serverType = 'remote';
      serverRemote.classList.add('selected');
      serverLocalhost.classList.remove('selected');
      document.getElementById('server-ip-section').classList.add('visible');
      setTimeout(() => document.getElementById('server-ip-input').focus(), 100);
    });
  }

  // Radio buttons do agente
  const agentLocalhost = document.getElementById('agent-localhost');
  const agentRemote = document.getElementById('agent-remote');
  if (agentLocalhost && agentRemote) {
    agentLocalhost.addEventListener('click', () => {
      wizardData.agentType = 'localhost';
      agentLocalhost.classList.add('selected');
      agentRemote.classList.remove('selected');
      document.getElementById('agent-ip-section').classList.remove('visible');
    });
    agentRemote.addEventListener('click', () => {
      wizardData.agentType = 'remote';
      agentRemote.classList.add('selected');
      agentLocalhost.classList.remove('selected');
      document.getElementById('agent-ip-section').classList.add('visible');
      setTimeout(() => document.getElementById('agent-ip-input').focus(), 100);
    });
  }

  // Auto-focus no input
  const usernameInput = document.getElementById('username-input');
  if (usernameInput) {
    setTimeout(() => usernameInput.focus(), 100);
    usernameInput.addEventListener('keypress', (e) => {
      if (e.key === 'Enter') handleNext();
    });
  }

  const serverIpInput = document.getElementById('server-ip-input');
  if (serverIpInput) {
    serverIpInput.addEventListener('keypress', (e) => {
      if (e.key === 'Enter') handleNext();
    });
  }

  const agentIpInput = document.getElementById('agent-ip-input');
  if (agentIpInput) {
    agentIpInput.addEventListener('keypress', (e) => {
      if (e.key === 'Enter') handleNext();
    });
  }
}

function showStatus(message, type) {
  const statusEl = document.getElementById('status-message');
  if (statusEl) {
    statusEl.textContent = message;
    statusEl.className = 'status-message';
    if (type) statusEl.classList.add(`status-${type}`);
  }
}

function handleNext() {
  if (wizardStep === 1) {
    const usernameInput = document.getElementById('username-input');
    const username = usernameInput.value.trim();
    
    if (!username) {
      showStatus('Digite um nome de usuário!', 'error');
      usernameInput.style.borderColor = '#ff4444';
      return;
    }
    if (username.length < 3) {
      showStatus('O nome deve ter pelo menos 3 caracteres!', 'error');
      return;
    }
    
    wizardData.username = username;
    wizardStep = 2;
    renderWizardStep();
    
  } else if (wizardStep === 2) {
    if (wizardData.serverType === 'remote') {
      const serverIP = document.getElementById('server-ip-input').value.trim();
      if (!serverIP) {
        showStatus('Digite o IP do servidor!', 'error');
        return;
      }
      wizardData.serverIP = serverIP;
    }
    wizardStep = 3;
    renderWizardStep();
    
  } else if (wizardStep === 3) {
    if (wizardData.agentType === 'remote') {
      const agentIP = document.getElementById('agent-ip-input').value.trim();
      if (!agentIP) {
        showStatus('Digite o IP do agente!', 'error');
        return;
      }
      wizardData.agentIP = agentIP;
    }
    wizardStep = 4;
    renderWizardStep();
  }
}

async function handleConnect() {
  const connectBtn = document.getElementById('connect-btn');
  connectBtn.disabled = true;
  connectBtn.innerHTML = '<span class="spinner"></span> Conectando...';
  
  // Configurar IPs
  const serverIP = wizardData.serverType === 'localhost' ? 'localhost' : wizardData.serverIP;
  const agentIP = wizardData.agentType === 'localhost' ? 'localhost' : wizardData.agentIP;
  
  setServerIP(serverIP);
  setAgentIP(agentIP);
  
  showStatus('Testando conexão com o servidor...', 'warning');
  
  try {
    // Testar conexão com o backend
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 5000);
    
    const testResponse = await fetch(`${getGatewayUrl()}/`, { 
      method: 'GET',
      signal: controller.signal
    });
    clearTimeout(timeoutId);
    
    if (!testResponse.ok) {
      throw new Error('Servidor não respondeu corretamente');
    }
    
    showStatus('Servidor conectado! Fazendo login...', 'success');
    
    // Fazer login
    await authService.login(wizardData.username);
    
    // Configurar agente no orchestrator
    showStatus('Configurando agente...', 'warning');
    try {
      const agentController = new AbortController();
      const agentTimeoutId = setTimeout(() => agentController.abort(), 5000);
      
      await fetch(`${getOrchestratorUrl()}/internal/configure-agent`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          agent_url: getAgentUrl(),
          enabled: true
        }),
        signal: agentController.signal
      });
      clearTimeout(agentTimeoutId);
      showStatus('Agente configurado!', 'success');
    } catch (agentError) {
      console.warn('Agente não disponível:', agentError);
      showStatus('Conectado! (Agente não disponível)', 'warning');
    }
    
    // Redirecionar para o chat
    setTimeout(() => {
      window.location.href = "chat.html";
    }, 1000);
    
  } catch (error) {
    console.error('Erro na conexão:', error);
    showStatus('Erro: ' + (error.message || 'Não foi possível conectar'), 'error');
    connectBtn.disabled = false;
    connectBtn.innerHTML = '🔗 Conectar';
  }
}
