# File: chat_lanne.py (Corrigido)
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline
from peft import PeftModel
import json
import warnings

# Suprimir avisos comuns de versão do transformers
warnings.filterwarnings('ignore', category=FutureWarning, module='transformers')

class LanneChat:
    def __init__(self, model_name="lanne-ai-final"): # <-- CORREÇÃO 1: Nome do modelo
        print("🚀 Inicializando Lanne.AI...")
        
        try:
            self.tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
            
            # Carregar modelo base
            base_model = AutoModelForCausalLM.from_pretrained(
                "microsoft/Phi-3-mini-4k-instruct",
                torch_dtype=torch.bfloat16,
                device_map="auto",
                trust_remote_code=True
            )
            
            # Aplicar LoRA (adaptadores fine-tuned)
            print(f"🔄 Aplicando adaptadores LoRA de '{model_name}'...")
            self.model = PeftModel.from_pretrained(base_model, model_name)
            self.model.eval()
            print("✅ Modelo fine-tuned carregado!")

            # Pipeline para gerar
            self.pipe = pipeline(
                "text-generation",
                model=self.model,
                tokenizer=self.tokenizer,
                torch_dtype=torch.bfloat16,
                device_map="auto"
            )
            
            print("✅ Lanne.AI pronta!\n")
            
        except Exception as e:
            print(f"\n❌ ERRO FATAL ao inicializar:")
            print(f"   Verifique se a pasta '{model_name}' está no mesmo diretório.")
            print(f"   Erro: {e}\n")
            exit(1)
    
    def verificar_contexto_incompleto(self, user_input):
        """Detecta se faltam detalhes"""
        keywords_problema = ['travado', 'erro', 'lento', 'quebrou', 'crash', 'não funciona']
        
        # Se menciona problema mas tem poucas palavras
        if any(k in user_input.lower() for k in keywords_problema):
            if len(user_input.split()) < 8:
                return True
        
        return False
    
    def fazer_perguntas_checklist(self):
        """Faz perguntas para coletar contexto"""
        print("\n❓ Preciso de mais detalhes para ajudar melhor:\n")
        
        perguntas_gerais = [
            "Qual foi exatamente a mudança que você fez?",
            "Qual é o erro ou comportamento específico?",
            "Qual o output do comando: `uname -a`?"
        ]
        
        contexto_adicional = ""
        for i, pergunta in enumerate(perguntas_gerais, 1):
            print(f"  {i}. {pergunta}")
            resposta = input(f"      > ").strip()
            if resposta:
                contexto_adicional += f"\n• {resposta}"
        
        return contexto_adicional
    
    def gerar_resposta(self, user_input, history):
        """Gera resposta usando o modelo fine-tuned e o histórico"""
        
        # Verificar se contexto é incompleto (apenas para a pergunta ATUAL)
        if self.verificar_contexto_incompleto(user_input):
            contexto_adicional = self.fazer_perguntas_checklist()
            user_input = user_input + contexto_adicional
            print()
        
        # Adicionar pergunta atual ao histórico
        history.append({"role": "user", "content": user_input})
        
        # Formatar como chat (System Prompt + Histórico Completo)
        messages = [
            {
                "role": "system",
                "content": "Você é Lanne.AI, assistente especializado em Linux/Debian. Responda sempre em português brasileiro. Seja conciso, prático e didático."
            }
        ] + history
        
        # Aplicar template de chat
        # add_generation_prompt=True adiciona o <|assistant|> no final
        prompt = self.tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True
        )
        
        print("\n💭 Gerando resposta...\n")
        
        # Gerar
        outputs = self.pipe(
            prompt,
            max_new_tokens=512,
            temperature=0.7,
            top_p=0.9,
            do_sample=True,
            pad_token_id=self.tokenizer.eos_token_id # Evitar warnings
        )
        
        resposta_completa = outputs[0]["generated_text"]
        
        # --- CORREÇÃO 2: Extrair apenas a resposta NOVA ---
        # O pipeline retorna o PROMPT + RESPOSTA.
        # Nós removemos o prompt original do início da string.
        if resposta_completa.startswith(prompt):
            resposta_nova = resposta_completa[len(prompt):].strip()
        else:
            # Fallback (Plano B)
            # Tenta pegar o que veio depois da última tag <|assistant|>
            if "<|assistant|>" in resposta_completa:
                resposta_nova = resposta_completa.split("<|assistant|>")[-1].strip()
            else:
                resposta_nova = "Desculpe, tive um problema ao processar a resposta."
        
        # Adicionar resposta do bot ao histórico
        history.append({"role": "assistant", "content": resposta_nova})
        
        return resposta_nova
    
    def chat_loop(self):
        """Loop principal de conversa"""
        print("\n" + "="*70)
        print("🎯 LANNE.AI - Chat Generativo Linux/Debian")
        print("="*70)
        print("Digite 'sair' para encerrar\n")
        
        # Histórico da conversa
        history = []
        
        while True:
            user_input = input("Você: ").strip()
            
            if not user_input:
                continue
            
            if user_input.lower() == 'sair':
                print("\n👋 Até logo! (Lanne.AI desligando)")
                break
            
            try:
                # Passar o histórico e a nova pergunta
                resposta = self.gerar_resposta(user_input, history)
                print(f"🤖 Lanne.AI:\n{resposta}\n")
                
            except Exception as e:
                print(f"\n❌ Erro: {e}\n")
                # Limpar histórico em caso de erro para não poluir
                history = []

# ========== EXECUTAR ==========
if __name__ == "__main__":
    # Apontar para a pasta do modelo treinado
    lanne = LanneChat(model_name="lanne-ai-final")
    lanne.chat_loop()