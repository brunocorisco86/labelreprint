import os
import sys
import json
import sqlite3
import logging
import pandas as pd
import tempfile
import zipfile
import shutil
from datetime import datetime, timedelta
from flask import Flask, render_template, jsonify, request, send_from_directory

# Adiciona a raiz do projeto ao sys.path para permitir a importação de src
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from src.pdf.writer import PDFLabelWriter
from src.core.email_sender import EmailSender

app = Flask(__name__)

# Configuração do Logger incremental (modo append)
LOGS_DIR = os.path.join(root_dir, "logs")
os.makedirs(LOGS_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOGS_DIR, "geracao_manual.log")

DATABASE_PATH = os.getenv("DATABASE_PATH", os.path.join(root_dir, "data/processed/entregas_processadas.db"))

logger = logging.getLogger("geracao_manual")
logger.setLevel(logging.INFO)
# Evita adicionar handlers duplicados caso o app recarregue
if not logger.handlers:
    file_handler = logging.FileHandler(LOG_FILE, mode="a", encoding="utf-8")
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

def load_templates_options():
    resolver_path = os.path.join(root_dir, "config/template_resolver.json")
    if not os.path.exists(resolver_path):
        logger.error(f"Configuração do resolver não encontrada em: {resolver_path}")
        return []
        
    try:
        with open(resolver_path, "r", encoding="utf-8") as f:
            resolver_data = json.load(f)
    except Exception as e:
        logger.error(f"Erro ao ler resolver_config: {e}")
        return []
        
    rules = resolver_data.get("resolver_rules", {})
    options = []
    
    # Processa terceiros_crescimento_comum
    fornecedores_terceiros = rules.get("terceiros_crescimento_comum", {})
    for fornecedor, pdf_name in fornecedores_terceiros.items():
        options.append({
            "fornecedor": fornecedor,
            "fase": "4_CRESCIMENTO",
            "tipo_racao": "CM",
            "pdf": pdf_name
        })
        
    # Processa fallback_cvale
    cvale_phases = rules.get("fallback_cvale", {})
    for fase, tipos in cvale_phases.items():
        for tipo, pdf_name in tipos.items():
            options.append({
                "fornecedor": "CVALE",
                "fase": fase,
                "tipo_racao": tipo,
                "pdf": pdf_name
            })
            
    # Ordena as opções por fornecedor, fase e tipo de ração
    options.sort(key=lambda x: (x["fornecedor"], x["fase"], x["tipo_racao"]))
    return options

def load_shelf_life():
    shelf_life_path = os.path.join(root_dir, "config/shelf_life.json")
    if not os.path.exists(shelf_life_path):
        return {"CVALE": 60, "COPACOL": 90, "AGRIFIRM": 180, "COAMO": 60, "LAR": 180}
    try:
        with open(shelf_life_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"CVALE": 60, "COPACOL": 90, "AGRIFIRM": 180, "COAMO": 60, "LAR": 180}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'),
                               'images/logo_cvale.jpeg', mimetype='image/jpeg')


@app.route('/api/templates')
def get_templates():
    options = load_templates_options()
    return jsonify(options)

@app.route('/api/logs')
def get_logs():
    lines_count = int(request.args.get('lines', 30))
    if not os.path.exists(LOG_FILE):
        return jsonify([])
    try:
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            lines = f.readlines()
        # Remove vazios e retorna na ordem inversa (mais recente primeiro)
        recent_lines = [l.strip() for l in lines[-lines_count:] if l.strip()]
        recent_lines.reverse()
        return jsonify(recent_lines)
    except Exception as e:
        return jsonify([f"Erro ao ler arquivo de logs: {e}"])

