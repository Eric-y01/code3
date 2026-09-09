# 多阶段构建：先构建前端，再把产物与后端合并
FROM node:20-alpine AS frontend
WORKDIR /app
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ ./
RUN npm run build

FROM python:3.11-slim AS backend
WORKDIR /app

# rembg 需要的基础库
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 libglib2.0-0 curl \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt backend/requirements-segmentation.txt ./
RUN pip install --no-cache-dir -r requirements.txt -r requirements-segmentation.txt

COPY backend/ ./backend/
COPY examples/ ./examples/
COPY --from=frontend /app/dist ./frontend/dist

ENV PYTHONUNBUFFERED=1
EXPOSE 8000
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
