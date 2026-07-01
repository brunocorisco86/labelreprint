import os
import json
import io
from datetime import datetime, timedelta
from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from dotenv import load_dotenv

load_dotenv()

TEMPLATES_CONFIG_PATH = "config/templates.json"
TEMPLATES_DIR = os.getenv("TEMPLATES_DIR", "assets/RotulosTemplate")

class PDFLabelWriter:
    """
    Classe responsável por escrever as informações do lote, data de fabricação e validade
    sobre os templates PDF originais usando reportlab e pypdf.
    """

    def __init__(self, config_path=None, templates_dir=None):
        self.config_path = config_path or TEMPLATES_CONFIG_PATH
        self.templates_dir = templates_dir or TEMPLATES_DIR
        self.configs = self._load_config()
        self.shelf_life_path = "config/shelf_life.json"
        self.shelf_life_configs = self._load_shelf_life()

    def _load_config(self):
        if not os.path.exists(self.config_path):
            raise FileNotFoundError(f"Configuração de templates não encontrada em: {self.config_path}")
        with open(self.config_path, "r", encoding="utf-8") as f:
            return json.load(f).get("templates", {})

    def _load_shelf_life(self):
        if not os.path.exists(self.shelf_life_path):
            return {"CVALE": 60, "COPACOL": 90, "AGRIFIRM": 180, "COAMO": 60}
        try:
            with open(self.shelf_life_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {"CVALE": 60, "COPACOL": 90, "AGRIFIRM": 180, "COAMO": 60}

    def calculate_dates(self, data_fabricacao_str, shelf_life_days):
        """
        Recebe a data de fabricação (em formato YYYY-MM-DD ou DD/MM/YYYY)
        e calcula as datas formatadas de fabricação e vencimento.
        """
        # Normaliza a data de fabricação
        try:
            if "-" in data_fabricacao_str:
                dt_fab = datetime.strptime(data_fabricacao_str, "%Y-%m-%d")
            else:
                dt_fab = datetime.strptime(data_fabricacao_str, "%d/%m/%Y")
        except Exception as e:
            raise ValueError(f"Formato de data de fabricação inválido: {data_fabricacao_str}. Use YYYY-MM-DD ou DD/MM/YYYY.")

        # Calcula vencimento
        dt_venc = dt_fab + timedelta(days=shelf_life_days)
        
        return dt_fab.strftime("%d/%m/%Y"), dt_venc.strftime("%d/%m/%Y")

    def write_label(self, template_name, data_fabricacao_raw, lote, shelf_life_days, output_path):
        """
        Gera o rótulo preenchido e salva em output_path.
        """
        # 1. Verifica se o template existe na configuração e no disco
        if template_name not in self.configs:
            raise KeyError(f"Template '{template_name}' não mapeado no arquivo de configuração templates.json")
            
        template_path = os.path.join(self.templates_dir, template_name)
        if not os.path.exists(template_path):
            raise FileNotFoundError(f"Arquivo PDF do template não encontrado: {template_path}")
            
        # 2. Determina o shelf life correto (prioriza o JSON de shelf life por fabricante)
        fornecedor = self.configs.get(template_name, {}).get("fornecedor")
        resolved_shelf_life = self.shelf_life_configs.get(fornecedor)
        if resolved_shelf_life is None:
            resolved_shelf_life = shelf_life_days if shelf_life_days is not None else 60
            
        # 3. Calcula as datas formatadas
        fab_str, venc_str = self.calculate_dates(data_fabricacao_raw, resolved_shelf_life)
        
        # 3. Lê as dimensões do PDF original
        reader = PdfReader(template_path)
        if len(reader.pages) == 0:
            raise ValueError(f"O template PDF {template_name} está vazio.")
            
        # Vamos preencher a primeira página
        page = reader.pages[0]
        
        # Transfere a rotação da página para o conteúdo físico para alinhar o aspect ratio
        try:
            page.transfer_rotation_to_content()
        except Exception:
            pass
            
        box = page.mediabox
        width = float(box.width)
        height = float(box.height)
        
        # 4. Gera o overlay com reportlab em memória
        packet = io.BytesIO()
        can = canvas.Canvas(packet, pagesize=(width, height))
        
        # Carrega os mapeamentos de campos para este template
        tmpl_config = self.configs[template_name]
        fields = tmpl_config.get("fields", {})
        
        for field_name, coord in fields.items():
            x = coord["x"]
            # Traduz Y do JSON (Y=0 no topo) para o ReportLab (Y=0 embaixo)
            y = height - coord["y"]
            font_size = coord.get("font_size", 10)
            align = coord.get("align", "left")
            
            # Define o valor textual do campo
            if field_name == "data_fabricacao":
                value = fab_str
            elif field_name == "lote":
                # O lote impresso deve ser a data de fabricação no formato DDMMAA (ex: 300626)
                try:
                    dt_obj = datetime.strptime(fab_str, "%d/%m/%Y")
                    value = dt_obj.strftime("%d%m%y")
                except Exception:
                    value = str(lote)
            elif field_name == "data_validade":
                value = venc_str
            else:
                continue
                
            can.setFont("Helvetica-Bold", font_size)
            
            # Tratamento de alinhamento
            if align == "center":
                can.drawCentredString(x, y, value)
            elif align == "right":
                can.drawRightString(x, y, value)
            else:
                can.drawString(x, y, value)
                
        can.save()
        packet.seek(0)
        
        # 5. Mescla o overlay com o template
        overlay_reader = PdfReader(packet)
        overlay_page = overlay_reader.pages[0]
        page.merge_page(overlay_page)
        
        # 6. Salva o PDF gerado
        writer = PdfWriter()
        writer.add_page(page)
        
        # Se o PDF original possuía mais páginas (como COPACOL), nós mantemos as demais intactas
        # COPACOL_4_CRESCIMENTO_CM.pdf possui 2 páginas, por exemplo.
        for i in range(1, len(reader.pages)):
            writer.add_page(reader.pages[i])
            
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "wb") as f:
            writer.write(f)

if __name__ == "__main__":
    # Teste rápido de geração
    writer = PDFLabelWriter()
    try:
        test_out = "scripts/output/test_label_cvale.pdf"
        writer.write_label(
            template_name="CVALE_5_ABATE_CM.pdf",
            data_fabricacao_raw="2026-06-30",
            lote="58",
            shelf_life_days=60,
            output_path=test_out
        )
        print(f"Rótulo de teste gerado com sucesso em: {test_out}")
    except Exception as e:
        print("Erro no teste:", e)
