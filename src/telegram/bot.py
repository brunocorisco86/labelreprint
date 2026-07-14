import os
import re
import logging
import asyncio
from datetime import datetime, timedelta
import httpx
from dotenv import load_dotenv

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.enums import ParseMode

# Carrega as configurações do ambiente
load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_ADMIN_ID = os.getenv("TELEGRAM_ADMIN_ID")
BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:5001")

# Configuração do Logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("TelegramBot")

# Define a Máquina de Estados (FSM)
class LabelReprintForm(StatesGroup):
    choosing_label = State()      # Escolhendo qual rótulo quer imprimir
    typing_date = State()         # Informando a data de fabricação
    confirming_email = State()    # Confirmando e-mail cadastrado ou solicitando um novo
    typing_email = State()        # Digitando um novo e-mail
    confirming_generation = State() # Tela final de confirmação de geração e envio
    loop_decision = State()       # Escolhendo se quer gerar outro ou sair

# Teclado padrão de reinício / cancelamento
def get_cancel_keyboard():
    builder = InlineKeyboardBuilder()
    builder.button(text="❌ Cancelar e Sair", callback_data="cancel_operation")
    return builder.as_markup()

class TelegramInterfaceBot:
    def __init__(self):
        if not TELEGRAM_BOT_TOKEN or "seu_token" in TELEGRAM_BOT_TOKEN:
            logger.error("TELEGRAM_BOT_TOKEN inválido ou não configurado no arquivo .env")
            raise ValueError("TELEGRAM_BOT_TOKEN inválido ou não configurado no arquivo .env")
            
        self.bot = Bot(token=TELEGRAM_BOT_TOKEN)
        self.dp = Dispatcher(storage=MemoryStorage())
        self.setup_handlers()

    def setup_handlers(self):
        # Comandos Básicos
        self.dp.message.register(self.cmd_start, Command("start"))
        self.dp.message.register(self.cmd_help, Command("help"))
        self.dp.message.register(self.cmd_cancel, Command("cancel"))
        
        # Callbacks Globais e Menus
        self.dp.callback_query.register(self.process_cancel, F.data == "cancel_operation")
        self.dp.callback_query.register(self.register_start_print, F.data == "start_print")
        self.dp.callback_query.register(self.process_show_help, F.data == "show_help")
        
        # FSM - Escolha do Rótulo
        self.dp.callback_query.register(self.process_label_choice, LabelReprintForm.choosing_label)
        
        # FSM - Data de Fabricação
        self.dp.callback_query.register(self.process_quick_date, LabelReprintForm.typing_date, F.data.startswith("date_"))
        self.dp.message.register(self.process_typed_date, LabelReprintForm.typing_date)
        
        # FSM - E-mail
        self.dp.callback_query.register(self.process_email_confirmation, LabelReprintForm.confirming_email)
        self.dp.message.register(self.process_typed_email, LabelReprintForm.typing_email)
        
        # FSM - Confirmação Final de Geração
        self.dp.callback_query.register(self.process_final_generation, LabelReprintForm.confirming_generation)
        
        # FSM - Decisão do Loop
        self.dp.callback_query.register(self.process_loop_decision, LabelReprintForm.loop_decision)

    # --- HANDLERS DE COMANDO ---

    async def cmd_start(self, message: types.Message, state: FSMContext):
        """Handler do comando /start. Mostra o painel inicial com opções."""
        await state.clear()
        
        # Verificar se o ID é do administrador ou se o admin não está configurado
        if TELEGRAM_ADMIN_ID and str(message.from_user.id) != str(TELEGRAM_ADMIN_ID):
            await message.answer(
                "⚠️ *Acesso Restrito!*\nEste bot é de uso exclusivo para o Homelab configurado.",
                parse_mode=ParseMode.MARKDOWN
            )
            return

        welcome_text = (
            "✨ *Portal de Rótulos de Ração C.Vale - Telegram Bot* ✨\n\n"
            "Bem-vindo! Este bot permite gerar e reenviar de forma prática "
            "rótulos de ração em formato PDF diretamente do Homelab.\n\n"
            "Como você deseja proceder?"
        )
        
        builder = InlineKeyboardBuilder()
        builder.button(text="🏷️ Imprimir Rótulo(s)", callback_data="start_print")
        builder.button(text="ℹ️ Ajuda & Comandos", callback_data="show_help")
        builder.adjust(1)
        
        await message.answer(welcome_text, reply_markup=builder.as_markup(), parse_mode=ParseMode.MARKDOWN)

    async def cmd_help(self, message: types.Message):
        """Mostra informações de ajuda."""
        help_text = (
            "📌 *Guia de Uso do Bot C.Vale*:\n\n"
            "/start - Inicia a interação e exibe o menu principal.\n"
            "/cancel - Cancela qualquer operação em andamento e limpa o estado.\n"
            "/help - Exibe este menu explicativo.\n\n"
            "💡 *Dica*: O bot utiliza botões interativos para facilitar todas as etapas "
            "de escolha de rótulos e datas."
        )
        await message.answer(help_text, parse_mode=ParseMode.MARKDOWN)

    async def process_show_help(self, callback_query: types.CallbackQuery):
        """Callback do botão de ajuda."""
        await callback_query.answer()
        await self.cmd_help(callback_query.message)

    async def cmd_cancel(self, message: types.Message, state: FSMContext):
        """Cancela a FSM ativa."""
        current_state = await state.get_state()
        if current_state is None:
            await message.answer("Nenhuma operação ativa no momento.")
            return
            
        await state.clear()
        await message.answer("❌ Operação cancelada. Digite /start para iniciar novamente.")

    async def process_cancel(self, callback_query: types.CallbackQuery, state: FSMContext):
        """Processa o botão de cancelar operação."""
        await state.clear()
        await callback_query.message.edit_text("❌ Operação cancelada pelo usuário. Digite /start para iniciar novamente.")
        await callback_query.answer()

    # --- FLUXO FSM: GERAR RÓTULO ---

    # Registra o callback do menu inicial para iniciar o fluxo
    async def register_start_print(self, callback_query: types.CallbackQuery, state: FSMContext):
        await callback_query.answer()
        await self.start_print_flow(callback_query.message, state)

    async def start_print_flow(self, message: types.Message, state: FSMContext):
        """Inicia o fluxo de impressão buscando os templates da API."""
        await message.answer("🔍 Carregando templates de rótulos disponíveis do servidor...")
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{BACKEND_URL}/api/templates")
                
            if response.status_code != 200:
                await message.answer(
                    "⚠️ *Erro no Servidor Backend*:\nNão foi possível obter a lista de templates do portal. "
                    "Verifique se o backend está rodando.",
                    parse_mode=ParseMode.MARKDOWN
                )
                await state.clear()
                return
                
            templates = response.json()
            if not templates:
                await message.answer("⚠️ Nenhum template de rótulo cadastrado no backend.")
                await state.clear()
                return
                
            # Salva os templates no estado para referência posterior
            await state.update_data(templates_list=templates)
            
            # Monta teclado inline com os templates
            builder = InlineKeyboardBuilder()
            builder.button(text="📦 [ TODOS OS RÓTULOS (ZIP) ]", callback_data="label_choice_all")
            
            for index, temp in enumerate(templates):
                # Formata um nome curto para caber no botão
                btn_text = f"{temp['fornecedor']} - {temp['fase'].replace('_', ' ')} ({temp['tipo_racao']})"
                # Limitado a 64 bytes de callback_data no Telegram: usamos o index
                builder.button(text=btn_text, callback_data=f"label_choice_{index}")
                
            builder.button(text="❌ Cancelar", callback_data="cancel_operation")
            builder.adjust(1)
            
            await state.set_state(LabelReprintForm.choosing_label)
            await message.answer(
                "📋 *Selecione qual rótulo você deseja gerar e imprimir*:",
                reply_markup=builder.as_markup(),
                parse_mode=ParseMode.MARKDOWN
            )
            
        except Exception as e:
            logger.error(f"Erro ao conectar ao backend em {BACKEND_URL}: {e}")
            await message.answer(
                f"⚠️ *Erro de Conexão*:\nNão foi possível estabelecer contato com o backend em `{BACKEND_URL}`.\n"
                f"Certifique-se de que o servidor Flask está ativo no Homelab.",
                parse_mode=ParseMode.MARKDOWN
            )
            await state.clear()

    async def process_label_choice(self, callback_query: types.CallbackQuery, state: FSMContext):
        """Processa a escolha do rótulo feita nos botões inline."""
        await callback_query.answer()
        data = callback_query.data
        
        state_data = await state.get_data()
        templates = state_data.get("templates_list", [])
        
        if data == "label_choice_all":
            await state.update_data(emit_all=True, selected_template=None)
            label_desc = "Todos os Rótulos (Arquivo ZIP)"
        else:
            try:
                index = int(data.replace("label_choice_", ""))
                selected = templates[index]
                await state.update_data(emit_all=False, selected_template=selected)
                label_desc = f"{selected['fornecedor']} - {selected['fase'].replace('_', ' ')} ({selected['tipo_racao']})"
            except (ValueError, IndexError):
                await callback_query.message.answer("Opção inválida. Vamos reiniciar. Digite /start.")
                await state.clear()
                return
                
        # Atualiza a mensagem mostrando a escolha e pergunta a data
        await state.update_data(label_desc=label_desc)
        
        # Sugere botões de data rápida (Hoje e Ontem)
        today = datetime.now()
        yesterday = today - timedelta(days=1)
        
        builder = InlineKeyboardBuilder()
        builder.button(text=f"📅 Hoje ({today.strftime('%d/%m')})", callback_data=f"date_{today.strftime('%d-%m-%Y')}")
        builder.button(text=f"📅 Ontem ({yesterday.strftime('%d/%m')})", callback_data=f"date_{yesterday.strftime('%d-%m-%Y')}")
        builder.button(text="❌ Cancelar", callback_data="cancel_operation")
        builder.adjust(2, 1)
        
        await state.set_state(LabelReprintForm.typing_date)
        await callback_query.message.edit_text(
            f"✅ *Opção Selecionada*: {label_desc}\n\n"
            f"📅 *Qual é a data de fabricação do lote?*\n"
            f"Selecione um botão abaixo ou digite no formato *DD/MM/AAAA*:",
            reply_markup=builder.as_markup(),
            parse_mode=ParseMode.MARKDOWN
        )

    # --- PROCESSAMENTO DA DATA ---

    async def process_quick_date(self, callback_query: types.CallbackQuery, state: FSMContext):
        """Processa a data escolhida pelos botões rápidos de data."""
        await callback_query.answer()
        date_str = callback_query.data.replace("date_", "") # formato DD-MM-YYYY
        
        try:
            dt_obj = datetime.strptime(date_str, "%d-%m-%Y")
            await self.save_date_and_proceed(callback_query.message, state, dt_obj)
        except ValueError:
            await callback_query.message.answer("Erro interno ao ler data rápida. Por favor, digite a data no formato DD/MM/AAAA:")

    async def process_typed_date(self, message: types.Message, state: FSMContext):
        """Processa e valida a data digitada pelo usuário."""
        raw_text = message.text.strip()
        
        # Tenta sanitizar e validar formatos comuns (ex: DD/MM/AAAA, DD/MM/AA, DDMMAA, DDMMAAAA)
        dt_obj = None
        
        # Padrão com barras: DD/MM/AAAA ou DD/MM/AA
        match_slash = re.match(r'^(\d{2})/(\d{2})/(\d{2,4})$', raw_text)
        # Padrão corrido: DDMMAA ou DDMMAAAA
        match_clean = re.match(r'^(\d{2})(\d{2})(\d{2,4})$', raw_text)
        
        if match_slash:
            day, month, year = match_slash.groups()
        elif match_clean:
            day, month, year = match_clean.groups()
        else:
            await message.answer(
                "⚠️ *Formato inválido!*\nInsira a data no formato padrão *DD/MM/AAAA* (ex: 30/06/2026):",
                reply_markup=get_cancel_keyboard(),
                parse_mode=ParseMode.MARKDOWN
            )
            return

        # Corrige ano curto (ex: 26 -> 2026)
        if len(year) == 2:
            year = "20" + year
            
        try:
            dt_obj = datetime(int(year), int(month), int(day))
        except ValueError:
            await message.answer(
                "⚠️ *Data calendário inválida!*\nPor favor, insira uma data real (ex: 30/06/2026):",
                reply_markup=get_cancel_keyboard(),
                parse_mode=ParseMode.MARKDOWN
            )
            return

        await self.save_date_and_proceed(message, state, dt_obj)

    async def save_date_and_proceed(self, message: types.Message, state: FSMContext, dt_obj: datetime):
        """Guarda a data validada e passa para a verificação do e-mail do usuário."""
        # Formato esperado pelo Flask backend: YYYY-MM-DD
        backend_date = dt_obj.strftime("%Y-%m-%d")
        user_display_date = dt_obj.strftime("%d/%m/%Y")
        
        await state.update_data(data_fabricacao=backend_date, display_date=user_display_date)
        
        # Verifica se o ID do Telegram já possui e-mail associado
        telegram_id = message.chat.id
        await message.answer("🔄 Verificando cadastro de e-mail...")
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{BACKEND_URL}/api/telegram/user/{telegram_id}")
                
            if response.status_code == 200:
                user_info = response.json()
                saved_email = user_info.get("email")
                
                if saved_email:
                    # E-mail localizado: Dá a sugestão de envio rápido
                    await state.update_data(email=saved_email)
                    
                    builder = InlineKeyboardBuilder()
                    builder.button(text=f"✉️ Sim, enviar para {saved_email}", callback_data="email_confirm_yes")
                    builder.button(text="✏️ Enviar para outro e-mail", callback_data="email_confirm_no")
                    builder.button(text="❌ Cancelar", callback_data="cancel_operation")
                    builder.adjust(1)
                    
                    await state.set_state(LabelReprintForm.confirming_email)
                    await message.answer(
                        f"📧 *Cadastro Localizado*:\n"
                        f"Identificamos que seu Telegram está associado ao e-mail:\n`{saved_email}`.\n\n"
                        f"Deseja utilizar este endereço para receber o rótulo PDF?",
                        reply_markup=builder.as_markup(),
                        parse_mode=ParseMode.MARKDOWN
                    )
                    return
            
            # Se não encontrou e-mail, pede para digitar um
            await self.ask_for_new_email(message, state)
            
        except Exception as e:
            logger.error(f"Erro ao verificar e-mail do telegram {telegram_id}: {e}")
            # Em caso de erro, procedemos perguntando o e-mail para não travar o bot
            await self.ask_for_new_email(message, state)

    # --- FLUXO DE E-MAIL ---

    async def ask_for_new_email(self, message: types.Message, state: FSMContext):
        """Pede para o usuário digitar o e-mail."""
        await state.set_state(LabelReprintForm.typing_email)
        await message.answer(
            "📧 *E-mail de Destino*:\n"
            "Não localizamos um e-mail padrão para o seu ID do Telegram.\n\n"
            "Por favor, digite o e-mail para onde o rótulo deve ser enviado:",
            reply_markup=get_cancel_keyboard(),
            parse_mode=ParseMode.MARKDOWN
        )

    async def process_email_confirmation(self, callback_query: types.CallbackQuery, state: FSMContext):
        """Processa a resposta do usuário à sugestão de e-mail existente."""
        await callback_query.answer()
        choice = callback_query.data
        
        if choice == "email_confirm_yes":
            # Vai direto para a tela de confirmação de geração
            await self.show_final_confirmation(callback_query.message, state)
        else:
            # Pede outro e-mail
            await self.ask_for_new_email(callback_query.message)

    async def process_typed_email(self, message: types.Message, state: FSMContext):
        """Processa e valida o e-mail digitado pelo usuário."""
        email = message.text.strip().lower()
        
        # Regex básico de validação de e-mail
        email_regex = r'^[\w\.-]+@[\w\.-]+\.\w+$'
        if not re.match(email_regex, email):
            await message.answer(
                "⚠️ *E-mail inválido!*\nPor favor, digite um e-mail válido (ex: seu.nome@cvale.com.br):",
                reply_markup=get_cancel_keyboard(),
                parse_mode=ParseMode.MARKDOWN
            )
            return
            
        # Salva o e-mail na base de dados (SQLite) via API Flask de forma assíncrona
        telegram_id = message.chat.id
        username = message.from_user.username
        
        await message.answer("💾 Salvando associação de e-mail na base de dados...")
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                save_res = await client.post(
                    f"{BACKEND_URL}/api/telegram/user",
                    json={
                        "telegram_id": telegram_id,
                        "email": email,
                        "username": username
                    }
                )
                
            if save_res.status_code == 200 and save_res.json().get("success"):
                logger.info(f"Telegram ID {telegram_id} associado com sucesso ao e-mail {email}")
            else:
                logger.warning(f"Não foi possível persistir e-mail na MER para o telegram ID {telegram_id}: {save_res.text}")
        except Exception as e:
            logger.error(f"Erro de conexão ao salvar e-mail do telegram {telegram_id} na base: {e}")

        await state.update_data(email=email)
        await self.show_final_confirmation(message, state)

    # --- TELA FINAL E CONFIRMAÇÃO ---

    async def show_final_confirmation(self, message: types.Message, state: FSMContext):
        """Mostra o resumo da operação e pede confirmação antes de gerar o rótulo."""
        state_data = await state.get_data()
        
        label_desc = state_data.get("label_desc")
        display_date = state_data.get("display_date")
        email = state_data.get("email")
        
        # Calcula o lote zootécnico impresso DDMMAA a partir da data de fabricação
        fabricacao_str = state_data.get("data_fabricacao") # YYYY-MM-DD
        dt_obj = datetime.strptime(fabricacao_str, "%Y-%m-%d")
        lote_impresso = dt_obj.strftime("%d%m%y")
        
        resumo_text = (
            "⚙️ *Confirmação de Geração de Rótulo* ⚙️\n\n"
            f"🏷️ *Rótulo*: {label_desc}\n"
            f"📅 *Data Fabricação*: {display_date}\n"
            f"📦 *Lote Impresso*: `{lote_impresso}`\n"
            f"✉️ *Enviar para*: `{email}`\n\n"
            "Deseja confirmar a geração física do arquivo e o disparo do e-mail?"
        )
        
        builder = InlineKeyboardBuilder()
        builder.button(text="🚀 Confirmar e Gerar", callback_data="generate_confirm")
        builder.button(text="❌ Cancelar", callback_data="cancel_operation")
        builder.adjust(1)
        
        await state.set_state(LabelReprintForm.confirming_generation)
        await message.answer(resumo_text, reply_markup=builder.as_markup(), parse_mode=ParseMode.MARKDOWN)

    async def process_final_generation(self, callback_query: types.CallbackQuery, state: FSMContext):
        """Dispara a geração do rótulo física no backend e envia o e-mail correspondente."""
        await callback_query.answer()
        data = callback_query.data
        
        if data != "generate_confirm":
            await state.clear()
            await callback_query.message.edit_text("❌ Operação cancelada.")
            return
            
        await callback_query.message.edit_text("⏳ *Processando solicitação...*\nGerando PDF de alta qualidade e preparando e-mail...", parse_mode=ParseMode.MARKDOWN)
        
        state_data = await state.get_data()
        emit_all = state_data.get("emit_all", False)
        data_fabricacao = state_data.get("data_fabricacao") # YYYY-MM-DD
        email = state_data.get("email")
        
        try:
            # 1. Dispara Geração de Rótulo no Backend Flask
            async with httpx.AsyncClient(timeout=30.0) as client:
                if emit_all:
                    gen_payload = {"emit_all": True, "data_fabricacao": data_fabricacao}
                else:
                    selected_temp = state_data.get("selected_template")
                    gen_payload = {
                        "emit_all": False,
                        "template_name": selected_temp["pdf"],
                        "data_fabricacao": data_fabricacao
                    }
                    
                logger.info(f"Telegram Bot - Disparando API Geração: {gen_payload}")
                gen_res = await client.post(f"{BACKEND_URL}/api/generate", json=gen_payload)
                
            if gen_res.status_code != 200 or not gen_res.json().get("success"):
                error_detail = gen_res.json().get("error", "Erro desconhecido") if gen_res.status_code == 200 else f"HTTP {gen_res.status_code}"
                await callback_query.message.answer(
                    f"❌ *Falha na Geração do PDF*:\nO servidor backend retornou o seguinte erro:\n`{error_detail}`",
                    parse_mode=ParseMode.MARKDOWN
                )
                await self.ask_for_loop(callback_query.message, state)
                return
                
            gen_data = gen_res.json()
            filename = gen_data.get("filename")
            summary = gen_data.get("summary")
            
            # 2. Dispara Envio do E-mail no Backend Flask
            await callback_query.message.answer("✉️ PDF gerado com sucesso! Iniciando envio do e-mail...")
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                email_payload = {
                    "email": email,
                    "filename": filename,
                    "summary": summary
                }
                logger.info(f"Telegram Bot - Disparando API Envio Email: {email_payload}")
                email_res = await client.post(f"{BACKEND_URL}/api/send-email", json=email_payload)
                
            if email_res.status_code == 200 and email_res.json().get("success"):
                await callback_query.message.answer(
                    f"🎉 *Sucesso!* Rótulo gerado e enviado para `{email}`.\n"
                    f"📂 *Arquivo*: `{filename}`",
                    parse_mode=ParseMode.MARKDOWN
                )
            else:
                error_detail = email_res.json().get("error", "Erro desconhecido") if email_res.status_code == 200 else f"HTTP {email_res.status_code}"
                await callback_query.message.answer(
                    f"⚠️ *PDF Gerado, mas falha no envio do e-mail*:\n`{error_detail}`\n\n"
                    f"Você pode baixar o arquivo diretamente no Portal Web.",
                    parse_mode=ParseMode.MARKDOWN
                )
                
            await self.ask_for_loop(callback_query.message, state)
            
        except Exception as e:
            logger.error(f"Erro no processamento da solicitação do telegram: {e}", exc_info=True)
            await callback_query.message.answer(
                f"❌ *Erro de Conexão com o Backend*:\nOcorreu uma falha ao comunicar com o Homelab:\n`{str(e)}`",
                parse_mode=ParseMode.MARKDOWN
            )
            await self.ask_for_loop(callback_query.message, state)

    # --- LOOP E ENCERRAMENTO ---

    async def ask_for_loop(self, message: types.Message, state: FSMContext):
        """Pergunta se o usuário deseja realizar outra operação ou sair."""
        builder = InlineKeyboardBuilder()
        builder.button(text="🔄 Sim, gerar outro", callback_data="loop_yes")
        builder.button(text="👋 Não, sair", callback_data="loop_no")
        builder.adjust(2)
        
        await state.set_state(LabelReprintForm.loop_decision)
        await message.answer(
            "🤔 *Deseja gerar outro rótulo de ração agora?*",
            reply_markup=builder.as_markup(),
            parse_mode=ParseMode.MARKDOWN
        )

    async def process_loop_decision(self, callback_query: types.CallbackQuery, state: FSMContext):
        """Processa a resposta sobre o reinício do loop."""
        await callback_query.answer()
        choice = callback_query.data
        
        if choice == "loop_yes":
            # Reinicia o fluxo limpando os dados anteriores mas mantendo o estado limpo antes do fluxo começar
            await state.clear()
            await self.start_print_flow(callback_query.message, state)
        else:
            # Despedida e limpa estado
            await state.clear()
            despedida_text = (
                "👋 *Atendimento Finalizado!*\n\n"
                "Obrigado por utilizar o assistente de Rótulos C.Vale.\n"
                "Se precisar de mais alguma coisa, basta enviar /start aqui no chat. "
                "Tenha um ótimo dia de trabalho!"
            )
            await callback_query.message.edit_text(despedida_text, parse_mode=ParseMode.MARKDOWN)

    async def start(self):
        """Inicia o pooling do bot do telegram."""
        logger.info("Telegram Bot iniciando no Homelab...")
        # Inicia Polling
        await self.dp.start_polling(self.bot)

if __name__ == "__main__":
    bot_interface = TelegramInterfaceBot()
    asyncio.run(bot_interface.start())
