import os
import glob
import io
from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas

# Caminho raiz do projeto dinâmico
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

TEMPLATE_DIR = os.path.join(PROJECT_ROOT, "assets/RotulosTemplate")
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "docs/grids")

def generate_grid_overlay(width, height):
    """
    Gera um PDF em memória com uma grade de coordenadas X e Y
    nas dimensões especificadas (width x height).
    O sistema de coordenadas assume origem (0,0) no canto superior esquerdo.
    """
    packet = io.BytesIO()
    can = canvas.Canvas(packet, pagesize=(width, height))
    can.setFont("Helvetica", 8)
    
    # 1. Desenha linhas verticais (marcações de X)
    for x in range(0, int(width), 50):
        can.setStrokeColorRGB(0.85, 0.85, 0.85)  # Cinza muito claro
        can.line(x, 0, x, height)
        can.setFillColorRGB(0.5, 0.5, 0.5)
        # Escreve a coordenada X em três alturas diferentes (em Y da ferramenta)
        can.drawString(x + 2, height - 10, f"X={x}")  # Perto do topo (Y=10 da ferramenta)
        can.drawString(x + 2, height / 2, f"X={x}")   # Meio
        can.drawString(x + 2, 15, f"X={x}")          # Perto do rodapé (Y=height-15 da ferramenta)
        
    # 2. Desenha linhas horizontais (marcações de Y da ferramenta)
    for y_ferramenta in range(0, int(height), 50):
        # Traduz y da ferramenta para o ReportLab
        y_reportlab = height - y_ferramenta
        can.setStrokeColorRGB(0.85, 0.85, 0.85)
        can.line(0, y_reportlab, width, y_reportlab)
        can.setFillColorRGB(0.5, 0.5, 0.5)
        # Escreve o Y que a ferramenta usará (0 no topo, height no rodapé)
        can.drawString(10, y_reportlab + 2, f"Y={y_ferramenta}")
        can.drawString(width / 2, y_reportlab + 2, f"Y={y_ferramenta}")
        can.drawString(width - 40, y_reportlab + 2, f"Y={y_ferramenta}")
        
    # 3. Desenha pontos de referência destacados em vermelho
    can.setFillColorRGB(0.9, 0.2, 0.2)
    can.setStrokeColorRGB(0.9, 0.2, 0.2)
    
    # Grid de círculos de referência principais (coordenadas da ferramenta)
    points = [
        (100, 100), (100, 400), (100, 700),
        (300, 100), (300, 400), (300, 700),
        (500, 100), (500, 400), (500, 700)
    ]
    for px, py_ferramenta in points:
        py_reportlab = height - py_ferramenta
        if px < width and py_reportlab > 0:
            can.circle(px, py_reportlab, 3, fill=1)
            can.drawString(px + 5, py_reportlab + 2, f"({px},{py_ferramenta})")
            
    # 4. Desenha borda externa da folha
    can.setStrokeColorRGB(0.9, 0.1, 0.1)
    can.rect(2, 2, width - 4, height - 4)
    
    can.save()
    packet.seek(0)
    return packet

def process_all_templates():
    """
    Varre a pasta de templates e cria os PDFs de grade correspondentes.
    """
    templates = glob.glob(os.path.join(TEMPLATE_DIR, "*.pdf"))
    if not templates:
        print(f"[Erro] Nenhum arquivo PDF encontrado na pasta {TEMPLATE_DIR}")
        return
        
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    print(f"Iniciando a geração de grades de coordenadas para {len(templates)} templates...")
    
    for template_path in sorted(templates):
        filename = os.path.basename(template_path)
        output_path = os.path.join(OUTPUT_DIR, filename)
        
        try:
            reader = PdfReader(template_path)
            if len(reader.pages) == 0:
                print(f"  [Ignorado] O arquivo {filename} não possui páginas.")
                continue
                
            page = reader.pages[0]
            
            # Transfere a rotação da página para o conteúdo físico para alinhar o aspect ratio
            try:
                page.transfer_rotation_to_content()
            except Exception:
                pass
                
            box = page.mediabox
            width = float(box.width)
            height = float(box.height)
            
            # Gera o overlay
            grid_packet = generate_grid_overlay(width, height)
            grid_reader = PdfReader(grid_packet)
            grid_page = grid_reader.pages[0]
            
            # Mescla com a primeira página do template
            page.merge_page(grid_page)
            
            # Reconstrói o PDF
            writer = PdfWriter()
            writer.add_page(page)
            # Mantém as demais páginas caso existam
            for idx in range(1, len(reader.pages)):
                writer.add_page(reader.pages[idx])
                
            with open(output_path, "wb") as f:
                writer.write(f)
                
            print(f"  [Sucesso] Grade gerada para: {filename} -> {output_path}")
            
        except Exception as e:
            print(f"  [Erro] Falha ao processar o arquivo {filename}: {e}")

if __name__ == "__main__":
    process_all_templates()
