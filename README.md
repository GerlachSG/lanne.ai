# Website Lanne AI - Frontend Integrado

Interface web integrada com o sistema backend Lanne AI para chat com IA sobre Debian Linux.

## 🚀 Mudanças Implementadas

### ✅ Sistema de Login Atualizado
- **Removido**: Firebase Authentication
- **Adicionado**: Sistema de autenticação local com `auth-service`
- Login simples com username (cria conta automaticamente se não existir)
- Sessão persistente com localStorage
- Validação de token JWT

### ✅ Histórico de Conversas
- Integração completa com `conversation-service`
- Lista de conversas carregada dinamicamente do banco de dados
- Conversas organizadas por data (mais recentes primeiro)
- Cada conversa mostra título, descrição e número de mensagens
- Clique em uma conversa para carregar mensagens anteriores

### ✅ Chat com IA
- Integração com `gateway-service` e `orchestrator-service`
- Todas as conversas são sobre Debian Linux
- Mensagens salvas automaticamente no histórico
- Suporte a formatação Markdown nas respostas
- Indicador visual de "pensando"

## 📁 Estrutura de Arquivos

```
website/
├── pages/
│   ├── index.html          # Página de login (atualizada)
│   └── chat.html           # Página de chat (atualizada)
├── scripts/
│   ├── login.js            # 🆕 Novo sistema de autenticação
│   ├── conversationService.js  # 🆕 Gerenciamento de conversas
│   ├── chatIntegration.js  # 🆕 Chat integrado com backend
│   └── logineanimacao.js   # ✏️ Atualizado para novo login
└── imagens/
    └── (recursos visuais)
```

## 🔧 Configuração

### Pré-requisitos

Os seguintes serviços devem estar rodando:

1. **Auth Service** (porta 8007)
   ```bash
   python auth-service/main.py
   ```

2. **Conversation Service** (porta 8006)
   ```bash
   python conversation-service/main.py
   ```

3. **Gateway Service** (porta 8000)
   ```bash
   python gateway-service/main.py
   ```

4. **Orchestrator Service** (porta 8001)
   ```bash
   python orchestrator-service/main.py
   ```

### URLs dos Serviços

Os scripts estão configurados para:
- Auth Service: `http://localhost:8007`
- Conversation Service: `http://localhost:8006`
- Gateway Service: `http://localhost:8000`

**⚠️ Importante**: Se os serviços estiverem em outras portas ou hosts, edite as constantes no topo de cada arquivo:
- `login.js`: `API_BASE_URL`
- `conversationService.js`: `CONVERSATION_API_URL` e `GATEWAY_API_URL`

## 🌐 Como Usar

### 1. Iniciar os Serviços Backend

```bash
# Na raiz do projeto
python start_all.py
```

Ou inicie cada serviço individualmente nas portas corretas.

### 2. Abrir o Website

Abra `website/pages/index.html` em um navegador moderno.

### 3. Fazer Login

1. Clique no botão "entrar"
2. Digite um nome de usuário (ex: "usuario123")
3. Clique em "Entrar com Lanne AI"
4. Você será redirecionado para a página de chat

**Nota**: Se o usuário não existir, será criado automaticamente.

### 4. Conversar com a IA

1. Digite sua pergunta sobre Debian Linux
2. Pressione Enter ou clique no botão enviar
3. A resposta será salva automaticamente no histórico

### 5. Navegar no Histórico

- Suas conversas aparecem na barra lateral esquerda
- Clique em qualquer conversa para ver mensagens anteriores
- Clique no botão "+" para iniciar uma nova conversa

## 🎨 Funcionalidades

### Autenticação
- ✅ Login/registro automático
- ✅ Validação de token JWT
- ✅ Sessão persistente (localStorage)
- ✅ Logout seguro
- ✅ Redirecionamento automático se não autenticado

### Conversas
- ✅ Criar nova conversa
- ✅ Listar conversas do usuário
- ✅ Carregar mensagens de conversas anteriores
- ✅ Deletar conversas (via API)
- ✅ Geração automática de título
- ✅ Ordenação por data de atualização

### Chat
- ✅ Envio de mensagens para IA
- ✅ Respostas formatadas em Markdown
- ✅ Indicador de "pensando"
- ✅ Scroll automático
- ✅ Suporte a código com syntax highlighting
- ✅ Tema claro/escuro

## 🔒 Segurança

- Tokens JWT para autenticação
- Validação de sessão ao carregar página de chat
- Redirecionamento automático se token inválido
- Logout limpa sessão local e backend

## 🐛 Troubleshooting

### "Erro ao fazer login"
- Verifique se o `auth-service` está rodando na porta 8007
- Abra o console do navegador (F12) para ver detalhes do erro

### "Erro ao carregar conversas"
- Verifique se o `conversation-service` está rodando na porta 8006
- Confirme que você está autenticado (verifique localStorage)

### "Erro ao processar mensagem"
- Verifique se todos os serviços estão rodando:
  - gateway-service (8000)
  - orchestrator-service (8001)
  - inference-service (8002)
  - rag-service (8003)
- Verifique os logs dos serviços no terminal

### CORS Errors
- Se você estiver abrindo o HTML diretamente (`file://`), use um servidor local:
  ```bash
  # Python
  python -m http.server 8080 --directory website/pages
  
  # Acesse: http://localhost:8080/index.html
  ```

## 📝 Notas de Desenvolvimento

### Arquivos Substituídos
- ❌ `update.js` (Firebase) → ✅ `login.js` (auth-service)
- ❌ Parte do `java-ia.js` → ✅ `chatIntegration.js`

### Arquivos Mantidos
- ✅ `chat.js` (mantido para referência)
- ✅ Estrutura CSS e HTML (só scripts foram atualizados)

### Distribuição Linux
Todas as conversas são configuradas para **Debian** apenas, conforme solicitado.

## 🔄 Fluxo de Dados

```
Usuário → index.html → login.js → auth-service
                                      ↓
                                   token JWT
                                      ↓
        chat.html → chatIntegration.js → conversationService.js
                                              ↓
                    ┌─────────────────────────┴─────────────────────────┐
                    ↓                                                   ↓
        conversation-service                              gateway-service
        (histórico, mensagens)                           (enviar mensagem)
                                                                 ↓
                                                        orchestrator-service
                                                                 ↓
                                                          (resposta da IA)
```

## ✨ Próximas Melhorias Sugeridas

- [ ] Upload de imagens/screenshots
- [ ] Busca no histórico de conversas
- [ ] Exportar conversas em PDF/TXT
- [ ] Suporte a múltiplas distribuições Linux
- [ ] Notificações de novas mensagens
- [ ] Avatar customizado
- [ ] Compartilhamento de conversas

---

**Desenvolvido para o projeto Lanne AI - Assistente Linux**