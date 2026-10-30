# Dockerfile Ultra-Leve (Portal de Rótulos de Ração C.Vale)
FROM python:3.11-slim

WORKDIR /app

# Instala apenas dependências enxutas de produção (Sem Pandas, NumPy, OpenPyXL ou Aiogram)
COPY requirements-prod.txt .
RUN pip install --no-cache-dir -r requirements-prod.txt

# Cria diretórios essenciais da aplicação
RUN mkdir -p logs data/processed Export/manuais config assets

# Copia configurações, templates PDF e código-fonte
COPY config/ /app/config/
COPY assets/ /app/assets/
COPY src/ /app/src/
COPY scripts/ /app/scripts/

ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV PORT=5001

EXPOSE 5001

# Gunicorn ultra-leve: 1 worker, 2 threads e reciclagem automática de memória
CMD ["gunicorn", "--bind", "0.0.0.0:5001", "--workers", "1", "--threads", "2", "--timeout", "120", "--max-requests", "500", "--max-requests-jitter", "50", "src.web.app:app"]
