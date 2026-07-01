import os
import glob
from pypdf import PdfReader

def inspect_templates():
    files = glob.glob("assets/RotulosTemplate/*.pdf")
    print(f"Inspecionando {len(files)} templates PDF:")
    print("-" * 70)
    print(f"{'Nome do Arquivo':<35} | {'Págs':<5} | {'Largura':<8} | {'Altura':<8} | {'Rot':<5}")
    print("-" * 70)
    
    for f in sorted(files):
        try:
            reader = PdfReader(f)
            num_pages = len(reader.pages)
            if num_pages > 0:
                page = reader.pages[0]
                box = page.mediabox
                width = float(box.width)
                height = float(box.height)
                rotation = page.rotation
                filename = os.path.basename(f)
                print(f"{filename:<35} | {num_pages:<5} | {width:<8.2f} | {height:<8.2f} | {rotation:<5}")
            else:
                print(f"{os.path.basename(f):<35} | Vazio")
        except Exception as e:
            print(f"Erro ao ler {f}: {e}")

if __name__ == "__main__":
    inspect_templates()
