#!/usr/bin/env python3
"""
Script para retreinar o classificador de intenção.
Usa o dataset expandido do intent_dataset.json

Uso: python train_classifier.py
"""

import json
import joblib
from pathlib import Path
from sklearn.pipeline import Pipeline
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import cross_val_score
import numpy as np

# Paths
DATASET_PATH = Path(__file__).parent / "intent_dataset.json"
OUTPUT_PATH = Path(__file__).parent / "intent_classifier.joblib"

def load_dataset():
    """Carrega o dataset de treinamento."""
    with open(DATASET_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    samples = data.get("training_samples", {})
    
    X = []  # queries
    y = []  # labels
    
    for label, queries in samples.items():
        for query in queries:
            X.append(query)
            y.append(label)
    
    return X, y


def train_classifier(X, y):
    """Treina o pipeline de classificação."""
    pipeline = Pipeline([
        ('tfidf', TfidfVectorizer(
            ngram_range=(1, 2),
            max_features=5000,
            lowercase=True,
            strip_accents='unicode'
        )),
        ('classifier', RandomForestClassifier(
            n_estimators=100,
            max_depth=15,
            random_state=42,
            class_weight='balanced'
        ))
    ])
    
    pipeline.fit(X, y)
    return pipeline


def evaluate_classifier(pipeline, X, y):
    """Avalia com cross-validation."""
    scores = cross_val_score(pipeline, X, y, cv=5, scoring='f1_weighted')
    return scores


def main():
    print("=" * 60)
    print("TREINAMENTO DO CLASSIFICADOR DE INTENÇÃO")
    print("=" * 60)
    
    # 1. Carregar dataset
    print("\n[1/4] Carregando dataset...")
    X, y = load_dataset()
    
    # Contar amostras por classe
    from collections import Counter
    counts = Counter(y)
    print(f"    Total de amostras: {len(X)}")
    for label, count in sorted(counts.items()):
        print(f"    - {label}: {count} amostras")
    
    # 2. Treinar
    print("\n[2/4] Treinando modelo...")
    pipeline = train_classifier(X, y)
    print("    Pipeline: TF-IDF (ngram 1-2) + RandomForest (100 trees)")
    
    # 3. Avaliar
    print("\n[3/4] Avaliando (5-fold cross-validation)...")
    scores = evaluate_classifier(pipeline, X, y)
    print(f"    F1-Score médio: {np.mean(scores):.4f} (+/- {np.std(scores):.4f})")
    print(f"    Scores por fold: {[f'{s:.4f}' for s in scores]}")
    
    # 4. Salvar
    print("\n[4/4] Salvando modelo...")
    joblib.dump(pipeline, OUTPUT_PATH)
    print(f"    Salvo em: {OUTPUT_PATH}")
    
    # 5. Testar com exemplos
    print("\n" + "=" * 60)
    print("TESTE COM EXEMPLOS PROBLEMÁTICOS")
    print("=" * 60)
    
    test_cases = [
        "qual o uso de memoria ram atualmente",
        "mostre me as informacoes da interface de rede",
        "qual meu IP",
        "execute ip addr show",
        "quem ta logado",
        "como instalar docker",
        "oi tudo bem",
        "você gosta de Linux?",
    ]
    
    for query in test_cases:
        pred = pipeline.predict([query])[0]
        proba = max(pipeline.predict_proba([query])[0])
        print(f"    '{query[:40]:<40}' -> {pred:<10} (conf={proba:.2f})")
    
    print("\n✅ Treinamento concluído!")
    print("   Reinicie o orchestrator-service para usar o novo modelo.")


if __name__ == "__main__":
    main()
