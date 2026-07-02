import os
import sys
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email.mime.image import MIMEImage
from email import encoders
from dotenv import load_dotenv

load_dotenv()

class EmailSender:
    """
    Classe responsável por estruturar e enviar e-mails de notificação
    contendo os rótulos de ração anexados e corpo HTML estilizado.
    """
    def __init__(self):
        self.smtp_server = os.getenv("SMTP_SERVER")
        self.smtp_port = os.getenv("SMTP_PORT")
        self.smtp_username = os.getenv("SMTP_USERNAME")
        self.smtp_password = os.getenv("SMTP_PASSWORD")
        self.from_email = os.getenv("SMTP_FROM_EMAIL")
        self.from_name = os.getenv("SMTP_FROM_NAME", "Portal de Rótulos C.Vale")
        # Raiz do projeto
        self.project_root = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))

    def send_label_email(self, to_email, pdf_path, label_details):
        """
        Envia o rótulo PDF gerado para o e-mail informado.
        """
        if not self.smtp_server or not self.smtp_username or not self.smtp_password:
            raise ValueError("Configurações de SMTP incompletas no arquivo .env (SMTP_SERVER, SMTP_USERNAME, SMTP_PASSWORD)")

        # Valida se o arquivo PDF existe
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"Arquivo PDF para anexo não encontrado em: {pdf_path}")

        # Mensagem raiz MIMEMultipart do tipo 'related' para conter o HTML e a imagem inline CID
        msg = MIMEMultipart('related')
        msg['Subject'] = f"Rótulo de Ração - Lote {label_details.get('lote', '-')} - {label_details.get('fornecedor', '-')} ({label_details.get('fase', '-')})"
        msg['From'] = f"{self.from_name} <{self.from_email}>"
        msg['To'] = to_email

        # Template HTML em Azul Cobalto e Branco
        html_body = f"""
        <html>
        <head>
            <style>
                body {{
                    font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
                    background-color: #f4f6f9;
                    margin: 0;
                    padding: 0;
                    color: #334155;
                }}
                .email-container {{
                    max-width: 600px;
                    margin: 20px auto;
                    background-color: #ffffff;
                    border: 1px solid #e2e8f0;
                    border-radius: 8px;
                    overflow: hidden;
                    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03);
                }}
                .header {{
                    background-color: #1e3a8a; /* Azul Cobalto */
                    padding: 24px;
                    text-align: center;
                }}
                .header img {{
                    height: 48px;
                    border-radius: 6px;
                    background-color: #ffffff;
                    padding: 2px;
                    display: block;
                    margin: 0 auto 10px auto;
                }}
                .header h1 {{
                    color: #ffffff;
                    font-size: 20px;
                    margin: 0;
                    font-weight: 700;
                    letter-spacing: -0.025em;
                }}
                .content {{
                    padding: 30px 24px;
                    line-height: 1.6;
                }}
                .content p {{
                    margin-bottom: 20px;
                    font-size: 15px;
                }}
                .table-summary {{
                    width: 100%;
                    border-collapse: collapse;
                    margin: 24px 0;
                    font-size: 14px;
                }}
                .table-summary th, .table-summary td {{
                    padding: 12px 14px;
                    border-bottom: 1px solid #e2e8f0;
                    text-align: left;
                }}
                .table-summary th {{
                    background-color: #f8fafc;
                    color: #475569;
                    font-weight: 600;
                    width: 40%;
                }}
                .table-summary td {{
                    font-weight: 500;
                    color: #0f172a;
                }}
                .alert-box {{
                    background-color: #eff6ff;
                    border-left: 4px solid #1e3a8a;
                    padding: 16px;
                    border-radius: 4px;
                    font-size: 14px;
                    margin: 24px 0 10px 0;
                    color: #1e40af;
                    line-height: 1.4;
                }}
                .footer {{
                    background-color: #f8fafc;
                    border-top: 1px solid #e2e8f0;
                    padding: 20px;
                    text-align: center;
                    font-size: 12px;
                    color: #64748b;
                    line-height: 1.4;
                }}
            </style>
        </head>
        <body>
            <div class="email-container">
                <div class="header">
                    <img src="cid:logo_cvale" alt="C.Vale Logo">
                    <h1>Portal de Rótulos de Ração</h1>
                </div>
                <div class="content">
                    <p>Olá,</p>
                    <p>O rótulo de ração solicitado foi gerado com sucesso pelo sistema e está anexado a este e-mail pronto para impressão física.</p>
                    
                    <div class="alert-box">
                        <strong>Lote Impresso:</strong> O lote físico gerado a partir da data de fabricação é <strong>{label_details.get('lote', '-')}</strong>.
                    </div>
                    
                    <table class="table-summary">
                        <tr>
                            <th>Fornecedor</th>
                            <td>{label_details.get('fornecedor', '-')}</td>
                        </tr>
                        <tr>
                            <th>Fase da Ração</th>
                            <td>{label_details.get('fase', '-')}</td>
                        </tr>
                        <tr>
                            <th>Tipo de Ração</th>
                            <td>{label_details.get('tipo_racao', '-')}</td>
                        </tr>
                        <tr>
                            <th>Data de Fabricação</th>
                            <td>{label_details.get('data_fabricacao', '-')}</td>
                        </tr>
                        <tr>
                            <th>Data de Validade</th>
                            <td>{label_details.get('data_validade', '-')} ({label_details.get('validade_dias', '-')} dias)</td>
                        </tr>
                    </table>
                    
                    <p>Em caso de dúvidas ou necessidade de recalibração das coordenadas físicas do layout, acesse o painel de administração no portal local.</p>
                </div>
                <div class="footer">
                    C.Vale Cooperativa Agroindustrial &bull; Impressão de Rótulos de Ração<br>
                    Este é um e-mail automático enviado pelo sistema.
                </div>
            </div>
        </body>
        </html>
        """

        # Adiciona parte alternativa para clientes sem HTML
        msgAlternative = MIMEMultipart('alternative')
        msg.attach(msgAlternative)

        msgText = MIMEText(html_body, 'html', 'utf-8')
        msgAlternative.attach(msgText)

        # Anexa o Logo da C.Vale como CID (inline image)
        logo_path = os.path.join(self.project_root, "images/logo_cvale.jpeg")
        if os.path.exists(logo_path):
            with open(logo_path, 'rb') as f:
                msgImage = MIMEImage(f.read())
                msgImage.add_header('Content-ID', '<logo_cvale>')
                msgImage.add_header('Content-Disposition', 'inline', filename='logo_cvale.jpeg')
                msg.attach(msgImage)

        # Anexa o PDF do rótulo
        pdf_name = os.path.basename(pdf_path)
        with open(pdf_path, "rb") as attachment:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(attachment.read())
            encoders.encode_base64(part)
            part.add_header(
                "Content-Disposition",
                f"attachment; filename= {pdf_name}",
            )
            msg.attach(part)

        # Conecta no servidor SMTP e envia o e-mail
        port = int(self.smtp_port) if self.smtp_port else 587
        
        # Detecção de tipo de criptografia (SSL na porta 465 ou TLS na 587)
        if port == 465:
            server = smtplib.SMTP_SSL(self.smtp_server, port)
        else:
            server = smtplib.SMTP(self.smtp_server, port)
            server.starttls()
            
        server.login(self.smtp_username, self.smtp_password)
        server.sendmail(self.from_email, to_email, msg.as_string())
        server.quit()

    def send_sumario_email(self, to_email, fazenda_lote, sumario_text):
        """
        Envia o relatório de sumário de entregas do lote composto por e-mail.
        """
        if not self.smtp_server or not self.smtp_username or not self.smtp_password:
            raise ValueError("Configurações de SMTP incompletas no arquivo .env (SMTP_SERVER, SMTP_USERNAME, SMTP_PASSWORD)")

        msg = MIMEMultipart('related')
        msg['Subject'] = f"Sumário de Entregas - Lote composto {fazenda_lote}"
        msg['From'] = f"{self.from_name} <{self.from_email}>"
        msg['To'] = to_email

        html_body = f"""
        <html>
        <head>
            <style>
                body {{
                    font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
                    background-color: #f4f6f9;
                    margin: 0;
                    padding: 0;
                    color: #334155;
                }}
                .email-container {{
                    max-width: 650px;
                    margin: 20px auto;
                    background-color: #ffffff;
                    border: 1px solid #e2e8f0;
                    border-radius: 8px;
                    overflow: hidden;
                    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03);
                }}
                .header {{
                    background-color: #1e3a8a; /* Azul Cobalto */
                    padding: 20px;
                    text-align: center;
                }}
                .header img {{
                    height: 44px;
                    border-radius: 6px;
                    background-color: #ffffff;
                    padding: 2px;
                    display: block;
                    margin: 0 auto 8px auto;
                }}
                .header h1 {{
                    color: #ffffff;
                    font-size: 18px;
                    margin: 0;
                    font-weight: 700;
                    letter-spacing: -0.025em;
                }}
                .content {{
                    padding: 24px;
                    line-height: 1.6;
                }}
                .content p {{
                    margin-bottom: 16px;
                    font-size: 14px;
                }}
                .sumario-container {{
                    background-color: #0f172a; /* Console escuro no email */
                    color: #38bdf8; /* Azul claro neon */
                    padding: 18px;
                    border-radius: 6px;
                    font-family: 'JetBrains Mono', 'Courier New', Courier, monospace;
                    font-size: 12px;
                    line-height: 1.5;
                    white-space: pre-wrap;
                    margin: 20px 0;
                    border: 1px solid #1e293b;
                    overflow-x: auto;
                }}
                .footer {{
                    background-color: #f8fafc;
                    border-top: 1px solid #e2e8f0;
                    padding: 16px;
                    text-align: center;
                    font-size: 11px;
                    color: #64748b;
                }}
            </style>
        </head>
        <body>
            <div class="email-container">
                <div class="header">
                    <img src="cid:logo_cvale" alt="C.Vale Logo">
                    <h1>Relatório do Lote {fazenda_lote}</h1>
                </div>
                <div class="content">
                    <p>Olá,</p>
                    <p>Segue abaixo o sumário zootécnico e de entregas de ração consolidado para o <strong>Lote composto {fazenda_lote}</strong>, gerado a partir do portal de rótulos.</p>
                    
                    <div class="sumario-container">{sumario_text}</div>
                    
                    <p>O arquivo original está salvo nos diretórios de exportação organizados por extensionista.</p>
                </div>
                <div class="footer">
                    C.Vale Cooperativa Agroindustrial &bull; Impressão de Rótulos de Ração<br>
                    Este é um e-mail automático enviado pelo sistema.
                </div>
            </div>
        </body>
        </html>
        """

        msgAlternative = MIMEMultipart('alternative')
        msg.attach(msgAlternative)
        msgAlternative.attach(MIMEText(html_body, 'html', 'utf-8'))

        # Anexa o Logo da C.Vale como CID
        logo_path = os.path.join(self.project_root, "images/logo_cvale.jpeg")
        if os.path.exists(logo_path):
            with open(logo_path, 'rb') as f:
                msgImage = MIMEImage(f.read())
                msgImage.add_header('Content-ID', '<logo_cvale>')
                msgImage.add_header('Content-Disposition', 'inline', filename='logo_cvale.jpeg')
                msg.attach(msgImage)

        port = int(self.smtp_port) if self.smtp_port else 587
        if port == 465:
            server = smtplib.SMTP_SSL(self.smtp_server, port)
        else:
            server = smtplib.SMTP(self.smtp_server, port)
            server.starttls()
            
        server.login(self.smtp_username, self.smtp_password)
        server.sendmail(self.from_email, to_email, msg.as_string())
        server.quit()
