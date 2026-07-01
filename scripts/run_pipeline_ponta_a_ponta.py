import os
import sys
import time
import shutil
import logging
from scripts.sync_config_templates import sync_configurations
from scripts.generate_all_grids import process_all_templates
from src.core.data_manager import DataManager
from src.core.generator import BatchGenerator

DATABASE_PATH = os.getenv("DATABASE_PATH", "data/processed/entregas_processadas.db")
EXPORT_DIR = os.getenv("EXPORT_DIR", "Export")
LOGS_DIR = "logs"
LOG_FILE = os.path.join(LOGS_DIR, "pipeline_ponta_a_ponta.log")

class LoggerWriter:
    """
    Wrapper para redirecionar o stdout/stderr para o console e o arquivo de log ao mesmo tempo.
    """
    def __init__(self, console_stream, file_stream):
        self.console = console_stream
        self.file = file_stream

    def write(self, message):
        self.console.write(message)
        self.file.write(message)
        self.file.flush()

    def flush(self):
        self.console.flush()
        self.file.flush()

def main():
    # Parsing manual e simplificado de argumentos
    tipo_filtro = None
    if "--tipo" in sys.argv:
        try:
            idx = sys.argv.index("--tipo")
            val = sys.argv[idx + 1].upper()
            if val in ["GG", "CM"]:
                tipo_filtro = val
        except (ValueError, IndexError):
            pass

    # 1. Configura a pasta de logs e o arquivo de log (modo 'w' garante apenas a última execução)
    os.makedirs(LOGS_DIR, exist_ok=True)
    log_file = open(LOG_FILE, "w", encoding="utf-8")
    
    # Redireciona o stdout e stderr para o console e arquivo simultaneamente
    original_stdout = sys.stdout
    original_stderr = sys.stderr
    sys.stdout = LoggerWriter(original_stdout, log_file)
    sys.stderr = LoggerWriter(original_stderr, log_file)
    
    try:
        print("=========================================================================")
        print("🚀 PIPELINE DE REIMPRESSÃO DE RÓTULOS C.VALE - EXECUÇÃO DE PONTA A PONTA")
        if tipo_filtro:
            print(f"   [Filtro de Tipo Ativo: {'GlobalGap' if tipo_filtro == 'GG' else 'Comum'}]")
        print("=========================================================================")
        print(f"[Logs] Gravando registro consolidado da execução em: {LOG_FILE}\n")
        
        pipeline_start_time = time.time()
        
        # -----------------------------------------------------------------------
        # ETAPA 1: Configuração e Sincronização de Templates
        # -----------------------------------------------------------------------
        print("\n-------------------------------------------------------------------------")
        print("📁 ETAPA 1: Sincronização das Configurações de Templates")
        print("-------------------------------------------------------------------------")
        t0 = time.time()
        try:
            sync_configurations()
            t_sync = time.time() - t0
            print(f"✔️ Etapa 1 concluída com sucesso em {t_sync:.2f} segundos.")
        except Exception as e:
            print(f"❌ Erro crítico na Etapa 1 (Sincronização): {e}")
            raise e
            
        # -----------------------------------------------------------------------
        # ETAPA 2: Aplicação das Grades de Coordenadas (Grids)
        # -----------------------------------------------------------------------
        print("\n-------------------------------------------------------------------------")
        print("📏 ETAPA 2: Geração das Grades Milimetradas de Calibração (Docs/Grids)")
        print("-------------------------------------------------------------------------")
        t0 = time.time()
        try:
            process_all_templates()
            t_grids = time.time() - t0
            print(f"✔️ Etapa 2 concluída com sucesso em {t_grids:.2f} segundos.")
        except Exception as e:
            print(f"❌ Erro crítico na Etapa 2 (Geração de Grades): {e}")
            raise e

        # -----------------------------------------------------------------------
        # ETAPA 3: Geração da MER e Execução do ETL
        # -----------------------------------------------------------------------
        print("\n-------------------------------------------------------------------------")
        print("⚙️ ETAPA 3: Materialização do Modelo Físico (MER) e Processamento do ETL")
        print("-------------------------------------------------------------------------")
        t0 = time.time()
        try:
            print("[ETL] Instanciando DataManager e validando arquivos brutos (raw)...")
            manager = DataManager(db_path=DATABASE_PATH)
            print("[ETL] Criando esquemas lógicos e processando tabelas Fato/Dimensões...")
            manager.run_etl()
            t_etl = time.time() - t0
            print(f"✔️ Etapa 3 concluída com sucesso em {t_etl:.2f} segundos.")
        except Exception as e:
            print(f"❌ Erro crítico na Etapa 3 (ETL/MER): {e}")
            raise e

        # -----------------------------------------------------------------------
        # ETAPA 4: Geração Retroativa e Mesclagem de PDFs de Rótulos (Produção)
        # -----------------------------------------------------------------------
        print("\n-------------------------------------------------------------------------")
        print("🖨️ ETAPA 4: Geração de Rótulos Retroativos e Consolidado Unificado (Produção)")
        print("-------------------------------------------------------------------------")
        t0 = time.time()
        try:
            # Limpa resíduos anteriores da pasta Export (mantém apenas AmostrasTemplates se existir)
            print(f"[Produção] Limpando pasta de exportação para nova execução: {EXPORT_DIR}...")
            if os.path.exists(EXPORT_DIR):
                for filename in os.listdir(EXPORT_DIR):
                    file_path = os.path.join(EXPORT_DIR, filename)
                    if filename == "AmostrasTemplates":
                        continue
                    if os.path.isdir(file_path):
                        shutil.rmtree(file_path)
                    else:
                        os.remove(file_path)
                print("[Produção] Pasta de exportação limpa com sucesso.")
            
            # Instancia o gerador com delete_individuals=True para gerar apenas o PDF unificado + Sumário TXT
            print("[Produção] Instanciando o gerador em lote (Modo: Apenas PDF Unificado Comprimido)...")
            generator = BatchGenerator(db_path=DATABASE_PATH, export_dir=EXPORT_DIR, delete_individuals=True)
            
            # Executa a geração em produção (toda a base)
            success, errors = generator.generate_all(tipo_racao_filtro=tipo_filtro)
            t_gen = time.time() - t0
            print(f"✔️ Etapa 4 concluída com sucesso em {t_gen:.2f} segundos.")
        except Exception as e:
            print(f"❌ Erro crítico na Etapa 4 (Geração de PDFs): {e}")
            raise e

        # -----------------------------------------------------------------------
        # RESUMO FINAL DO PIPELINE
        # -----------------------------------------------------------------------
        pipeline_elapsed = time.time() - pipeline_start_time
        print("\n=========================================================================")
        print("🏆 PIPELINE EXECUTADO COM SUCESSO DE PONTA A PONTA!")
        print("=========================================================================")
        print(f"Tempo total do Pipeline: {pipeline_elapsed:.2f} segundos")
        print(f"  - Sincronização    : {t_sync:.2f}s")
        print(f"  - Grades (Grids)   : {t_grids:.2f}s")
        print(f"  - ETL & Modelagem  : {t_etl:.2f}s")
        print(f"  - Geração Rótulos  : {t_gen:.2f}s")
        print("-------------------------------------------------------------------------")
        print(f"Rótulos Consolidados Gerados : {success}")
        print(f"Erros de Geração             : {errors}")
        if tipo_filtro:
            print(f"Filtro de Tipo Aplicado      : {tipo_filtro}")
        print(f"Pasta de Saída (Export)      : {EXPORT_DIR}/")
        print(f"Arquivo de Log Completo      : {LOG_FILE}")
        print("=========================================================================")

    except Exception as e:
        print(f"\n❌ Falha na execução do pipeline de ponta a ponta: {e}")
        
    finally:
        # Restaura os handlers padrão de saída do console
        sys.stdout = original_stdout
        sys.stderr = original_stderr
        log_file.close()

if __name__ == "__main__":
    main()
