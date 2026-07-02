import os
import sys
import json
import logging
from datetime import datetime, timedelta

# Adiciona a raiz do projeto ao sys.path para permitir a importação de src
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from src.pdf.writer import PDFLabelWriter

# Configuração do Logger incremental (modo append)
LOGS_DIR = os.path.join(root_dir, "logs")
os.makedirs(LOGS_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOGS_DIR, "geracao_manual.log")

logger = logging.getLogger("geracao_manual")
logger.setLevel(logging.INFO)
file_handler = logging.FileHandler(LOG_FILE, mode="a", encoding="utf-8")
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

def load_options():
    resolver_path = os.path.join(root_dir, "config/template_resolver.json")
    if not os.path.exists(resolver_path):
        error_msg = f"Arquivo de configuração não encontrado em: {resolver_path}"
        logger.error(error_msg)
        print(f"Erro: {error_msg}")
        sys.exit(1)
        
    with open(resolver_path, "r", encoding="utf-8") as f:
        resolver_data = json.load(f)
        
    rules = resolver_data.get("resolver_rules", {})
    options = []
    
    # Processa terceiros_crescimento_comum
    fornecedores_terceiros = rules.get("terceiros_crescimento_comum", {})
    for fornecedor, pdf_name in fornecedores_terceiros.items():
        options.append({
            "fornecedor": fornecedor,
            "fase": "4_CRESCIMENTO",
            "tipo_racao": "CM",
            "pdf": pdf_name,
            "grupo": "Terceiros Crescimento Comum"
        })
        
    # Processa fallback_cvale
    cvale_phases = rules.get("fallback_cvale", {})
    for fase, tipos in cvale_phases.items():
        for tipo, pdf_name in tipos.items():
            options.append({
                "fornecedor": "CVALE",
                "fase": fase,
                "tipo_racao": tipo,
                "pdf": pdf_name,
                "grupo": "C.Vale Fallback"
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

def main():
    logger.info("Iniciando sessão interativa de geração manual de rótulo.")
    options = load_options()
    shelf_life_config = load_shelf_life()
    
    while True:
        print("\n====================================================")
        print("   GERADOR MANUAL DE RÓTULOS DE RAÇÃO (C.VALE)      ")
        print("====================================================\n")
        
        print("Selecione o tipo de ração pelo número correspondente:")
        for idx, opt in enumerate(options, 1):
            tipo_label = "Comum" if opt["tipo_racao"] == "CM" else "GlobalGap"
            print(f"  {idx:2d}. {opt['fornecedor']} - {opt['fase']} ({tipo_label}) -> {opt['pdf']}")
        print("")
        
        # 1. Seleção do tipo de ração
        escolha_sair = False
        while True:
            try:
                escolha = input("Digite o número da ração selecionada (ou 'sair' para encerrar): ").strip()
                if escolha.lower() == 'sair':
                    escolha_sair = True
                    break
                escolha_idx = int(escolha) - 1
                if 0 <= escolha_idx < len(options):
                    selected = options[escolha_idx]
                    break
                else:
                    print(f"Número inválido. Digite um valor entre 1 e {len(options)}.")
            except ValueError:
                print("Entrada inválida. Por favor, digite um número inteiro.")
                
        if escolha_sair:
            print("Encerrando programa. Obrigado!")
            logger.info("Sessão de geração manual encerrada pelo usuário (na seleção de ração).")
            break
            
        # 2. Seleção da data de fabricação
        while True:
            data_input = input("\nDigite a data de fabricação no formato dd/mm/aaaa (ex: 30/06/2026): ").strip()
            try:
                dt_fabricacao = datetime.strptime(data_input, "%d/%m/%Y")
                break
            except ValueError:
                print("Formato de data inválido. Certifique-se de digitar no padrão DD/MM/AAAA.")
                
        # 3. Processamento de datas e validade
        fornecedor = selected["fornecedor"]
        validade_dias = shelf_life_config.get(fornecedor, 60)
        dt_validade_padrao = dt_fabricacao + timedelta(days=validade_dias)
        lote_impresso = dt_fabricacao.strftime("%d%m%y")
        
        print(f"\nData de validade calculada de fábrica: {dt_validade_padrao.strftime('%d/%m/%Y')} ({validade_dias} dias)")
        escolha_validade = input("Deseja alterar a data de validade para um valor personalizado? (s/N): ").strip().lower()
        
        if escolha_validade == 's':
            while True:
                validade_input = input("Digite a data de validade desejada no formato dd/mm/aaaa: ").strip()
                try:
                    dt_validade = datetime.strptime(validade_input, "%d/%m/%Y")
                    if dt_validade < dt_fabricacao:
                        print("A data de validade não pode ser anterior à data de fabricação.")
                        continue
                    # Calcula a diferença de dias a ser aplicada na geração
                    validade_dias = (dt_validade - dt_fabricacao).days
                    break
                except ValueError:
                    print("Formato de data inválido. Certifique-se de digitar no padrão DD/MM/AAAA.")
        else:
            dt_validade = dt_validade_padrao
            
        tipo_label_completo = "Comum" if selected["tipo_racao"] == "CM" else "GlobalGap"
        print("\n----------------------------------------------------")
        print("Resumo do Rótulo a ser Gerado:")
        print(f"  Fornecedor:          {fornecedor}")
        print(f"  Fase da Ração:       {selected['fase']}")
        print(f"  Tipo da Ração:       {tipo_label_completo}")
        print(f"  Template Base:       {selected['pdf']}")
        print(f"  Data de Fabricação:  {dt_fabricacao.strftime('%d/%m/%Y')}")
        print(f"  Validade Calculada:  {dt_validade.strftime('%d/%m/%Y')} ({validade_dias} dias)")
        print(f"  Lote Impresso:       {lote_impresso}")
        print("----------------------------------------------------")
        
        # 4. Geração do PDF
        export_dir = os.path.join(root_dir, "Export/manuais")
        os.makedirs(export_dir, exist_ok=True)
        
        # Nome do arquivo descritivo com fornecedor, tipo_racao e data
        data_slug = dt_fabricacao.strftime("%d-%m-%Y")
        base_name = selected["pdf"].replace(".pdf", "")
        filename = f"{base_name}_FAB_{data_slug}.pdf"
        output_path = os.path.join(export_dir, filename)
        
        logger.info(
            f"Solicitada geração manual: Template={selected['pdf']}, "
            f"Fornecedor={fornecedor}, Fase={selected['fase']}, Tipo={tipo_label_completo}, "
            f"Fab={dt_fabricacao.strftime('%Y-%m-%d')}, Venc={dt_validade.strftime('%Y-%m-%d')} ({validade_dias} dias), "
            f"Lote={lote_impresso}, Output={filename}"
        )
        
        print(f"\nGerando rótulo...")
        try:
            writer = PDFLabelWriter()
            # Atualiza temporariamente na instância o shelf life do fornecedor para bater com a escolha do usuário
            writer.shelf_life_configs[fornecedor] = validade_dias
            
            writer.write_label(
                template_name=selected["pdf"],
                data_fabricacao_raw=dt_fabricacao.strftime("%Y-%m-%d"),
                lote=lote_impresso,
                shelf_life_days=validade_dias,
                output_path=output_path
            )
            success_msg = f"Rótulo gerado com sucesso e salvo em: {output_path}"
            logger.info(success_msg)
            print("\n✅ Rótulo gerado com sucesso!")
            print(f"📁 Arquivo salvo em: {output_path}")
        except Exception as e:
            error_msg = f"Erro ao gerar o rótulo: {e}"
            logger.error(error_msg, exc_info=True)
            print(f"\n❌ {error_msg}")
            
        print("\n----------------------------------------------------")
        outra = input("Deseja gerar outro rótulo? (S/n): ").strip().lower()
        if outra == 'n':
            print("\nEncerrando programa. Obrigado!")
            logger.info("Sessão de geração manual encerrada pelo usuário no loop de reinício.")
            break
            
if __name__ == "__main__":
    main()
