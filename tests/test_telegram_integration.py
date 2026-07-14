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
    # Garante a criação da tabela UsuariosTelegram
    manager.init_telegram_table()
    
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

def test_flask_endpoints_telegram_user(client):
    # Usando o banco padrão do Flask de testes ou mockando a base
    # Para simplificar o teste de integração, faremos chamadas à API
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
