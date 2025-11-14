import torch
import json
from datasets import load_dataset, Dataset
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
    TrainingArguments,
    TrainerCallback
)
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
from trl import SFTTrainer
import warnings
import time
from datetime import datetime
import gc
warnings.filterwarnings('ignore')

# ========== CONFIGURAÇÕES ==========
NOME_MODELO_BASE = "microsoft/Phi-3-mini-4k-instruct"
NOME_MODELO_FINETUNED = "lanne-ai-final"
ARQUIVO_DATASET = "dataset_prepared.jsonl"

print("\n" + "="*80)
print("                    🚀 LANNE.AI - TREINAMENTO GENERATIVO PT-BR")
print("="*80)
print(f"📅 Início: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("="*80)

# ========== CALLBACK CUSTOMIZADO PARA MONITORAMENTO ==========
class MonitorCallback(TrainerCallback):
    """Callback para mostrar detalhes durante o treino"""
    def __init__(self):
        self.start_time = time.time()
        self.step_times = []
        
    def on_log(self, args, state, control, logs=None, **kwargs):
        """Chamado a cada logging_steps"""
        if state.global_step > 0:
            # Calcular tempo médio por step
            elapsed = time.time() - self.start_time
            avg_time_per_step = elapsed / state.global_step
            remaining_steps = state.max_steps - state.global_step
            eta_seconds = remaining_steps * avg_time_per_step
            eta_minutes = eta_seconds / 60
            
            print("\n" + "-"*60)
            print(f"📊 STEP {state.global_step}/{state.max_steps}")
            print("-"*60)
            
            # Mostrar métricas
            if logs:
                if 'loss' in logs:
                    print(f"   📉 Loss de treino: {logs['loss']:.4f}")
                if 'eval_loss' in logs:
                    print(f"   📈 Loss de validação: {logs['eval_loss']:.4f}")
                if 'learning_rate' in logs:
                    print(f"   🎯 Learning rate: {logs['learning_rate']:.2e}")
            
            # Tempo e memória
            print(f"   ⏱️  Tempo decorrido: {elapsed/60:.1f} min")
            print(f"   ⏳ Tempo restante estimado: {eta_minutes:.1f} min")
            
            # Memória GPU
            if torch.cuda.is_available():
                allocated = torch.cuda.memory_allocated() / 1e9
                reserved = torch.cuda.memory_reserved() / 1e9
                print(f"   🎮 GPU Mem: {allocated:.1f}GB alocado / {reserved:.1f}GB reservado")
            
            print("-"*60)
    
    def on_epoch_end(self, args, state, control, **kwargs):
        """Chamado ao final de cada época"""
        print("\n" + "🌟"*30)
        print(f"   ÉPOCA {int(state.epoch)} CONCLUÍDA!")
        print("🌟"*30 + "\n")

# ========== 1. VERIFICAR AMBIENTE ==========
print("\n[CHECAGEM INICIAL] Verificando ambiente...")
print("-"*60)

# Verificar GPU
if torch.cuda.is_available():
    gpu_name = torch.cuda.get_device_name(0)
    gpu_memory = torch.cuda.get_device_properties(0).total_memory / 1e9
    print(f"✅ GPU detectada: {gpu_name}")
    print(f"✅ VRAM total: {gpu_memory:.1f} GB")
    print(f"✅ CUDA version: {torch.version.cuda}")
    
    # Limpar cache GPU
    torch.cuda.empty_cache()
    gc.collect()
    print(f"✅ Cache GPU limpo")
else:
    print("❌ GPU não detectada! O treino será MUITO lento.")
    resposta = input("Continuar mesmo assim? (s/n): ")
    if resposta.lower() != 's':
        exit(1)

print("-"*60)

# ========== 2. CARREGAR E ANALISAR DATASET ==========
print("\n[PASSO 1/10] 📂 Carregando e analisando dataset...")
print("-"*60)

try:
    # Carregar dataset
    dataset = load_dataset("json", data_files=ARQUIVO_DATASET, split="train")
    print(f"✅ Dataset carregado: {len(dataset)} exemplos")
    
    # Mostrar estatísticas
    print("\n📊 Estatísticas do dataset:")
    
    # Amostra de perguntas
    print("\n🔍 Primeiras 3 perguntas:")
    for i in range(min(3, len(dataset))):
        print(f"   {i+1}. {dataset[i]['question'][:80]}...")
    
    # Verificar tamanhos
    questions_lens = [len(ex['question']) for ex in dataset]
    answers_lens = [len(ex['answer']) for ex in dataset]
    
    print(f"\n📏 Tamanho médio:")
    print(f"   • Perguntas: {sum(questions_lens)/len(questions_lens):.0f} caracteres")
    print(f"   • Respostas: {sum(answers_lens)/len(answers_lens):.0f} caracteres")
    
    # Dividir treino/validação
    print("\n🔄 Dividindo dataset...")
    dataset = dataset.train_test_split(test_size=0.1, seed=42)
    train_dataset = dataset["train"]
    eval_dataset = dataset["test"]
    
    print(f"✅ Dataset dividido:")
    print(f"   • Treino: {len(train_dataset)} exemplos (90%)")
    print(f"   • Validação: {len(eval_dataset)} exemplos (10%)")
    
except Exception as e:
    print(f"❌ Erro ao carregar dataset: {e}")
    exit(1)

print("-"*60)
input("\n⏸️  Pressione ENTER para continuar com o carregamento do modelo...")

# ========== 3. CARREGAR TOKENIZADOR ==========
print("\n[PASSO 2/10] 🔤 Carregando tokenizador...")
print("-"*60)

tokenizer = AutoTokenizer.from_pretrained(
    NOME_MODELO_BASE, 
    trust_remote_code=True,
    use_fast=False
)

# Configurar tokens especiais
if tokenizer.pad_token is None:
    tokenizer.pad_token = tokenizer.eos_token
tokenizer.padding_side = "right"

print(f"✅ Tokenizador carregado")
print(f"   • Vocabulário: {len(tokenizer)} tokens")
print(f"   • Pad token: '{tokenizer.pad_token}'")
print(f"   • EOS token: '{tokenizer.eos_token}'")
print("-"*60)

# ========== 4. FORMATAR DATASET COM EXEMPLOS ==========
print("\n[PASSO 3/10] 🎨 Formatando dataset para chat...")
print("-"*60)

def formatar_exemplo(exemplo):
    """Formata com system prompt fixo em PT-BR"""
    context = exemplo.get("context", "")
    question = exemplo["question"]
    answer = exemplo["answer"]
    
    # System prompt FIXO em PT-BR
    system_prompt = """Você é Lanne.AI, assistente especializada em Linux e Debian.
IMPORTANTE: 
- Responda SEMPRE em português brasileiro
- Seja técnica mas acessível  
- Se faltar informação, PERGUNTE antes de responder
- Foque em soluções práticas e comandos verificáveis
"""
    
    if context:
        system_prompt += f"\nContexto específico: {context}"
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": question},
        {"role": "assistant", "content": answer}
    ]
    
    # Aplicar template do Phi-3
    text = tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=False
    )
    
    return {"text": text}

