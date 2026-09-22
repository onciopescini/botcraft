FROM python:3.11-slim
WORKDIR /app
COPY sim/ ./sim/
COPY bots/ ./bots/
COPY runner/ ./runner/
COPY backend/ ./backend/
COPY llm/ ./llm/
COPY sdk/ ./sdk/
RUN pip install --no-cache-dir fastapi uvicorn pydantic python-multipart pyyaml
# Workers: run with --network=none --cpus=1 --memory=256m --pids-limit=64
# API: needs network for OpenRouter gateway (egress only to openrouter.ai)
EXPOSE 8000
CMD ["uvicorn", "backend.api:app", "--host", "0.0.0.0", "--port", "8000"]
