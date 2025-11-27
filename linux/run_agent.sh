#!/bin/bash
# Script para rodar o Lanne Agent (servidor Linux)

cd "$(dirname "$0")"

if [ ! -d "venv" ]; then
    echo "❌ Ambiente virtual não encontrado!"
    echo "Execute primeiro: ./install.sh"
    exit 1
fi

source venv/bin/activate

echo "======================================"
echo "Lanne AI Agent - Linux Server"
echo "======================================"
echo ""
echo "Servidor rodando na porta 9000"
echo "Pressione Ctrl+C para parar"
echo ""

python lanne_agent.py
