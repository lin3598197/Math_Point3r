FROM python:3.11-slim

# 安裝 MediaPipe 必須的系統 C++ 函式庫與 OpenGL 依賴
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgles2 \
    mesa-utils \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 複製並安裝 Python 依賴
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 複製所有後端檔案 (含 .task 模型)
COPY . .

# Render 會自動注入 $PORT 變數，預設給 10000 作為備用
ENV PORT=10000
EXPOSE $PORT

# 啟動 FastAPI，吃環境變數裡的 $PORT
CMD uvicorn server:app --host 0.0.0.0 --port $PORT
