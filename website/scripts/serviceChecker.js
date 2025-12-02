/**
 * Service Checker - Verifica se os serviços backend estão rodando
 * Mostra aviso amigável se não estiverem disponíveis
 */

const REQUIRED_SERVICES = [
    { name: 'Auth Service', url: 'http://localhost:8007/', port: 8007 },
    { name: 'Conversation Service', url: 'http://localhost:8006/', port: 8006 },
    { name: 'Gateway Service', url: 'http://localhost:8000/', port: 8000 }
];

class ServiceChecker {
    constructor() {
        this.servicesOk = false;
    }

    /**
     * Verifica se um serviço está disponível
     */
    async checkService(service) {
        try {
            const controller = new AbortController();
            const timeoutId = setTimeout(() => controller.abort(), 2000); // 2s timeout

            const response = await fetch(service.url, {
                signal: controller.signal,
                method: 'GET'
            });
            
            clearTimeout(timeoutId);
            return response.ok;
        } catch (error) {
            return false;
        }
    }

    /**
     * Verifica todos os serviços
     */
    async checkAllServices() {
        const results = [];
        
        for (const service of REQUIRED_SERVICES) {
            const isAvailable = await this.checkService(service);
            results.push({
                ...service,
                available: isAvailable
            });
        }

        return results;
    }

    /**
     * Mostra modal com instruções se serviços não estiverem disponíveis
     */
    showServicesDownModal(servicesStatus) {
        const unavailableServices = servicesStatus.filter(s => !s.available);
        
        if (unavailableServices.length === 0) {
            this.servicesOk = true;
            return;
        }

        // Criar modal
        const modal = document.createElement('div');
        modal.id = 'services-modal';
        modal.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0, 0, 0, 0.8);
            display: flex;
            justify-content: center;
            align-items: center;
            z-index: 99999;
            font-family: 'Ubuntu', Arial, sans-serif;
        `;

        const modalContent = document.createElement('div');
        modalContent.style.cssText = `
            background: #1D2142;
            color: white;
            padding: 40px;
            border-radius: 15px;
            max-width: 600px;
            text-align: center;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5);
        `;

        const servicesList = unavailableServices.map(s => 
            `<li style="margin: 8px 0;">❌ <strong>${s.name}</strong> (porta ${s.port})</li>`
        ).join('');

        modalContent.innerHTML = `
            <h2 style="color: #ff6b6b; margin-bottom: 20px;">⚠️ Serviços Offline</h2>
            <p style="font-size: 16px; margin-bottom: 20px;">
                Os seguintes serviços não estão disponíveis:
            </p>
            <ul style="text-align: left; list-style: none; padding: 0; margin: 20px 0;">
                ${servicesList}
            </ul>
            <div style="background: #2a3058; padding: 20px; border-radius: 8px; margin: 20px 0;">
                <h3 style="color: #ffd93d; margin-bottom: 15px;">📝 Como Resolver:</h3>
                <ol style="text-align: left; padding-left: 20px; line-height: 1.8;">
                    <li>Abra um terminal/PowerShell na pasta do projeto</li>
                    <li>Execute: <code style="background: #1D2142; padding: 4px 8px; border-radius: 4px; color: #4ade80;">python start_all.py</code></li>
                    <li>Aguarde os serviços iniciarem (≈10 segundos)</li>
                    <li>Clique em "Tentar Novamente" abaixo</li>
                </ol>
            </div>
            <div style="margin-top: 25px;">
                <button id="retry-btn" style="
                    background: #4ade80;
                    color: #1D2142;
                    border: none;
                    padding: 12px 30px;
                    font-size: 16px;
                    border-radius: 8px;
                    cursor: pointer;
                    font-weight: bold;
                    margin-right: 10px;
                ">
                    🔄 Tentar Novamente
                </button>
                <button id="ignore-btn" style="
                    background: #6b7280;
                    color: white;
                    border: none;
                    padding: 12px 30px;
                    font-size: 16px;
                    border-radius: 8px;
                    cursor: pointer;
                ">
                    Continuar Mesmo Assim
                </button>
            </div>
        `;

        modal.appendChild(modalContent);
        document.body.appendChild(modal);

        // Event listeners
        document.getElementById('retry-btn').addEventListener('click', async () => {
            document.getElementById('retry-btn').textContent = '⏳ Verificando...';
            const newStatus = await this.checkAllServices();
            const stillDown = newStatus.filter(s => !s.available);
            
            if (stillDown.length === 0) {
                modal.remove();
                this.servicesOk = true;
                window.location.reload();
            } else {
                document.getElementById('retry-btn').textContent = '🔄 Tentar Novamente';
                alert(`Ainda offline: ${stillDown.map(s => s.name).join(', ')}`);
            }
        });

        document.getElementById('ignore-btn').addEventListener('click', () => {
            modal.remove();
            console.warn('⚠️ Continuando sem verificar serviços - funcionalidades podem não funcionar');
        });
    }

    /**
     * Verifica serviços e mostra modal se necessário
     */
    async initialize() {
        console.log('🔍 Verificando serviços backend...');
        const servicesStatus = await this.checkAllServices();
        
        const allOk = servicesStatus.every(s => s.available);
        
        if (allOk) {
            console.log('✅ Todos os serviços estão disponíveis');
            this.servicesOk = true;
        } else {
            console.warn('⚠️ Alguns serviços não estão disponíveis');
            this.showServicesDownModal(servicesStatus);
        }

        return this.servicesOk;
    }
}

// Instância global
const serviceChecker = new ServiceChecker();

// Auto-verificar ao carregar página (apenas em páginas que precisam)
window.addEventListener('DOMContentLoaded', async () => {
    // Verificar se estamos em uma página que precisa dos serviços
    const needsServices = window.location.pathname.includes('chat.html') || 
                         window.location.pathname.includes('index.html');
    
    if (needsServices) {
        await serviceChecker.initialize();
    }
});
