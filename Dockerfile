# 使用官方 Python 3.11 slim 映像
FROM python:3.11-slim

# 系統依賴（waitress 不需編譯，這裡只需基礎工具）
WORKDIR /app

# 先複製依賴清單，利用層快取
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 複製程式碼
COPY . .

# 建立非 root 使用者執行（安全）
RUN useradd -m appuser && \
    mkdir -p /data/uploads && \
    chown -R appuser:appuser /data /app
USER appuser

# 用 waitress 生產模式啟動（關 debug）
ENV FLASK_ENV=production
ENV DATABASE_URL=sqlite:////data/app.db
ENV UPLOAD_FOLDER=/data/uploads
EXPOSE 5000

CMD ["python", "run.py"]