# Formatar datasets
print("🔄 Formatando datasets...")
train_dataset = train_dataset.map(formatar_exemplo, desc="Formatando treino")
eval_dataset = eval_dataset.map(formatar_exemplo, desc="Formatando validação")

# Mostrar exemplo formatado
print("\n📝 EXEMPLO FORMATADO COMPLETO:")
print("="*60)
exemplo = train_dataset[0]["text"]
print(exemplo[:800])
if len(exemplo) > 800:
    print(f"... [cortado - total de {len(exemplo)} caracteres]")
print("="*60)

# Tokenizar um exemplo para ver o tamanho
tokens = tokenizer(train_dataset[0]["text"], return_tensors="pt")
print(f"\n📊 Exemplo tokenizado: {tokens['input_ids'].shape[1]} tokens")
print("-"*60)

input("\n⏸️  Pressione ENTER para carregar o modelo (vai usar ~6GB de VRAM)...")

# ========== 5. CONFIGURAR QUANTIZAÇÃO ==========
print("\n[PASSO 4/10] ⚙️ Configurando quantização 4-bit...")
print("-"*60)

bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_compute_dtype=torch.bfloat16,
    bnb_4bit_use_double_quant=True,
)

print("✅ Configuração de quantização:")
print("   • Tipo: NF4 (Normal Float 4-bit)")
print("   • Compute dtype: bfloat16")
print("   • Double quantization: Ativado")
print("   • Economia estimada: ~75% da VRAM")
print("-"*60)

