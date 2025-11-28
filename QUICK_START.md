# 🚀 Guia Rápido - Lanne AI Website

## ⚡ Primeira Vez? Instale as Dependências Primeiro!

### Windows:
```cmd
install_dependencies.bat
```

### Linux/Mac:
```bash
pip install -r requirements.txt
```

**Isso precisa ser feito apenas UMA VEZ!**

---

## Opção 1: Usar o Script Automático (RECOMENDADO)

### Windows:
```cmd
start_website.bat
```

### Linux/Mac:
```bash
chmod +x start_website.sh
./start_website.sh
```

**O que ele faz:**
1. ✅ Verifica e instala dependências (se necessário)
2. ✅ Inicia todos os serviços backend (`start_all.py`)
3. ✅ Aguarda os serviços ficarem prontos
4. ✅ Inicia um servidor web local (porta 8080)
5. ✅ Abre o navegador automaticamente

---

## Opção 2: Manualmente

### Passo 1: Iniciar Backend
```bash
python start_all.py
```

Aguarde até ver todas as mensagens:
```
✓ Auth Service running on port 8007
✓ Conversation Service running on port 8006
✓ Gateway Service running on port 8000
...
```

### Passo 2: Iniciar Website

**Opção A - Servidor Local (evita CORS):**
```bash
python -m http.server 8080 --directory website/pages
```
Acesse: http://localhost:8080/index.html

**Opção B - Direto no navegador:**
Abra diretamente: `website/pages/index.html`

---

## 🔍 Verificação Automática

O website agora verifica automaticamente se os serviços estão rodando!

Se você esquecer de iniciar o backend, verá esta tela:

```
⚠️ Serviços Offline

Os seguintes serviços não estão disponíveis:
❌ Auth Service (porta 8007)
❌ Conversation Service (porta 8006)
❌ Gateway Service (porta 8000)

📝 Como Resolver:
1. Abra um terminal/PowerShell na pasta do projeto
2. Execute: python start_all.py
3. Aguarde os serviços iniciarem (≈10 segundos)
4. Clique em "Tentar Novamente"
```

---

## ⚡ Atalhos Úteis

### Ver logs dos serviços:
Os logs aparecem na janela onde você rodou `start_all.py`

### Parar tudo:
- **Windows**: Feche a janela do terminal ou pressione `Ctrl+C`
- **Linux/Mac**: Pressione `Ctrl+C` no terminal

### Reiniciar apenas o backend:
```bash
# Pare com Ctrl+C, depois:
python start_all.py
```

---
## 🐛 Solução de Problemas

### "No module named 'fastapi'" ou outras dependências
→ Execute primeiro: `install_dependencies.bat`
→ Ou manualmente: `pip install -r requirements.txt`

### "ERR_CONNECTION_REFUSED"
### "ERR_CONNECTION_REFUSED"
→ Backend não está rodando. Execute `start_website.bat`

### "Port already in use"
→ Algum serviço já está rodando. Feche tudo e tente novamente.

### Login não funciona
→ Verifique se o Auth Service está na porta 8007

### Conversas não carregam
→ Verifique se o Conversation Service está na porta 8006

### IA não responde
→ Verifique se todos os serviços estão rodando (Gateway, Orchestrator, Inference, RAG)

---

## 📝 Portas Usadas

| Serviço | Porta |
|---------|-------|
| Gateway | 8000 |
| Orchestrator | 8001 |
| Inference | 8002 |
| RAG | 8003 |
| Web Search | 8004 |
| Metrics | 8005 |
| Conversation | 8006 |
| Auth | 8007 |
## ✅ Checklist Antes de Usar

- [ ] Python 3.8+ instalado
- [ ] **Dependências instaladas** (`install_dependencies.bat` ou `pip install -r requirements.txt`)
- [ ] Backend iniciado (`start_all.py` rodando)
- [ ] Website aberto (porta 8080 ou direto no navegador)
- [ ] Verificador de serviços passou (tela de login aparece)
- [ ] Dependências instaladas (`pip install -r requirements.txt`)
- [ ] Backend iniciado (`start_all.py` rodando)
- [ ] Website aberto (porta 8080 ou direto no navegador)
- [ ] Verificador de serviços passou (tela de login aparece)

---

**Pronto! Agora é só fazer login e conversar com a IA! 🎉**
