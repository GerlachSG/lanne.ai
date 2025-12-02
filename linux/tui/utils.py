"""
Funções utilitárias para o TUI
"""

from pathlib import Path


def load_ascii_logo() -> str:
    """Carrega logo ASCII do arquivo"""
    logo_path = Path(__file__).parent.parent / "lanne_ascii.txt"
    
    if logo_path.exists():
        try:
            with open(logo_path, 'r', encoding='utf-8') as f:
                # Lê e remove caracteres de retorno de carro que podem causar problemas
                content = f.read().replace('\r\n', '\n').replace('\r', '\n')
                return content.strip()
        except Exception as e:
            print(f"Erro ao carregar logo: {e}")
    
    # Fallback se não encontrar o arquivo ou houver erro
    return """
 __         ______     __   __     __   __     ______    
/\\ \\       /\\  __ \\   /\\ "-.\\ \\   /\\ "-.\\ \\   /\\  ___\\   
\\ \\ \\____  \\ \\  __ \\  \\ \\ \\-.  \\  \\ \\ \\-.  \\  \\ \\  __\\   
 \\ \\_____\\  \\ \\_\\ \\_\\  \\ \\_\\\\"\\_\\  \\ \\_\\\\"\\_\\  \\ \\_____\\ 
  \\/_____/   \\/_/\\/_/   \\/_/ \\/_/   \\/_/ \\/_/   \\/_____/ 
"""
