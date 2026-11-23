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
# 必須提供初始管理員密碼（至少 10 字元），不再有寫死的預設密碼
ADMIN_PASSWORD='你的強密碼' python seed.py
python run.py           # 啟動，預設 http://localhost:5000
```
初始帳號為 `admin`，密碼就是上面設定的 `ADMIN_PASSWORD`，請妥善保管。
登入後仍建議到「成員管理」為每位使用者建立專屬帳號。

## 設定
- `SECRET_KEY`：正式部署**必須**以環境變數設定；`FLASK_ENV=production` 時若仍用開發預設值會拒絕啟動
- `ADMIN_PASSWORD`：`seed.py` 建立初始管理員時必填（至少 10 字元）
- `DATABASE_URL`：設定後可改用 PostgreSQL
- 附件上傳上限 16MB，允許類型見 `app/config.py` 的 `ALLOWED_EXTENSIONS`

## 權限與流程（2026-11 加固）
- 全站 POST 皆有 CSRF 保護；表單由 `csrf_token()` 產生隱藏欄位
- 專案的新增／編輯／結案／附件上傳與刪除僅 `admin`、`manager` 可執行；所有登入者皆可瀏覽
- 採購與請款有狀態機：已駁回不能改回核准，待核准不能直接標為已付款/已下單

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

## 文件
- [外網連線指引手冊](docs/external-access-guide.md)：讓外網員工連線、HTTPS、安全清單、開機自啟、備份
- [NAS 部署指引](docs/nas-deployment-guide.md)：Docker 容器化、用 NAS 當儲存與備份
- [Windows 原生部署指引](docs/windows-deployment-guide.md)：Z2 Mini G3 不重灌、waitress 生產模式、**Unitek 2-bay JBOD**（Windows 路線）、開機自啟、備份、HTTPS
- [地端設備架構規劃](docs/on-prem-infra-plan.md)：**Ubuntu + Docker 路線**，Z2 Mini + **ACASIS 雙盤 JBOD + mdadm RAID1**，內控/網站/DB 地端運行

> 兩份文件的硬碟配置不同是刻意安排的：Windows 路線用 Unitek JBOD（兩碟獨立、靠備份流程），
> Ubuntu 路線用 ACASIS JBOD + 主機 mdadm RAID1。依你實際選的作業系統看對應文件即可。
