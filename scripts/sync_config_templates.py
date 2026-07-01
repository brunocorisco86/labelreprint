import os
import glob
import json
import re

# Caminho raiz do projeto dinâmico
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

TEMPLATES_DIR = os.path.join(PROJECT_ROOT, "assets/RotulosTemplate")
TEMPLATES_JSON_PATH = os.path.join(PROJECT_ROOT, "config/templates.json")
RESOLVER_JSON_PATH = os.path.join(PROJECT_ROOT, "config/template_resolver.json")

def parse_template_name(filename):
    """
    Analisa o nome do arquivo PDF para extrair Fornecedor/Fábrica, Fase e Tipo de Ração.
    Padrão esperado: {FABRICA}_{FASE}_{TIPO}.pdf
    Exemplo: CVALE_1_PREINICIAL_CM.pdf
    """
    name_without_ext = os.path.splitext(filename)[0]
    parts = name_without_ext.split('_')
    
    if len(parts) >= 3:
        factory = parts[0].upper()
        # A fase pode conter sub-partes se dividida por underscore, ex: 1_PREINICIAL ou 2_INICIAL1
        # O tipo (CM/GG) geralmente é a última parte
        tipo = parts[-1].upper()
        fase = "_".join(parts[1:-1]).upper()
        return factory, fase, tipo
        
    # Fallback caso a nomenclatura saia do padrão
    return "DESCONHECIDO", "OUTRA", "CM"

def sync_configurations():
    print("[Sync] Iniciando sincronização das configurações JSON...")
    
    # 1. Busca todos os templates PDF físicos
    pdf_files = glob.glob(os.path.join(TEMPLATES_DIR, "*.pdf"))
    pdf_filenames = [os.path.basename(f) for f in pdf_files]
    print(f"[Sync] Encontrados {len(pdf_filenames)} arquivos PDF de templates no disco.")
    
    # 2. Carrega templates.json atual para preservar as coordenadas já ajustadas pelo usuário
    existing_templates = {}
    if os.path.exists(TEMPLATES_JSON_PATH):
        try:
            with open(TEMPLATES_JSON_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                existing_templates = data.get("templates", {})
            print(f"[Sync] Carregados {len(existing_templates)} templates já configurados no templates.json.")
        except Exception as e:
            print(f"[Sync] Erro ao carregar templates.json existente (será recriado): {e}")

    # 3. Reconstrói o dicionário de templates preservando o que já existe
    new_templates = {}
    for filename in sorted(pdf_filenames):
        factory, fase, tipo = parse_template_name(filename)
        
        if filename in existing_templates:
            # Preserva a configuração existente do usuário (coordenadas x, y etc.)
            new_templates[filename] = existing_templates[filename]
            # Garante que os metadados estejam atualizados
            new_templates[filename]["fornecedor"] = factory
            new_templates[filename]["fase"] = fase
            new_templates[filename]["tipo_racao"] = tipo
        else:
            # Cria uma entrada padrão zerada se for um novo arquivo de template
            print(f"  [Novo] Adicionando novo template à configuração: {filename}")
            new_templates[filename] = {
                "fornecedor": factory,
                "fase": fase,
                "tipo_racao": tipo,
                "fields": {
                    "data_fabricacao": { "x": 0, "y": 0, "font_size": 10, "align": "center" if factory == "CVALE" else "left" },
                    "lote": { "x": 0, "y": 0, "font_size": 10, "align": "center" if factory == "CVALE" else "left" },
                    "data_validade": { "x": 0, "y": 0, "font_size": 10, "align": "center" if factory == "CVALE" else "left" }
                }
            }
            # Caso especial: Rótulo da LAR não tem validade impressa
            if factory == "LAR":
                new_templates[filename]["fields"].pop("data_validade", None)

    # 4. Salva o templates.json atualizado
    os.makedirs(os.path.dirname(TEMPLATES_JSON_PATH), exist_ok=True)
    with open(TEMPLATES_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump({"templates": new_templates}, f, indent=2, ensure_ascii=False)
    print(f"[Sync] templates.json atualizado com sucesso em: {TEMPLATES_JSON_PATH}")

    # 5. Reconstrói dinamicamente o template_resolver.json com base nos templates do disco
    terceiros = {}
    fallback_cvale = {}
    
    for filename in sorted(pdf_filenames):
        factory, fase, tipo = parse_template_name(filename)
        
        if factory == "CVALE":
            # Organiza a árvore de fallbacks da C.Vale: fase -> tipo -> arquivo
            if fase not in fallback_cvale:
                fallback_cvale[fase] = {}
            fallback_cvale[fase][tipo] = filename
        else:
            # Organiza as regras de terceiros para a fase de crescimento comum (fase 4, tipo CM)
            if fase == "4_CRESCIMENTO" and tipo == "CM":
                terceiros[factory] = filename
                
    # Adiciona COAMO se não houver um template físico (utiliza C.Vale crescimento como fallback padrão)
    if "COAMO" not in terceiros:
        cvale_cresc_comum = fallback_cvale.get("4_CRESCIMENTO", {}).get("CM", "CVALE_4_CRESCIMENTO_CM.pdf")
        terceiros["COAMO"] = cvale_cresc_comum

    resolver_data = {
        "resolver_rules": {
            "terceiros_crescimento_comum": terceiros,
            "fallback_cvale": fallback_cvale
        }
    }
    
    # 6. Salva o template_resolver.json atualizado
    with open(RESOLVER_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(resolver_data, f, indent=2, ensure_ascii=False)
    print(f"[Sync] template_resolver.json atualizado com sucesso em: {RESOLVER_JSON_PATH}")

if __name__ == "__main__":
    sync_configurations()
