import os
import sys

# Adiciona a raiz do projeto ao sys.path para permitir a importação de src
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from src.web.app import app

def main():
    print("====================================================")
    # Exibe no terminal a URL para facilitar o acesso
    print("   INICIANDO PORTAL DE RÓTULOS DE RAÇÃO (C.VALE)    ")
    print("====================================================")
    print("\nO portal de impressão de rótulos de ração está inicializando...")
    print("Acesse no navegador: http://localhost:5000")
    print("Para encerrar o servidor, pressione CTRL+C.\n")
    print("----------------------------------------------------")
    
    app.run(host="127.0.0.1", port=5000, debug=True)

if __name__ == "__main__":
    main()
