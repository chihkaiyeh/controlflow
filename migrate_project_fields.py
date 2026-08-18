"""專案欄位擴充遷移：給舊 DB 加上新欄位與附件表，不破壞既有資料。

執行：python migrate_project_fields.py
"""
import os
import sqlite3

from app import create_app, db

app = create_app()

# 確保模型已載入（Project / ProjectAttachment）
from app.models import Project, ProjectAttachment  # noqa: F401

# 1) 用 SQLAlchemy 建立新表（ProjectAttachment）與確保 metadata 註冊
with app.app_context():
    db.create_all()
    print("[OK] 確保新表/欄位存在 (db.create_all)")

# 2) 對既有 project 表用原生 SQL 補欄位（已存在則跳過）
with app.app_context():
    DB = db.engine.url.database  # 與 create_app 使用的同一個 db 檔
    NEW_COLS = [
        ("priority", "VARCHAR(16) DEFAULT 'medium'"),
        ("start_date", "DATE"),
        ("due_date", "DATE"),
        ("risk_assessment", "TEXT"),
        ("stakeholders", "TEXT"),
        ("target_quality", "TEXT"),
    ]

    conn = sqlite3.connect(DB)
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(project)")
    existing = {row[1] for row in cur.fetchall()}
    added = []
    for col, ddl in NEW_COLS:
        if col not in existing:
            cur.execute(f"ALTER TABLE project ADD COLUMN {col} {ddl}")
            added.append(col)
    conn.commit()
    conn.close()

if added:
    print("[OK] 已補欄位:", added)
else:
    print("[OK] project 表欄位已是最新，無須新增")

print("=== 遷移完成 ===")
