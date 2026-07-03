import os
import json
import pytest
from unittest.mock import patch
from src.web.app import app, root_dir

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_api_generate_individual(client):
    res_templates = client.get('/api/templates')
    assert res_templates.status_code == 200
    templates = res_templates.get_json()
    assert len(templates) > 0
    
    selected_template = templates[0]['pdf']
    
    payload = {
        "emit_all": False,
        "template_name": selected_template,
        "data_fabricacao": "2026-07-03",
        "data_validade": None
    }
    
    res = client.post('/api/generate', json=payload)
    assert res.status_code == 200
    data = res.get_json()
    assert data['success'] is True
    assert 'filename' in data
    assert 'download_url' in data
    assert data['filename'].endswith('.pdf')
    
    pdf_path = os.path.join(root_dir, "Export/manuais", data['filename'])
    assert os.path.exists(pdf_path)
    
    if os.path.exists(pdf_path):
        os.remove(pdf_path)

def test_api_generate_all_zip(client):
    payload = {
        "emit_all": True,
        "data_fabricacao": "2026-07-03",
        "data_validade": None
    }
    
    res = client.post('/api/generate', json=payload)
    assert res.status_code == 200
    data = res.get_json()
    assert data['success'] is True
    assert 'filename' in data
    assert 'download_url' in data
    assert data.get('is_zip') is True
    assert data['filename'].endswith('.zip')
    
    zip_path = os.path.join(root_dir, "Export/manuais", data['filename'])
    assert os.path.exists(zip_path)
    
    import zipfile
    assert zipfile.is_zipfile(zip_path)
    with zipfile.ZipFile(zip_path, 'r') as zf:
        file_list = zf.namelist()
        assert len(file_list) > 0
        for name in file_list:
            assert name.endswith('.pdf')
            
    if os.path.exists(zip_path):
        os.remove(zip_path)

def test_api_send_email_zip(client):
    payload_gen = {
        "emit_all": True,
        "data_fabricacao": "2026-07-03",
        "data_validade": None
    }
    res_gen = client.post('/api/generate', json=payload_gen)
    assert res_gen.status_code == 200
    data_gen = res_gen.get_json()
    assert data_gen['success'] is True
    zip_filename = data_gen['filename']
    summary = data_gen['summary']
    
    with patch('src.web.app.EmailSender') as MockEmailSender:
        mock_sender_instance = MockEmailSender.return_value
        
        payload_email = {
            "email": "test@cvale.com.br",
            "filename": zip_filename,
            "summary": summary
        }
        
        res_email = client.post('/api/send-email', json=payload_email)
        assert res_email.status_code == 200
        data_email = res_email.get_json()
        assert data_email['success'] is True
        
        expected_zip_path = os.path.join(root_dir, "Export/manuais", zip_filename)
        mock_sender_instance.send_label_email.assert_called_once_with(
            "test@cvale.com.br",
            expected_zip_path,
            summary
        )
        
    zip_path = os.path.join(root_dir, "Export/manuais", zip_filename)
    if os.path.exists(zip_path):
        os.remove(zip_path)
