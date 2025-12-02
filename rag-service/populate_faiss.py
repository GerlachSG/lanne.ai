"""
Script para popular o índice FAISS com o dataset enriched
"""

import json
import faiss
import numpy as np
import pickle
from pathlib import Path
from sentence_transformers import SentenceTransformer
from tqdm import tqdm

# Paths
DATA_DIR = Path(__file__).parent / "data"
DATASET_PATH = DATA_DIR / "dataset_enriched.jsonl"
FAISS_INDEX_PATH = DATA_DIR / "faiss_index.bin"
METADATA_PATH = DATA_DIR / "metadata.pkl"
EMBEDDINGS_PATH = DATA_DIR / "embeddings.npy"

print("🚀 Iniciando população do FAISS...")

# Carregar modelo de embeddings
print("📦 Carregando modelo de embeddings (sentence-transformers)...")
model = SentenceTransformer('all-MiniLM-L6-v2')  # 384 dimensões
dimension = 384

# Ler dataset
print(f"📖 Lendo dataset: {DATASET_PATH}")
documents = []
with open(DATASET_PATH, 'r', encoding='utf-8') as f:
    for line in f:
        doc = json.loads(line)
        documents.append(doc)

print(f"✅ {len(documents)} documentos carregados")

# Preparar textos para embeddings
print("🔤 Preparando textos...")
texts = []
metadata = []

for doc in documents:
    # Combinar question + context para texto rico
    text = f"{doc['question']}\n{doc.get('context', '')}"
    texts.append(text)
    
    # Metadados
    metadata.append({
        "text": text,
        "question": doc['question'],
        "answer": doc['answer'],
        "category": doc.get('category', 'Unknown'),
        "source": "dataset_enriched"
    })

# Gerar embeddings em lotes
print("🧠 Gerando embeddings (isso pode demorar alguns minutos)...")
batch_size = 256
embeddings_list = []

for i in tqdm(range(0, len(texts), batch_size)):
    batch = texts[i:i + batch_size]
    batch_embeddings = model.encode(batch, show_progress_bar=False)
    embeddings_list.append(batch_embeddings)

embeddings = np.vstack(embeddings_list).astype('float32')
print(f"✅ Embeddings gerados: shape {embeddings.shape}")

# Criar índice FAISS
print("🔍 Criando índice FAISS...")
index = faiss.IndexFlatL2(dimension)
index.add(embeddings)
print(f"✅ Índice criado com {index.ntotal} vetores")

# Salvar
print("💾 Salvando arquivos...")
faiss.write_index(index, str(FAISS_INDEX_PATH))
print(f"  ✓ FAISS index: {FAISS_INDEX_PATH}")

with open(METADATA_PATH, 'wb') as f:
    pickle.dump(metadata, f)
print(f"  ✓ Metadata: {METADATA_PATH}")

np.save(EMBEDDINGS_PATH, embeddings)
print(f"  ✓ Embeddings: {EMBEDDINGS_PATH}")

print("\n🎉 Concluído! FAISS populado com sucesso!")
print(f"📊 Total de documentos indexados: {len(documents)}")
print(f"📏 Dimensão dos vetores: {dimension}")
