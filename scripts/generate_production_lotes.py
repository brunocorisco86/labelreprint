import os
import sys
import time
import shutil
from src.core.generator import BatchGenerator

DATABASE_PATH = os.getenv("DATABASE_PATH", "data/processed/entregas_processadas.db")
EXPORT_DIR = os.getenv("EXPORT_DIR", "Export")
LOGS_DIR = "logs"
LOG_FILE = os.path.join(LOGS_DIR, "geracao_producao.log")

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

    # 1. Configura a pasta de logs e o arquivo de log (modo 'w' garante apenas uma cópia - a última)
    os.makedirs(LOGS_DIR, exist_ok=True)
    log_file = open(LOG_FILE, "w", encoding="utf-8")
    
    # Redireciona o stdout e stderr para o console e arquivo simultaneamente
    original_stdout = sys.stdout
    original_stderr = sys.stderr
    sys.stdout = LoggerWriter(original_stdout, log_file)
    sys.stderr = LoggerWriter(original_stderr, log_file)
    
    try:
        print("=========================================================================")
        print("🚀 INICIANDO GERAÇÃO DE PRODUÇÃO DE RÓTULOS retroativos (C.VALE)")
        if tipo_filtro:
            print(f"   [Filtro de Tipo Ativo: {'GlobalGap' if tipo_filtro == 'GG' else 'Comum'}]")
        print("=========================================================================")
        print(f"[Logs] Gravando cópia da execução em: {LOG_FILE}\n")
        
        if not os.path.exists(DATABASE_PATH):
            print(f"Erro: Banco de dados processado não encontrado em {DATABASE_PATH}.")
            print("Por favor, execute o ETL primeiro (venv/bin/python3 src/core/data_manager.py).")
            return
            
        start_time = time.time()
        
        # 2. Limpar a pasta Export para evitar resíduos das execuções de testes
        print(f"[Produção] Limpando pasta de exportação: {EXPORT_DIR}...")
        if os.path.exists(EXPORT_DIR):
            try:
                for filename in os.listdir(EXPORT_DIR):
                    file_path = os.path.join(EXPORT_DIR, filename)
                    if filename == "AmostrasTemplates":
                        continue
                    if os.path.isdir(file_path):
                        shutil.rmtree(file_path)
                    else:
                        os.remove(file_path)
                print("[Produção] Pasta de exportação limpa com sucesso.")
            except Exception as e:
                print(f"[Aviso] Erro parcial ao limpar pasta Export: {e}")
                
        # 3. Instancia o BatchGenerator com a flag delete_individuals=True
        print("[Produção] Instanciando o gerador em lote (Modo: Apenas PDF Unificado Comprimido)...")
        generator = BatchGenerator(db_path=DATABASE_PATH, export_dir=EXPORT_DIR, delete_individuals=True)
        
        # 4. Executa a geração para todas as entregas do banco (sem limite)
        success, errors = generator.generate_all(tipo_racao_filtro=tipo_filtro)
        elapsed_time = time.time() - start_time
        
        print("\n=========================================================================")
        print("✅ EXECUÇÃO DE GERAÇÃO CONCLUÍDA")
        print("=========================================================================")
        print(f"Tempo total gasto      : {elapsed_time:.2f} segundos")
        print(f"Rótulos gerados (total): {success}")
        print(f"Erros de geração       : {errors}")
        if tipo_filtro:
            print(f"Filtro de Tipo Aplicado: {tipo_filtro}")
        print(f"Resultado final salvo em: {EXPORT_DIR}/")
        print(f"Log de diagnóstico em  : {LOG_FILE}")
        print("=========================================================================")
        
    except Exception as e:
        print(f"\n❌ Erro crítico durante a geração de produção: {e}")
        
    finally:
        # Restaura streams originais e fecha arquivo de log
        sys.stdout = original_stdout
        sys.stderr = original_stderr
        log_file.close()

if __name__ == "__main__":
    main()
