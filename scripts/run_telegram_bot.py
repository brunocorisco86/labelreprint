import os
import sys
import asyncio

# Adiciona a raiz do projeto ao sys.path para permitir a importação de src
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from src.telegram.bot import TelegramInterfaceBot

def main():
    print("====================================================")
    print("    INICIANDO BOT DE TELEGRAM DE RÓTULOS (C.VALE)   ")
    print("====================================================")
    print("\nO bot do telegram para impressão de rótulos está inicializando...")
    print("Para encerrar o bot, pressione CTRL+C.\n")
    print("----------------------------------------------------")
    
    try:
        bot_interface = TelegramInterfaceBot()
        asyncio.run(bot_interface.start())
    except KeyboardInterrupt:
        print("\nBot do Telegram finalizado pelo usuário.")
    except Exception as e:
        print(f"\nErro ao iniciar bot do Telegram: {e}")

if __name__ == "__main__":
    main()
