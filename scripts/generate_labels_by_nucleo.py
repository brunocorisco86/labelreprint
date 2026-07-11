import os
import sys
import sqlite3
import logging
import pandas as pd

# Adiciona a raiz do projeto ao sys.path para permitir a importação de src
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from src.core.generator import BatchGenerator

# Configuração do Logger incremental (modo append)
LOGS_DIR = os.path.join(root_dir, "logs")
os.makedirs(LOGS_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOGS_DIR, "geracao_manual.log")

logger = logging.getLogger("geracao_manual")
logger.setLevel(logging.INFO)
if not logger.handlers:
    file_handler = logging.FileHandler(LOG_FILE, mode="a", encoding="utf-8")
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

DATABASE_PATH = os.getenv("DATABASE_PATH", os.path.join(root_dir, "data/processed/entregas_processadas.db"))

def get_nucleos():
    if not os.path.exists(DATABASE_PATH):
        print(f"Erro: Banco de dados não encontrado em: {DATABASE_PATH}. Execute o ETL primeiro.")
        sys.exit(1)
        
    conn = sqlite3.connect(DATABASE_PATH)
    try:
        df_nucleos = pd.read_sql("SELECT DISTINCT R.Nucleo FROM FiltroLotesAtivos F JOIN Regioes R ON F.Fazenda = R.Aviario WHERE R.Nucleo IS NOT NULL ORDER BY R.Nucleo", conn)
        return df_nucleos["Nucleo"].tolist()
    except Exception as e:
        print(f"Erro ao consultar núcleos: {e}")
        sys.exit(1)
    finally:
        conn.close()

def get_lotes_by_nucleo(nucleo):
    conn = sqlite3.connect(DATABASE_PATH)
    try:
        # Busca os lotes vinculados a esse núcleo
        df_lotes = pd.read_sql(
            "SELECT DISTINCT F.FazendaLote, R.NomeFazenda AS [Nome Aviário] FROM FiltroLotesAtivos F JOIN Regioes R ON F.Fazenda = R.Aviario WHERE R.Nucleo = ? AND F.FazendaLote IS NOT NULL", 
            conn, 
            params=(nucleo,)
        )
        return df_lotes
    except Exception as e:
        print(f"Erro ao buscar lotes do núcleo {nucleo}: {e}")
        sys.exit(1)
    finally:
        conn.close()

def get_entregas_count(lotes):
    if not lotes:
        return 0
    conn = sqlite3.connect(DATABASE_PATH)
    try:
        placeholders = ",".join(["?"] * len(lotes))
        query = f"SELECT COUNT(*) as qtd FROM EntregasRacao WHERE FazendaLote IN ({placeholders})"
        cursor = conn.cursor()
        cursor.execute(query, lotes)
        return cursor.fetchone()[0]
    except Exception as e:
        print(f"Erro ao contar entregas: {e}")
        return 0
    finally:
        conn.close()

def main():
    print("====================================================")
    print("   GERAÇÃO DE RÓTULOS POR NÚCLEO ESPECÍFICO (C.VALE) ")
    print("====================================================\n")
    
    logger.info("Iniciando sessão de geração de rótulos por núcleo.")
    nucleos = get_nucleos()
    
    if not nucleos:
        print("Nenhum núcleo encontrado na base de dados.")
        return
        
    print("Núcleos de criação disponíveis:")
    # Formata a exibição em colunas para não ficar gigante na vertical
    for i in range(0, len(nucleos), 6):
        row_nucleos = nucleos[i:i+6]
        row_str = " | ".join([f"Núcleo {n:3d}" for n in row_nucleos])
        print(f"  {row_str}")
    print("")
    
    # 1. Seleciona o núcleo
    selected_nucleo = None
    while True:
        try:
            escolha = input("Digite o número do núcleo desejado (ou 'sair' para encerrar): ").strip()
            if escolha.lower() == 'sair':
                print("Encerrando programa.")
                logger.info("Sessão por núcleo encerrada pelo usuário.")
                return
            nucleo_val = int(escolha)
            if nucleo_val in nucleos:
                selected_nucleo = nucleo_val
                break
            else:
                print(f"Núcleo {nucleo_val} não encontrado. Digite um núcleo da lista.")
        except ValueError:
            print("Entrada inválida. Digite o número inteiro do núcleo.")
            
    # 2. Busca lotes do núcleo
    df_lotes = get_lotes_by_nucleo(selected_nucleo)
    lotes_lista = df_lotes["FazendaLote"].tolist()
    
    print(f"\n----------------------------------------------------")
    print(f"Núcleo Selecionado: {selected_nucleo}")
    print(f"Lotes Vinculados encontrados: {len(lotes_lista)}")
    print(f"Detalhes das Granjas:")
    for _, r in df_lotes.iterrows():
        print(f"  - Lote Composto: {r['FazendaLote']:8s} | Nome: {r['Nome Aviário']}")
    print(f"----------------------------------------------------")
    
    # 3. Conta entregas reais
    total_entregas = get_entregas_count(lotes_lista)
    print(f"Total de entregas de ração registradas para estes lotes: {total_entregas}")
    
    if total_entregas == 0:
        print("\n⚠️ Nenhuma entrega de ração foi registrada na base SQLite para os lotes deste núcleo.")
        print("Certifique-se de que as entregas brutas em data/raw/EntregasRacao contêm dados destes lotes.")
        logger.warning(f"Nenhuma entrega de ração encontrada para o Núcleo {selected_nucleo} (Lotes: {lotes_lista}).")
        return
        
    confirmacao = input("\nDeseja gerar os rótulos consolidados para todos os lotes deste núcleo? (S/n): ").strip().lower()
    if confirmacao == 'n':
        print("Cancelado pelo usuário.")
        logger.info(f"Geração de rótulos do núcleo {selected_nucleo} cancelada pelo usuário.")
        return
        
    # 4. Executa a geração batch filtrada por lote
    print(f"\n[Filtro Núcleo {selected_nucleo}] Inicializando BatchGenerator...")
    logger.info(f"Solicitada geração em lote por Núcleo: Núcleo={selected_nucleo}, Lotes={lotes_lista}, QtdEntregas={total_entregas}")
    
    try:
        # delete_individuals=True para mesclar no PDF do lote e apagar os avulsos das cargas, mantendo a pasta limpa
        generator = BatchGenerator(delete_individuals=True)
        sucesso, erros = generator.generate_all(lotes_filtro=lotes_lista)
        
        success_msg = f"Geração por Núcleo {selected_nucleo} concluída. Sucesso: {sucesso} PDFs | Erros: {erros}."
        logger.info(success_msg)
        
        print("\n====================================================")
        print(f"  ✅ GERAÇÃO CONCLUÍDA PARA O NÚCLEO {selected_nucleo}!")
        print(f"  Sucessos: {sucesso} rótulos de cargas individuais processadas.")
        print(f"  Erros: {erros}")
        print("  Os PDFs unificados e sumários foram salvos na pasta Export/.")
        print("====================================================")
    except Exception as e:
        error_msg = f"Erro na geração em lote para o núcleo {selected_nucleo}: {e}"
        logger.error(error_msg, exc_info=True)
        print(f"\n❌ {error_msg}")

if __name__ == "__main__":
    main()