# ========== 6. CARREGAR MODELO BASE ==========
print("\n[PASSO 5/10] 🧠 Carregando modelo Phi-3-mini...")
print("-"*60)
print("⏳ Isso vai levar 1-2 minutos...")
print("   Baixando ~3.8GB na primeira vez")
print("   Carregando na GPU com quantização...")

inicio_carga = time.time()

model = AutoModelForCausalLM.from_pretrained(
    NOME_MODELO_BASE,
    quantization_config=bnb_config,
    torch_dtype=torch.bfloat16,
    device_map="auto",
    trust_remote_code=True,
)

tempo_carga = time.time() - inicio_carga
print(f"\n✅ Modelo carregado em {tempo_carga:.1f} segundos!")

# Preparar para treino com quantização
model = prepare_model_for_kbit_training(model)
model.config.use_cache = False

# Mostrar uso de memória
if torch.cuda.is_available():
    memoria_usada = torch.cuda.memory_allocated() / 1e9
    print(f"🎮 Memória GPU usada: {memoria_usada:.2f} GB")

print("-"*60)

# ========== 7. CONFIGURAR E APLICAR LORA ==========
print("\n[PASSO 6/10] 🔧 Configurando LoRA (adaptadores eficientes)...")
print("-"*60)

peft_config = LoraConfig(
    r=32,  # Rank
    lora_alpha=64,
    lora_dropout=0.1,
    bias="none",
    task_type="CAUSAL_LM",
    target_modules=[
        "qkv_proj",
        "o_proj", 
        "gate_up_proj",
        "down_proj"
    ]
)

print("📋 Configuração LoRA:")
print(f"   • Rank (r): 32")
print(f"   • Alpha: 64")
print(f"   • Dropout: 0.1")
print(f"   • Módulos alvo: qkv_proj, o_proj, gate_up_proj, down_proj")

# Aplicar LoRA
print("\n🔄 Aplicando LoRA ao modelo...")
model = get_peft_model(model, peft_config)

# Mostrar parâmetros treináveis
print("\n📊 PARÂMETROS DO MODELO:")
print("-"*40)
model.print_trainable_parameters()
print("-"*40)

total_params = sum(p.numel() for p in model.parameters())
trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
print(f"🎯 Eficiência: Treinando apenas {trainable_params/total_params*100:.2f}% dos parâmetros!")
print("-"*60)

# ========== 8. CONFIGURAR ARGUMENTOS DE TREINAMENTO ==========
print("\n[PASSO 7/10] 📝 Configurando hiperparâmetros...")
print("-"*60)

# Calcular steps totais
steps_per_epoch = len(train_dataset) // (2 * 4)  # batch_size * gradient_accumulation
total_steps = steps_per_epoch * 2  # 2 épocas