@app.route('/api/generate', methods=['POST'])
def generate_label():
    data = request.json
    template_name = data.get('template_name')
    data_fabricacao_str = data.get('data_fabricacao') # formato YYYY-MM-DD
    custom_validade_str = data.get('data_validade') # opcional, formato YYYY-MM-DD
    emit_all = data.get('emit_all', False)
    
    if emit_all:
        if not data_fabricacao_str:
            return jsonify({"success": False, "error": "A data de fabricação é obrigatória."}), 400
            
        try:
            dt_fabricacao = datetime.strptime(data_fabricacao_str, "%Y-%m-%d")
        except ValueError:
            return jsonify({"success": False, "error": "Formato de data de fabricação inválido."}), 400
            
        validade_dias_customizado = None
        if custom_validade_str:
            try:
                dt_validade_custom = datetime.strptime(custom_validade_str, "%Y-%m-%d")
                if dt_validade_custom < dt_fabricacao:
                    return jsonify({"success": False, "error": "A data de validade não pode ser anterior à data de fabricação."}), 400
                validade_dias_customizado = (dt_validade_custom - dt_fabricacao).days
            except ValueError:
                return jsonify({"success": False, "error": "Formato de data de validade inválido."}), 400
                
        options = load_templates_options()
        if not options:
            return jsonify({"success": False, "error": "Nenhum template cadastrado."}), 400
            
        export_dir = os.path.join(root_dir, "Export/manuais")
        os.makedirs(export_dir, exist_ok=True)
        
        temp_dir = tempfile.mkdtemp(dir=export_dir)
        
        lote_impresso = dt_fabricacao.strftime("%d%m%y")
        data_slug = dt_fabricacao.strftime("%d-%m-%Y")
        zip_filename = f"rotulos_todos_FAB_{data_slug}.zip"
        zip_output_path = os.path.join(export_dir, zip_filename)
        
        logger.info(
            f"Web App - Solicitada geração manual de TODOS os templates: "
            f"Fab={dt_fabricacao.strftime('%Y-%m-%d')}, Lote={lote_impresso}, Output ZIP={zip_filename}"
        )
        
        try:
            writer = PDFLabelWriter()
            shelf_life_config = load_shelf_life()
            gerados_count = 0
            
            for opt in options:
                t_name = opt["pdf"]
                fornecedor = opt["fornecedor"]
                fase = opt["fase"]
                tipo_racao = opt["tipo_racao"]
                
                if validade_dias_customizado is not None:
                    validade_dias = validade_dias_customizado
                else:
                    validade_dias = shelf_life_config.get(fornecedor, 60)
                    
                pdf_filename = f"{fornecedor}_{fase}_{tipo_racao}_FAB_{data_slug}.pdf"
                pdf_output_path = os.path.join(temp_dir, pdf_filename)
                
                writer.shelf_life_configs[fornecedor] = validade_dias
                
                writer.write_label(
                    template_name=t_name,
                    data_fabricacao_raw=dt_fabricacao.strftime("%Y-%m-%d"),
                    lote=lote_impresso,
                    shelf_life_days=validade_dias,
                    output_path=pdf_output_path
                )
                gerados_count += 1
                
            with zipfile.ZipFile(zip_output_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, _, files in os.walk(temp_dir):
                    for file in files:
                        if file.endswith('.pdf'):
                            file_path = os.path.join(root, file)
                            zipf.write(file_path, arcname=file)
                            
            logger.info(f"Web App - ZIP de todos os rótulos gerado com sucesso contendo {gerados_count} PDFs: {zip_filename}")
            
            if validade_dias_customizado is not None:
                res_validade = dt_validade_custom.strftime("%d/%m/%Y")
                res_validade_dias = validade_dias_customizado
            else:
                res_validade = "Padrão de cada fabricante"
                res_validade_dias = "-"
                
            return jsonify({
                "success": True,
                "filename": zip_filename,
                "download_url": f"/download/{zip_filename}",
                "is_zip": True,
                "summary": {
                    "fornecedor": "TODOS",
                    "fase": "TODAS",
                    "tipo_racao": "TODAS",
                    "template": "Vários (ZIP)",
                    "data_fabricacao": dt_fabricacao.strftime("%d/%m/%Y"),
                    "data_validade": res_validade,
                    "validade_dias": res_validade_dias,
                    "lote": lote_impresso
                }
            })
            
        except Exception as e:
            error_msg = f"Web App - Erro ao gerar todos os rótulos: {e}"
            logger.error(error_msg, exc_info=True)
            return jsonify({"success": False, "error": str(e)}), 500
        finally:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
                
    else:
        if not template_name or not data_fabricacao_str:
            return jsonify({"success": False, "error": "Template e Data de Fabricação são obrigatórios."}), 400
            
        try:
            dt_fabricacao = datetime.strptime(data_fabricacao_str, "%Y-%m-%d")
        except ValueError:
            return jsonify({"success": False, "error": "Formato de data de fabricação inválido."}), 400
            
        options = load_templates_options()
        selected_option = next((opt for opt in options if opt["pdf"] == template_name), None)
        if not selected_option:
            return jsonify({"success": False, "error": "O template selecionado não é reconhecido."}), 400
            
        fornecedor = selected_option["fornecedor"]
        shelf_life_config = load_shelf_life()
        validade_dias = shelf_life_config.get(fornecedor, 60)
        
        if custom_validade_str:
            try:
                dt_validade = datetime.strptime(custom_validade_str, "%Y-%m-%d")
                if dt_validade < dt_fabricacao:
                    return jsonify({"success": False, "error": "A data de validade não pode ser anterior à data de fabricação."}), 400
                validade_dias = (dt_validade - dt_fabricacao).days
            except ValueError:
                return jsonify({"success": False, "error": "Formato de data de validade inválido."}), 400
        else:
            dt_validade = dt_fabricacao + timedelta(days=validade_dias)
            
        lote_impresso = dt_fabricacao.strftime("%d%m%y")
        
        export_dir = os.path.join(root_dir, "Export/manuais")
        os.makedirs(export_dir, exist_ok=True)
        
        data_slug = dt_fabricacao.strftime("%d-%m-%Y")
        base_name = template_name.replace(".pdf", "")
        filename = f"{base_name}_FAB_{data_slug}.pdf"
        output_path = os.path.join(export_dir, filename)
        
        tipo_label_completo = "Comum" if selected_option["tipo_racao"] == "CM" else "GlobalGap"
        
        logger.info(
            f"Web App - Solicitada geração manual: Template={template_name}, "
            f"Fornecedor={fornecedor}, Fase={selected_option['fase']}, Tipo={tipo_label_completo}, "
            f"Fab={dt_fabricacao.strftime('%Y-%m-%d')}, Venc={dt_validade.strftime('%Y-%m-%d')} ({validade_dias} dias), "
            f"Lote={lote_impresso}, Output={filename}"
        )
        
        try:
            writer = PDFLabelWriter()
            writer.shelf_life_configs[fornecedor] = validade_dias
            
            writer.write_label(
                template_name=template_name,
                data_fabricacao_raw=dt_fabricacao.strftime("%Y-%m-%d"),
                lote=lote_impresso,
                shelf_life_days=validade_dias,
                output_path=output_path
            )
            
            success_msg = f"Web App - Rótulo gerado com sucesso: {filename}"
            logger.info(success_msg)
            
            return jsonify({
                "success": True,
                "filename": filename,
                "download_url": f"/download/{filename}",
                "summary": {
                    "fornecedor": fornecedor,
                    "fase": selected_option["fase"],
                    "tipo_racao": tipo_label_completo,
                    "template": template_name,
                    "data_fabricacao": dt_fabricacao.strftime("%d/%m/%Y"),
                    "data_validade": dt_validade.strftime("%d/%m/%Y"),
                    "validade_dias": validade_dias,
                    "lote": lote_impresso
                }
            })
        except Exception as e:
            error_msg = f"Web App - Erro ao preencher rótulo: {e}"
            logger.error(error_msg, exc_info=True)
            return jsonify({"success": False, "error": str(e)}), 500

@app.route('/download/<filename>')
def download_file(filename):
    directory = os.path.join(root_dir, "Export/manuais")
    return send_from_directory(directory, filename, as_attachment=True)

# ----------------- ROTAS PARA GERAÇÃO POR NÚCLEO -----------------

@app.route('/api/nucleos')
def get_nucleos():
    if not os.path.exists(DATABASE_PATH):
        return jsonify({"error": "Banco de dados relacional não encontrado."}), 404
        
    conn = sqlite3.connect(DATABASE_PATH)
    try:
        df_nucleos = pd.read_sql("SELECT DISTINCT R.Nucleo FROM FiltroLotesAtivos F JOIN Regioes R ON F.Fazenda = R.Aviario WHERE R.Nucleo IS NOT NULL ORDER BY R.Nucleo", conn)
        return jsonify(df_nucleos["Nucleo"].tolist())
    except Exception as e:
        logger.error(f"Erro ao buscar núcleos no SQLite: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()

@app.route('/api/nucleos/<int:nucleo_id>/lotes')
def get_nucleo_lotes(nucleo_id):
    if not os.path.exists(DATABASE_PATH):
        return jsonify({"error": "Banco de dados relacional não encontrado."}), 404
        
    conn = sqlite3.connect(DATABASE_PATH)
    try:
        # Busca lotes do núcleo
        df_lotes = pd.read_sql(
            "SELECT DISTINCT F.FazendaLote, R.NomeFazenda AS [Nome Aviário] FROM FiltroLotesAtivos F JOIN Regioes R ON F.Fazenda = R.Aviario WHERE R.Nucleo = ? AND F.FazendaLote IS NOT NULL", 
            conn, 
            params=(nucleo_id,)
        )
        lotes_lista = df_lotes["FazendaLote"].tolist()
        
        # Conta entregas
        if lotes_lista:
            placeholders = ",".join(["?"] * len(lotes_lista))
            cursor = conn.cursor()
            cursor.execute(f"SELECT COUNT(*) FROM EntregasRacao WHERE FazendaLote IN ({placeholders})", lotes_lista)
            total_entregas = cursor.fetchone()[0]
        else:
            total_entregas = 0
            
        lotes_details = []
        for _, r in df_lotes.iterrows():
            lotes_details.append({
                "lote_composto": r["FazendaLote"],
                "nome_aviario": r["Nome Aviário"]
            })
            
        return jsonify({
            "nucleo": nucleo_id,
            "total_lotes": len(lotes_lista),
            "total_entregas": total_entregas,
            "lotes": lotes_details
        })
    except Exception as e:
        logger.error(f"Erro ao carregar lotes do núcleo {nucleo_id}: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()

@app.route('/api/nucleos/generate', methods=['POST'])
def generate_nucleo_labels():
    data = request.json
    nucleo_id = data.get('nucleo')
    
    if not nucleo_id:
        return jsonify({"success": False, "error": "O campo núcleo é obrigatório."}), 400
        
    if not os.path.exists(DATABASE_PATH):
        return jsonify({"success": False, "error": "Banco de dados relacional não encontrado."}), 500
        
    conn = sqlite3.connect(DATABASE_PATH)
    try:
        df_lotes = pd.read_sql(
            "SELECT DISTINCT F.FazendaLote FROM FiltroLotesAtivos F JOIN Regioes R ON F.Fazenda = R.Aviario WHERE R.Nucleo = ? AND F.FazendaLote IS NOT NULL", 
            conn, 
            params=(nucleo_id,)
        )
        lotes_lista = df_lotes["FazendaLote"].tolist()
    except Exception as e:
        logger.error(f"Erro ao buscar lotes: {e}")
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        conn.close()
        
    if not lotes_lista:
        return jsonify({"success": False, "error": f"Nenhum lote ativo associado ao Núcleo {nucleo_id}."}), 400
        
    logger.info(f"Web App - Solicitada geração em lote do Núcleo={nucleo_id}, Lotes={lotes_lista}")
    
    try:
        # Importação tardia do gerador para evitar problemas de dependência circular
        from src.core.generator import BatchGenerator
        generator = BatchGenerator(delete_individuals=True)
        sucesso, erros = generator.generate_all(lotes_filtro=lotes_lista)
        
        success_msg = f"Web App - Geração do Núcleo {nucleo_id} finalizada. Sucessos: {sucesso} | Erros: {erros}."
        logger.info(success_msg)
        
        return jsonify({
            "success": True,
            "sucesso_count": sucesso,
            "erros_count": erros,
            "message": f"Geração concluída com sucesso para o Núcleo {nucleo_id}! {sucesso} rótulos de cargas processados."
        })
    except Exception as e:
        error_msg = f"Web App - Falha no BatchGenerator para o núcleo {nucleo_id}: {e}"
        logger.error(error_msg, exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500

# ----------------- ROTA DE ENVIO DE E-MAIL E DESTINATÁRIOS -----------------

EMAILS_JSON_PATH = os.path.join(root_dir, "config/destinatarios_salvos.json")

def load_saved_emails():
    os.makedirs(os.path.dirname(EMAILS_JSON_PATH), exist_ok=True)
    default_emails = ["bruno.conter@cvale.com.br", "vinicius.duarte@cvale.com.br"]
    
    if not os.path.exists(EMAILS_JSON_PATH):
        try:
            with open(EMAILS_JSON_PATH, "w", encoding="utf-8") as f:
                json.dump(default_emails, f, ensure_ascii=False, indent=4)
            return default_emails
        except Exception as e:
            logger.error(f"Erro ao criar arquivo de e-mails padrão: {e}")
            return default_emails
            
    try:
        with open(EMAILS_JSON_PATH, "r", encoding="utf-8") as f:
            emails = json.load(f)
            # Garante que os e-mails padrão sempre existam
            for de in default_emails:
                if de not in emails:
                    emails.append(de)
            return emails
    except Exception as e:
        logger.error(f"Erro ao ler e-mails salvos: {e}")
        return default_emails

def save_email(email):
    if not email:
        return
    email = email.strip().lower()
    emails = load_saved_emails()
    if email not in emails:
        emails.append(email)
        try:
            with open(EMAILS_JSON_PATH, "w", encoding="utf-8") as f:
                json.dump(emails, f, ensure_ascii=False, indent=4)
        except Exception as e:
            logger.error(f"Erro ao salvar novo e-mail no JSON: {e}")

@app.route('/api/emails')
def get_emails():
    emails = load_saved_emails()
    return jsonify(emails)

@app.route('/api/send-email', methods=['POST'])
def send_email():
    data = request.json
    to_email = data.get('email')
    filename = data.get('filename') # ex: CVALE_5_ABATE_CM_FAB_30-06-2026.pdf
    summary = data.get('summary')
    
    if not to_email or not filename or not summary:
        return jsonify({"success": False, "error": "Destinatário, arquivo e dados de resumo são obrigatórios."}), 400
        
    # Localiza o PDF em Export/manuais/ ou Export/
    pdf_path = os.path.join(root_dir, "Export/manuais", filename)
    if not os.path.exists(pdf_path):
        pdf_path = os.path.join(root_dir, "Export", filename)
        
    if not os.path.exists(pdf_path):
        return jsonify({"success": False, "error": f"Arquivo PDF '{filename}' não foi encontrado no servidor."}), 404
        
    logger.info(f"Web App - Solicitado envio de e-mail para: {to_email} contendo o arquivo: {filename}")
    
    try:
        sender = EmailSender()
        sender.send_label_email(to_email, pdf_path, summary)
        
        # Salva o e-mail na base JSON se for um e-mail novo
        save_email(to_email)
        
        success_msg = f"Web App - E-mail enviado com sucesso para {to_email} contendo {filename}."
        logger.info(success_msg)
        
        return jsonify({
            "success": True,
            "message": f"E-mail enviado com sucesso para {to_email}!"
        })
    except Exception as e:
        error_msg = f"Web App - Falha ao enviar e-mail para {to_email}: {e}"
        logger.error(error_msg, exc_info=True)
        return jsonify({"success": False, "error": f"Falha no envio de e-mail: {str(e)}"}), 500

@app.route('/api/send-sumario-email', methods=['POST'])
def send_sumario_email():
    data = request.json
    to_email = data.get('email')
    fazenda_lote = data.get('lote')
    sumario_text = data.get('text')
    
    if not to_email or not fazenda_lote or not sumario_text:
        return jsonify({"success": False, "error": "Destinatário, Lote Composto e Texto do Sumário são obrigatórios."}), 400
        
    logger.info(f"Web App - Solicitado envio do sumário do lote {fazenda_lote} para: {to_email}")
    
    try:
        sender = EmailSender()
        sender.send_sumario_email(to_email, fazenda_lote, sumario_text)
        
        # Salva o e-mail na base JSON se for um e-mail novo
        save_email(to_email)
        
        success_msg = f"Web App - Sumário do lote {fazenda_lote} enviado com sucesso para {to_email}."
        logger.info(success_msg)
        
        return jsonify({
            "success": True,
            "message": f"Sumário do lote {fazenda_lote} enviado com sucesso para {to_email}!"
        })
    except Exception as e:
        error_msg = f"Web App - Falha ao enviar sumário do lote {fazenda_lote} para {to_email}: {e}"
        logger.error(error_msg, exc_info=True)
        return jsonify({"success": False, "error": f"Falha no envio de e-mail: {str(e)}"}), 500

# ----------------- NOVOS ENDPOINTS: PRODUTORES E SUMÁRIOS -----------------

@app.route('/api/produtores')
def get_produtores():
    if not os.path.exists(DATABASE_PATH):
        return jsonify({"error": "Banco de dados relacional não encontrado."}), 404
        
    conn = sqlite3.connect(DATABASE_PATH)
    try:
        df_produtores = pd.read_sql(
            "SELECT DISTINCT R.NomeFazenda as nome FROM FiltroLotesAtivos F JOIN Regioes R ON F.Fazenda = R.Aviario WHERE R.NomeFazenda IS NOT NULL ORDER BY R.NomeFazenda", 
            conn
        )
        return jsonify(df_produtores["nome"].tolist())
    except Exception as e:
        logger.error(f"Erro ao buscar produtores no SQLite: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()

@app.route('/api/produtores/lotes')
def get_produtores_lotes():
    produtor = request.args.get('produtor')
    if not produtor:
        return jsonify({"error": "O parâmetro produtor é obrigatório."}), 400
        
    if not os.path.exists(DATABASE_PATH):
        return jsonify({"error": "Banco de dados relacional não encontrado."}), 404
        
    conn = sqlite3.connect(DATABASE_PATH)
    try:
        df_lotes = pd.read_sql(
            "SELECT DISTINCT F.FazendaLote FROM FiltroLotesAtivos F JOIN Regioes R ON F.Fazenda = R.Aviario WHERE R.NomeFazenda = ? AND F.FazendaLote IS NOT NULL ORDER BY F.FazendaLote", 
            conn, 
            params=(produtor,)
        )
        return jsonify(df_lotes["FazendaLote"].tolist())
    except Exception as e:
        logger.error(f"Erro ao buscar lotes do produtor {produtor}: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()

@app.route('/api/sumario')
def get_sumario():
    fazenda_lote = request.args.get('lote')
    if not fazenda_lote:
        return jsonify({"error": "O parâmetro lote é obrigatório."}), 400
        
    if not os.path.exists(DATABASE_PATH):
        return jsonify({"error": "Banco de dados relacional não encontrado."}), 404
        
    conn = sqlite3.connect(DATABASE_PATH)
    try:
        # Busca metadados da entrega para saber o caminho físico
        cursor = conn.cursor()
        cursor.execute(
            "SELECT Extensionista, TipoRacao, NomeFazenda FROM EntregasRacao WHERE FazendaLote = ? LIMIT 1",
            (fazenda_lote,)
        )
        row = cursor.fetchone()
        
        if not row:
            # Caso não tenha entregas reais (pode ser lote inativo ou fora de ordem omitido)
            # Vamos buscar os dados mínimos no Regioes / FiltroLotesAtivos para informar o usuário
            cursor.execute(
                "SELECT R.Extensionista, R.NomeFazenda AS [Nome Aviário] FROM FiltroLotesAtivos F JOIN Regioes R ON F.Fazenda = R.Aviario WHERE F.FazendaLote = ? LIMIT 1",
                (fazenda_lote,)
            )
            row_europa = cursor.fetchone()
            if not row_europa:
                return jsonify({"text": f"Lote composto {fazenda_lote} não foi localizado no cadastro."}), 404
                
            extensionista, nome_produtor = row_europa
            return jsonify({
                "text": f"====================================================\n"
                        f"             CADASTRO: LOTE {fazenda_lote}            \n"
                        f"====================================================\n\n"
                        f"Produtor: {nome_produtor}\n"
                        f"Extensionista: {extensionista}\n\n"
                        f"⚠️ Nenhuma entrega de ração está ativa no SQLite para este lote.\n"
                        f"As cargas podem ter sido omitidas por duplicidade diária, devolução integral,\n"
                        f"ou classificadas como fora de ordem (sobra de lote anterior).\n\n"
                        f"Por conta disso, não há arquivo sumario_entregas.txt gerado para este lote."
            })
            
        extensionista, tipo_racao, nome_produtor = row
        # Capitaliza o diretório (Comum ou GlobalGap)
        tipo_racao_pasta = "Comum" if tipo_racao.upper() in ["CM", "COMUM"] else "GlobalGap"
        
        # Normaliza nomes de pastas para letras maiúsculas com underline
        nome_produtor_slug = nome_produtor.replace(" ", "_").upper()
        extensionista_slug = extensionista.replace(" ", "_").upper()
        
        sumario_filename = "sumario_entregas.txt"
        sumario_path = os.path.join(
            root_dir, 
            "Export", 
            extensionista_slug, 
            tipo_racao_pasta, 
            nome_produtor_slug, 
            fazenda_lote, 
            sumario_filename
        )
        
        if not os.path.exists(sumario_path):
            return jsonify({
                "text": f"====================================================\n"
                        f"             CADASTRO: LOTE {fazenda_lote}            \n"
                        f"====================================================\n\n"
                        f"Produtor: {nome_produtor}\n"
                        f"Extensionista: {extensionista}\n"
                        f"Tipo de Ração: {tipo_racao_pasta}\n\n"
                        f"📂 O arquivo físico do sumário ainda não existe no servidor.\n"
                        f"Caminho: Export/{extensionista_slug}/{tipo_racao_pasta}/{nome_produtor_slug}/{fazenda_lote}/sumario_entregas.txt\n\n"
                        f"👉 Por favor, execute a Geração por Núcleo (Aba 2) ou o pipeline completo\n"
                        f"para renderizar os arquivos deste lote."
            })
            
        # Lê o conteúdo do arquivo
        with open(sumario_path, "r", encoding="utf-8") as f:
            sumario_text = f.read()
            
        return jsonify({"text": sumario_text})
    except Exception as e:
        logger.error(f"Erro ao carregar sumário do lote {fazenda_lote}: {e}")
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)
