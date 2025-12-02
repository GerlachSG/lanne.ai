#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Lanne AI TUI Client - Script de entrada
Execute: python lanne_client.py
"""

import sys
import io
from pathlib import Path

# Forçar UTF-8 para stdout/stderr
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
if sys.stderr.encoding != 'utf-8':
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Adicionar path do projeto
sys.path.insert(0, str(Path(__file__).parent))

def main():
    """Ponto de entrada principal"""
    try:
        from tui.app import LanneApp
        app = LanneApp()
        app.run()
    except ImportError as e:
        print(f"Erro de importação: {e}")
        print("\nVerifique se as dependências estão instaladas:")
        print("  pip install textual rich httpx")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n👋 Até logo!")
        sys.exit(0)
    except Exception as e:
        print(f"Erro: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()