training_args = TrainingArguments(
    output_dir="./lanne_checkpoints",
    
    # Batch e gradientes
    per_device_train_batch_size=2,
    per_device_eval_batch_size=2,
    gradient_accumulation_steps=4,
    
    # Learning rate
    learning_rate=2e-4,
    lr_scheduler_type="cosine",
    warmup_steps=50,
    
    # Épocas e passos
    num_train_epochs=2,
    max_steps=total_steps,
    
    # Avaliação e salvamento
    eval_strategy="steps",
    eval_steps=max(50, steps_per_epoch//4),
    save_strategy="steps",
    save_steps=max(100, steps_per_epoch//2),
    
    # Logging detalhado
    logging_steps=10,
    logging_first_step=True,
    logging_dir="./logs",
    
    # Otimizações para RTX 3060
    optim="paged_adamw_8bit",
    gradient_checkpointing=True,
    max_grad_norm=0.3,
    
    # Mixed precision
    bf16=True,
    bf16_full_eval=True,
    
    # Controles
    save_total_limit=2,
    load_best_model_at_end=True,
    metric_for_best_model="eval_loss",
    greater_is_better=False,
    
    # Desabilitar relatórios externos
    report_to="none",
    push_to_hub=False,
    
    # Seeds para reprodutibilidade
    seed=42,
    data_seed=42,
)

print("📊 CONFIGURAÇÃO DO TREINAMENTO:")
print(f"   • Batch size efetivo: {2 * 4} (2 * 4 acumulação)")
print(f"   • Total de steps: ~{total_steps}")
print(f"   • Steps por época: ~{steps_per_epoch}")
print(f"   • Learning rate: 2e-4 com cosine decay")
print(f"   • Warmup steps: 50")
print(f"   • Avaliação a cada: {max(50, steps_per_epoch//4)} steps")
print(f"   • Checkpoint a cada: {max(100, steps_per_epoch//2)} steps")
print(f"   • Otimizador: AdamW 8-bit paginado")
print(f"   • Mixed precision: bfloat16")
print(f"   • Gradient checkpointing: Ativado (economiza VRAM)")
print("-"*60)

# ========== 9. CRIAR TRAINER ==========
print("\n[PASSO 8/10] 🏋️ Preparando trainer...")
print("-"*60)

# Instanciar callback de monitoramento
monitor_callback = MonitorCallback()

# Criar trainer
trainer = SFTTrainer(
    model=model,
    tokenizer=tokenizer,
    train_dataset=train_dataset,
    eval_dataset=eval_dataset,
    peft_config=None,  # Já aplicamos LoRA
    dataset_text_field="text",
    max_seq_length=1024,
    args=training_args,
    callbacks=[monitor_callback],
)

print("✅ Trainer configurado e pronto!")
print("-"*60)

# ========== 10. TESTE RÁPIDO PRÉ-TREINO ==========
print("\n[PASSO 9/10] 🧪 Teste rápido PRÉ-TREINO...")
print("-"*60)

# Fazer uma inferência rápida para ver como está antes do treino
test_prompt = "Como listar arquivos no Linux?"
messages = [
    {"role": "system", "content": "Você é Lanne.AI, assistente Linux em PT-BR."},
    {"role": "user", "content": test_prompt}
]

input_text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
inputs = tokenizer(input_text, return_tensors="pt").to(model.device)

print(f"🔍 Pergunta teste: '{test_prompt}'")
print("💭 Resposta ANTES do treino:")
print("-"*40)

with torch.no_grad():
    outputs = model.generate(
        **inputs,
        max_new_tokens=50,
        temperature=0.7,
        do_sample=True,
        pad_token_id=tokenizer.eos_token_id
    )
    response = tokenizer.decode(outputs[0], skip_special_tokens=True)
    # Extrair apenas a resposta
    if "assistant" in response.lower():
        response = response.split("assistant")[-1].strip()
    print(response[:200])

print("-"*60)

# ========== AVISO FINAL ANTES DO TREINO ==========
print("\n" + "🚨"*30)
print("         PRONTO PARA INICIAR O TREINAMENTO!")
print("🚨"*30)
print(f"\n📊 RESUMO FINAL:")
print(f"   • Modelo: Phi-3-mini 4k")
print(f"   • Dataset: {len(train_dataset)} exemplos de treino")
print(f"   • Épocas: 2")
print(f"   • Tempo estimado: 60-90 minutos")
print(f"   • VRAM necessária: ~8-10 GB")
print(f"   • Checkpoints salvos em: ./lanne_checkpoints")

print("\n⚠️  AVISOS:")
print("   • NÃO feche o terminal")
print("   • NÃO suspenda o computador")
print("   • A GPU ficará em 100% de uso")
print("   • Você verá updates a cada 10 steps")

input("\n🚀 Pressione ENTER para COMEÇAR O TREINAMENTO...")

# ========== TREINAR! ==========
print("\n" + "="*80)
print("                        🔥 INICIANDO TREINAMENTO")
print("="*80)
print(f"⏰ Início: {datetime.now().strftime('%H:%M:%S')}")
print("="*80 + "\n")

try:
    # Executar treinamento
    trainer.train()
    
    print("\n" + "="*80)
    print("                     ✅ TREINAMENTO CONCLUÍDO!")
    print("="*80)
    
except KeyboardInterrupt:
    print("\n\n⚠️ Treinamento interrompido pelo usuário!")
    print("Salvando checkpoint de emergência...")
    trainer.save_model("./lanne_emergency_checkpoint")
    print("Checkpoint salvo em: ./lanne_emergency_checkpoint")
    exit(1)
    
except Exception as e:
    print(f"\n\n❌ Erro durante o treinamento: {e}")
    print("Salvando checkpoint de emergência...")
    trainer.save_model("./lanne_emergency_checkpoint")
    exit(1)

# ========== 11. SALVAR MODELO FINAL ==========
print("\n[PASSO 10/10] 💾 Salvando modelo final...")
print("-"*60)

# Salvar modelo e tokenizador
trainer.save_model(NOME_MODELO_FINETUNED)
tokenizer.save_pretrained(NOME_MODELO_FINETUNED)

print(f"✅ Modelo salvo em: ./{NOME_MODELO_FINETUNED}/")
print(f"✅ Tokenizador salvo")
print("-"*60)

# ========== 12. TESTE PÓS-TREINO ==========
print("\n🧪 Teste rápido PÓS-TREINO...")
print("-"*60)

print(f"🔍 Mesma pergunta: '{test_prompt}'")
print("🎯 Resposta DEPOIS do treino:")
print("-"*40)

# Recarregar para teste (opcional, já está em memória)
inputs = tokenizer(input_text, return_tensors="pt").to(model.device)

with torch.no_grad():
    outputs = model.generate(
        **inputs,
        max_new_tokens=100,
        temperature=0.7,
        do_sample=True,
        pad_token_id=tokenizer.eos_token_id
    )
    response = tokenizer.decode(outputs[0], skip_special_tokens=True)
    if "assistant" in response.lower():
        response = response.split("assistant")[-1].strip()
    print(response[:300])

print("-"*60)

# ========== RELATÓRIO FINAL ==========
print("\n" + "="*80)
print("                        📊 RELATÓRIO FINAL")
print("="*80)

# Tempo total
tempo_total = time.time() - monitor_callback.start_time
print(f"\n⏱️  Tempo total de treino: {tempo_total/60:.1f} minutos")

# Métricas finais
if hasattr(trainer.state, 'log_history'):
    history = trainer.state.log_history
    final_loss = [h.get('loss') for h in history if 'loss' in h]
    if final_loss:
        print(f"📉 Loss final de treino: {final_loss[-1]:.4f}")
    
    eval_losses = [h.get('eval_loss') for h in history if 'eval_loss' in h]
    if eval_losses:
        print(f"📈 Loss final de validação: {eval_losses[-1]:.4f}")
        print(f"   Melhoria: {((eval_losses[0] - eval_losses[-1])/eval_losses[0]*100):.1f}%")

# Arquivos gerados
import os
if os.path.exists(NOME_MODELO_FINETUNED):
    size = sum(os.path.getsize(os.path.join(NOME_MODELO_FINETUNED, f)) 
               for f in os.listdir(NOME_MODELO_FINETUNED)) / 1e6
    print(f"\n💾 Tamanho do modelo salvo: {size:.1f} MB")

print("\n🎉 SUCESSO TOTAL!")
print("="*80)
print("\n📝 PRÓXIMOS PASSOS:")
print("   1. Execute: python chat_lanne.py")
print("   2. Teste com perguntas sobre Linux")
print("   3. O modelo já responde em PT-BR!")
print("\n" + "="*80)