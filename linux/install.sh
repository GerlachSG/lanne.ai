#!/bin/bash
# Script de instalação do Lanne AI TUI para Linux

echo "==================================="
echo "Lanne AI TUI - Instalação Linux"
echo "==================================="
echo ""

# Verificar se Python 3 está instalado
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 não encontrado!"
    echo "Instale com: sudo apt install python3 python3-pip python3-venv"
    exit 1
fi

echo "✓ Python 3 encontrado: $(python3 --version)"

# Criar ambiente virtual
echo ""
echo "Criando ambiente virtual..."
python3 -m venv venv

# Ativar ambiente virtual
echo "Ativando ambiente virtual..."
source venv/bin/activate

# Atualizar pip
echo "Atualizando pip..."
pip install --upgrade pip --quiet

# Instalar dependências
echo "Instalando dependências..."
pip install -r requirements.txt --quiet

echo ""
echo "==================================="
echo "✓ Instalação concluída!"
echo "==================================="
echo ""
echo "Para iniciar o TUI:"
echo "  1. source venv/bin/activate"
echo "  2. python lanne_client.py"
echo ""
echo "Ou use: ./run.sh"
echo ""
