# File: prepare_dataset_lanne.py
import json
import os

ARQUIVO_JSON = "dataset.json"  # Seu arquivo com 20k exemplos
ARQUIVO_JSONL = "dataset_prepared.jsonl"

print("📂 Preparando dataset...")

# Carregar JSON
with open(ARQUIVO_JSON, 'r', encoding='utf-8') as f:
    data = json.load(f)

print(f"✓ Carregado: {len(data)} exemplos")

# Validar estrutura
exemplo = data[0]
print(f"\n📋 Estrutura do exemplo:")
print(f"   - question: {exemplo['question'][:50]}...")
print(f"   - answer: {exemplo['answer'][:50]}...")
print(f"   - context: {exemplo['context'][:50]}...\n")

# Converter para JSONL (1 JSON por linha)
with open(ARQUIVO_JSONL, 'w', encoding='utf-8') as f:
    for item in data:
        f.write(json.dumps(item, ensure_ascii=False) + '\n')

print(f"✅ Convertido para JSONL: {ARQUIVO_JSONL}")
print(f"   Total: {len(data)} linhas")
