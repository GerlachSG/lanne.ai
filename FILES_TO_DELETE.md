# 🗑️ Arquivos que Podem Ser Deletados

Agora que você tem o `run.py`, estes arquivos são **OPCIONAIS** e podem ser deletados:

## ✅ Pode Deletar com Segurança

### Scripts Substituídos pelo `run.py`:

```
✗ start_website.bat          (substituído por run.py)
✗ start_website.sh           (substituído por run.py)
✗ install_dependencies.bat   (run.py faz isso automaticamente)
✗ start_venv.bat            (não é mais necessário)
```

### Documentação Redundante:

```
✗ SETUP.md                   (informações agora no README.md principal)
```

### Arquivos de Website Antigos (Não Usados):

```
✗ website/scripts/chat.js           (substituído por chatIntegration.js)
✗ website/scripts/update.js         (Firebase, não usado mais)
✗ website/scripts/app.py            (não integrado)
✗ website/scripts/chatbot.py        (não integrado)
```

## ⚠️ MANTENHA Estes Arquivos

### Essenciais:

```
✓ run.py                     ← NOVO! Use este para iniciar tudo
✓ start_all.py              ← Usado pelo run.py
✓ requirements.txt          ← Necessário para dependências
✓ README.md                 ← Documentação principal
✓ QUICK_START.md           ← Guia detalhado
```

### Website (Todos Necessários):

```
✓ website/pages/index.html
✓ website/pages/chat.html
✓ website/scripts/login.js
✓ website/scripts/conversationService.js
✓ website/scripts/chatIntegration.js
✓ website/scripts/logineanimacao.js
✓ website/scripts/serviceChecker.js
✓ website/scripts/java-ia.js         ← Mantenha para referência
✓ website/test-integration.html      ← Útil para testes
✓ website/README.md
```

### Serviços Backend (Todos Necessários):

```
✓ auth-service/
✓ conversation-service/
✓ gateway-service/
✓ orchestrator-service/
✓ inference-service/
✓ rag-service/
✓ metrics-service/
✓ web-search-service/
✓ lanne-schemas/
```

---

## 📊 Resumo

**Deletar (5 arquivos):**
- start_website.bat
- start_website.sh
- install_dependencies.bat
- start_venv.bat
- SETUP.md

**Deletar Opcionais (4 arquivos - se quiser limpar):**
- website/scripts/chat.js
- website/scripts/update.js
- website/scripts/app.py
- website/scripts/chatbot.py

**Total economizado:** ~9 arquivos, ~500 linhas de código redundante

---

## 🎯 Novo Fluxo de Trabalho

### Antes:
```bash
1. install_dependencies.bat
2. start_all.py
3. python -m http.server (manual)
4. Abrir navegador (manual)
```

### Agora:
```bash
python run.py
```

**Muito mais simples!** 🎉
