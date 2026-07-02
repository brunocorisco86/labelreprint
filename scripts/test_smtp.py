import os
import sys
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from dotenv import load_dotenv

# Adiciona a raiz do projeto ao sys.path para permitir importações
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

load_dotenv()

def test_smtp_connection():
    print("====================================================")
    print("   TESTE DE CONEXÃO E AUTENTICAÇÃO SMTP (C.VALE)     ")
    print("====================================================\n")
    
    server_host = os.getenv("SMTP_SERVER")
    server_port = os.getenv("SMTP_PORT")
    username = os.getenv("SMTP_USERNAME")
    password = os.getenv("SMTP_PASSWORD")
    from_email = os.getenv("SMTP_FROM_EMAIL")
    from_name = os.getenv("SMTP_FROM_NAME", "Teste SMTP C.Vale")
    
    print("Variáveis de ambiente lidas:")
    print(f"  - Servidor SMTP: {server_host}")
    print(f"  - Porta: {server_port}")
    print(f"  - Usuário: {username}")
    print(f"  - Remetente: {from_email}")
    print(f"  - Senha: {'*****' if password else 'Não definida'}")
    print("----------------------------------------------------")
    
    if not all([server_host, server_port, username, password, from_email]):
        print("\n❌ Erro: Uma ou mais variáveis do SMTP não estão definidas no arquivo .env.")
        print("Verifique se as chaves SMTP_SERVER, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD e SMTP_FROM_EMAIL estão preenchidas.")
        return False
        
    port = int(server_port)
    
    try:
        print("\nPasso 1: Conectando ao servidor SMTP...")
        if port == 465:
            print("  -> Utilizando conexão segura SSL direta (Porta 465)...")
            server = smtplib.SMTP_SSL(server_host, port, timeout=10)
        else:
            print(f"  -> Utilizando conexão TLS padrão (Porta {port})...")
            server = smtplib.SMTP(server_host, port, timeout=10)
            print("Passo 2: Iniciando protocolo de criptografia STARTTLS...")
            server.starttls()
            
        print("✅ Conectado com sucesso!")
        
        print("\nPasso 3: Tentando autenticação (Login)...")
        server.login(username, password)
        print("✅ Autenticação realizada com sucesso!")
        
        print("\n----------------------------------------------------")
        print("  🎉 AS CREDENCIAIS DO .ENV ESTÃO CORRETAS E ATIVAS!")
        print("----------------------------------------------------")
        
        confirm = input("\nDeseja enviar um e-mail de teste real agora? (S/n): ").strip().lower()
        if confirm == 'n':
            print("Encerrando teste sem enviar e-mail.")
            server.quit()
            return True
            
        to_email = input(f"Digite o e-mail de destino (padrão: {username}): ").strip()
        if not to_email:
            to_email = username
            
        print(f"\nPasso 4: Enviando e-mail de teste para {to_email}...")
        
        # Constrói mensagem de teste utilizando o template institucional simplificado
        msg = MIMEMultipart('related')
        msg['Subject'] = "Teste SMTP com Sucesso - Sistema de Reimpressão C.Vale"
        msg['From'] = f"{from_name} <{from_email}>"
        msg['To'] = to_email
        
        html_content = """
        <html>
        <body style="font-family: Arial, sans-serif; background-color: #f4f6f9; padding: 20px; margin: 0;">
            <div style="max-width: 600px; margin: 0 auto; background-color: #ffffff; border: 1px solid #e2e8f0; border-radius: 8px; overflow: hidden; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);">
                <div style="background-color: #1e3a8a; padding: 24px; text-align: center; color: #ffffff;">
                    <h2 style="margin: 0; font-size: 20px;">Conexão SMTP Ativa!</h2>
                </div>
                <div style="padding: 30px; line-height: 1.6; color: #334155; font-size: 15px;">
                    <p>Olá,</p>
                    <p>Este é um e-mail de teste automático enviado para validar as credenciais do servidor SMTP no arquivo <code>.env</code> do <strong>Sistema de Reimpressão de Rótulos C.Vale</strong>.</p>
                    <p>Se você recebeu esta mensagem, significa que a conexão SMTP, a criptografia e a autenticação estão funcionando perfeitamente e o envio de rótulos por e-mail já está pronto para uso operacional!</p>
                </div>
                <div style="background-color: #f8fafc; padding: 15px; text-align: center; font-size: 11px; color: #64748b; border-top: 1px solid #e2e8f0;">
                    C.Vale Cooperativa Agroindustrial &bull; Teste SMTP
                </div>
            </div>
        </body>
        </html>
        """
        
        msgAlternative = MIMEMultipart('alternative')
        msg.attach(msgAlternative)
        msgAlternative.attach(MIMEText(html_content, 'html', 'utf-8'))
        
        # Tenta embutir o logo
        logo_path = os.path.join(root_dir, "images/logo_cvale.jpeg")
        if os.path.exists(logo_path):
            try:
                # Modifica o HTML para incluir a imagem inline se ela existir
                html_with_logo = html_content.replace(
                    '<h2 style="margin: 0; font-size: 20px;">Conexão SMTP Ativa!</h2>',
                    '<img src="cid:logo_cvale" alt="C.Vale Logo" style="height:44px; margin-bottom:12px; background:#fff; padding:2px; border-radius:4px;"><h2 style="margin: 0; font-size: 20px;">Conexão SMTP Ativa!</h2>'
                )
                # Remove o attachment anterior e adiciona o novo HTML com imagem
                msgAlternative.get_payload().clear()
                msgAlternative.attach(MIMEText(html_with_logo, 'html', 'utf-8'))
                
                with open(logo_path, 'rb') as f:
                    msgImage = MIMEImage(f.read())
                    msgImage.add_header('Content-ID', '<logo_cvale>')
                    msgImage.add_header('Content-Disposition', 'inline', filename='logo_cvale.jpeg')
                    msg.attach(msgImage)
            except Exception as le:
                print(f"  (Aviso: Não foi possível anexar o logo inline: {le})")
                
        server.sendmail(from_email, to_email, msg.as_string())
        server.quit()
        print("\n✅ E-mail de teste enviado com sucesso! Verifique a sua caixa de entrada.")
        return True
        
    except smtplib.SMTPAuthenticationError:
        print("\n❌ Erro de Autenticação: Usuário ou senha incorretos.")
        print("  - Verifique se o e-mail de login e a senha estão corretos no arquivo .env.")
        print("  - Se estiver utilizando Gmail, certifique-se de usar uma 'Senha de Aplicativo' em vez da sua senha de login padrão.")
        return False
    except smtplib.SMTPConnectError:
        print("\n❌ Erro de Conexão: Não foi possível conectar ao servidor SMTP.")
        print("  - Verifique se o endereço do servidor SMTP e a porta no .env estão corretos.")
        print("  - Certifique-se de que sua rede/firewall não está bloqueando conexões de saída na porta especificada.")
        return False
    except Exception as e:
        print(f"\n❌ Falha ao processar teste SMTP: {e}")
        return False

if __name__ == "__main__":
    test_smtp_connection()
