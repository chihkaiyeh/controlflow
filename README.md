# 公司內控系統 (ControlFlow)

[![CI](https://github.com/chihkaiyeh/controlflow/actions/workflows/ci.yml/badge.svg)](https://github.com/chihkaiyeh/controlflow/actions/workflows/ci.yml)

一套自架的企業內控網頁系統，管理公司的 **專案、採購申請、請款、耗材庫存**，並含成員與權限管理。

## 技術架構
- **後端**：Flask + Flask-Login
- **資料庫**：SQLite（開發便捷；可經由 `DATABASE_URL` 環境變數無痛換成 PostgreSQL）
- **前端**：Bootstrap 5（瀏覽器操作，手機可看）
- **權限角色**：admin（管理員）、manager（主管）、finance（財務）、warehouse（倉管）、employee（員工）

## 功能模組
| 模組 | 功能 |
|------|------|
| 專案管理 | 新增/編輯、時程、優先層級(高/中/低)、風險評估、利害關係人、目標品質、附件上傳、結案（僅新增不刪除） |
| 採購申請 | 員工申請 → 主管核准/駁回 → 標記已下單 |
| 請款 | 關聯採購單、財務/主管核准 → 標記已付款 |
| 耗材庫存 | 品項 CRUD、出入庫流水、低庫存警示 |
| 成員管理 | 僅 admin：新增成員、調整角色、啟用/停用、重設密碼 |

## 快速開始
```bash
pip install -r requirements.txt
python seed.py          # 建立資料庫 + 初始 admin 帳號
python run.py           # 啟動，預設 http://localhost:5000
```
初始帳號：`admin / admin123`（請務必上線後修改密碼）。

## 設定
- `SECRET_KEY`：建議以環境變數覆蓋預設值
- `DATABASE_URL`：設定後可改用 PostgreSQL
- 附件上傳上限 16MB，允許類型見 `app/config.py` 的 `ALLOWED_EXTENSIONS`

## 測試
```bash
python smoke.py              # 基礎架構
python smoke_projects.py     # 專案管理
python smoke_procurements.py # 採購申請
python smoke_payments.py     # 請款
python smoke_projects_v2.py  # 專案擴充 + 成員管理
```

## 注意
- 目前使用 Flask 開發伺服器，**生產環境請改用 WSGI 伺服器（如 gunicorn / waitress）並關閉 debug**。
- 本系統預設為內網/本機使用；若要對外，需另行設定 HTTPS 與防火牆。
