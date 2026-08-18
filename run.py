"""啟動入口。

開發模式（內網/本機測試）：
    python run.py
    # 監聽 0.0.0.0:5000，開 debug，程式碼變動自動重載

生產模式（對外/多人使用，關閉 debug 改用 waitress）：
    pip install waitress
    SET FLASK_ENV=production     (Windows cmd)
    $env:FLASK_ENV="production"  (PowerShell)
    python run.py
    # 監聽 0.0.0.0:5000，無 debug，較耐用
"""
import os

from app import create_app

app = create_app()
env = os.environ.get("FLASK_ENV", "development")

if env == "production":
    from waitress import serve
    print("=== 生產模式 (waitress, debug 關閉) ===")
    print("監聽 http://0.0.0.0:5000")
    serve(app, host="0.0.0.0", port=5000, threads=4)
else:
    print("=== 開發模式 (debug on) ===")
    app.run(host="0.0.0.0", port=5000, debug=True)
