#!/bin/bash
# Script para rodar o Lanne AI TUI

cd "$(dirname "$0")"

if [ ! -d "venv" ]; then
    echo "❌ Ambiente virtual não encontrado!"
    echo "Execute primeiro: ./install.sh"
    exit 1
fi

# Configurar locale para UTF-8
export LC_ALL=pt_BR.UTF-8
export LANG=pt_BR.UTF-8
export PYTHONIOENCODING=utf-8

source venv/bin/activate
python lanne_client.py
