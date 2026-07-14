import os
import json
import pytest
import sqlite3
from unittest.mock import patch
from src.web.app import app, DATABASE_PATH
from src.core.data_manager import DataManager

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

@pytest.fixture
def clean_db():
    # Cria uma base SQLite temporária de teste
    test_db = "data/processed/test_telegram.db"
    if os.path.exists(test_db):
        os.remove(test_db)
        
    manager = DataManager(db_path=test_db)
    # Garante a criação das tabelas
    manager.init_telegram_table()
    manager.init_saved_emails_table()
    
    yield manager
    
    if os.path.exists(test_db):
        os.remove(test_db)

def test_data_manager_telegram_user(clean_db):
    manager = clean_db
    
    # 1. Busca usuário que não existe
    email = manager.get_telegram_user(123456789)
    assert email is None
    
    # 2. Salva novo usuário do Telegram
    success = manager.save_telegram_user(123456789, "bruno.conter@cvale.com.br", "brunoconter")
    assert success is True
    
    # 3. Busca usuário cadastrado
    email = manager.get_telegram_user(123456789)
    assert email == "bruno.conter@cvale.com.br"
    
    # 4. Atualiza e-mail do usuário do Telegram existente
    success = manager.save_telegram_user(123456789, "vinicius.duarte@cvale.com.br", "brunoconter")
    assert success is True
    
    email = manager.get_telegram_user(123456789)
    assert email == "vinicius.duarte@cvale.com.br"

def test_data_manager_saved_emails(clean_db):
    manager = clean_db
    
    # 1. Lista de e-mails deve estar vazia inicialmente
    emails = manager.get_saved_emails()
    assert len(emails) == 0
    
    # 2. Salva um e-mail de destinatário
    assert manager.save_saved_email("test.destinatario@cvale.com.br") is True
    
    # 3. Lista e verifica
    emails = manager.get_saved_emails()
    assert len(emails) == 1
    assert "test.destinatario@cvale.com.br" in emails
    
    # 4. Salva e-mail duplicado (deve ignorar)
    assert manager.save_saved_email("test.destinatario@cvale.com.br") is True
    assert len(manager.get_saved_emails()) == 1

def test_flask_endpoints_telegram_user(client):
    telegram_id = 999888777
    email_teste = "telegram.teste@cvale.com.br"
    
    # 1. Consulta usuário inexistente via Flask
    res_get = client.get(f'/api/telegram/user/{telegram_id}')
    assert res_get.status_code == 200
    data_get = res_get.get_json()
    assert data_get['telegram_id'] == telegram_id
    assert data_get['email'] is None
    
    # 2. Cadastra o usuário via Flask (POST)
    payload = {
        "telegram_id": telegram_id,
        "email": email_teste,
        "username": "test_tg_user"
    }
    res_post = client.post('/api/telegram/user', json=payload)
    assert res_post.status_code == 200
    data_post = res_post.get_json()
    assert data_post['success'] is True
    
    # 3. Consulta novamente para confirmar que está na base
    res_get = client.get(f'/api/telegram/user/{telegram_id}')
    assert res_get.status_code == 200
    data_get = res_get.get_json()
    assert data_get['telegram_id'] == telegram_id
    assert data_get['email'] == email_teste
    
    # Limpeza da base para o teste de integração
    conn = sqlite3.connect(DATABASE_PATH)
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM UsuariosTelegram WHERE telegram_id = ?", (telegram_id,))
        conn.commit()
    finally:
        conn.close()

def test_flask_emails_endpoints(client):
    email_teste = "outro.teste.email@cvale.com.br"
    
    # 1. Verifica e-mails cadastrados via GET
    res_get = client.get('/api/emails')
    assert res_get.status_code == 200
    emails = res_get.get_json()
    assert "bruno.conter@cvale.com.br" in emails
    
    # 2. Cadastra um e-mail disparando o envio de e-mail mockado
    with patch('src.web.app.EmailSender') as MockEmailSender:
        mock_sender_instance = MockEmailSender.return_value
        
        # Simulamos o envio que implicitamente salva o e-mail na base
        payload = {
            "email": email_teste,
            "filename": "mock.pdf",
            "summary": {"lote": "123", "fase": "4_CRESCIMENTO", "fornecedor": "CVALE"}
        }
        
        # Criamos o arquivo mock temporário para o teste passar
        os.makedirs("Export/manuais", exist_ok=True)
        mock_pdf_path = "Export/manuais/mock.pdf"
        with open(mock_pdf_path, "w") as f:
            f.write("mock")
            
        try:
            res_send = client.post('/api/send-email', json=payload)
            assert res_send.status_code == 200
            
            # 3. Verifica se o e-mail foi inserido na base de dados
            res_get2 = client.get('/api/emails')
            assert res_get2.status_code == 200
            emails2 = res_get2.get_json()
            assert email_teste in emails2
        finally:
            if os.path.exists(mock_pdf_path):
                os.remove(mock_pdf_path)
                
            # Limpeza do e-mail de teste
            conn = sqlite3.connect(DATABASE_PATH)
            try:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM DestinatariosSalvos WHERE email = ?", (email_teste,))
                conn.commit()
            finally:
                conn.close()
