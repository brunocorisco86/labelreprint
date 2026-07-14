import os
import asyncio
from dotenv import load_dotenv
from aiogram import Bot

load_dotenv()

async def main():
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        print("Erro: Token não configurado ou nulo no .env")
        return
        
    print(f"Testando conexão com token: {token[:10]}...{token[-5:] if len(token) > 15 else ''}")
    
    if "seu_token" in token:
        print("Erro: Token padrão de exemplo no .env")
        return
        
    try:
        bot = Bot(token=token)
        me = await bot.get_me()
        print("====================================================")
        print(f" Conectado com Sucesso! ")
        print(f" ID do Bot: {me.id}")
        print(f" Nome do Bot: {me.first_name}")
        print(f" Username: @{me.username}")
        print("====================================================")
        await bot.session.close()
    except Exception as e:
        print(f"Erro ao conectar com o Telegram: {e}")

if __name__ == "__main__":
    asyncio.run(main())
