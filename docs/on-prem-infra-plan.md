# 地端設備架構規劃（辦公室小主機 + 抽取盒陣列）

> 本文檔為**規劃層級**：架構圖、採購清單、關鍵決策。
> 不含逐條安裝指令；實作細節請參考同倉的
> [NAS 部署指引](nas-deployment-guide.md) 與 [外網連線指引](external-access-guide.md)。

---

## 〇、已確認硬體與相容性核對

| 設備 | 型號 | 結論 |
|------|------|------|
| 小主機 | **HP Z2 Mini G3** | ✅ 合適。迷你靜音、GbE 網孔；儲存有 **1× M.2 NVMe (PCIe Gen3 x1) + 1× 2.5" SATA**（G3 的 M.2 為 Gen3 x1，對內控低負載無影響）；跑 Ubuntu + Docker 綽綽有餘。注意：**無內建 3.5" 碟位**，資料碟需用 2.5" SATA SSD 或全走外接抽取盒。 |
| 抽取盒 | **HIKVISION 磁碟陣列硬碟櫃** | ⚠️ 多數此類櫃為**盒內硬體 RAID**（按鈕/開關設 RAID0/1/JBOD），經 USB3 把「一顆已合併的碟」給主機。Ubuntu 只會看到**一顆碟**，無法在其上做軟體 RAID（mdadm/ZFS）。→ 當「自動鏡像的資料碟」可用，但**備份仍要走抽取冷備 + Mage20 Pro**。 |

> 若您的 HIKVISION 櫃型號支援「JBOD / 每碟獨立透過 USB 暴露」模式，請告知，可改走軟體 RAID 方案。

---

## 一、目標

在辦公室用 **HP Z2 Mini** 當伺服器，**外接 HIKVISION 陣列櫃**，把公司的
**內控系統 + 公司網站 + 資料庫**全部在地端設備上運行，不依賴公有雲。

核心精神：**資料留在自己辦公室、可控、可備份、不上公雲**。

---

## 二、架構圖（依實際型號）

```
                        ┌─────────────────────────────┐
   員工 (內網)          │   辦公室路由器 / 防火牆       │   員工 (外網, 可選)
   PC / 手機  ─────────▶│   192.168.x.x               │◀────────  (回家/出差)
                        └──────────────┬──────────────┘
                                       │  :80/:443
                                       ▼
                        ┌─────────────────────────────┐
                        │   HP Z2 Mini G3 (Ubuntu Server) │
                        │   M.2: 系統碟 (OS+Docker)       │
                        │   2.5" SATA: 熱資料 (可選)       │
                        │   ┌───────────────────────┐  │
                        │   │ Docker Engine          │  │
                        │   │  ├─ caddy     (反向代理 │  │
                        │   │  │             + 自動HTTPS)
                        │   │  ├─ controlflow (內控系統)│ │
                        │   │  ├─ website     (公司網站)│ │
                        │   │  └─ postgres    (資料庫)  │ │  ← 多服務共用
                        │   └───────────────────────┘  │
                        └───────┬───────────────┬──────┘
                 資料卷掛載     │                │ 備份輸出
                        ┌───────▼───────────────▼──────┐
                        │  HIKVISION 陣列櫃 (USB3)      │
                        │  盒內 RAID1 鏡像 → 主機看到   │
                        │  一顆 /mnt/data 大碟          │
                        └──────────────┬───────────────┘
                                       │ 每日備份
                        ┌──────────────▼───────────────┐
                        │ 抽取冷備碟（輪替/離線）        │
                        │ ＋ Mage20 Pro (NAS, SMB)      │
                        └───────────────────────────────┘
```

---

## 三、採購清單（依實際型號精簡版）

| 項目 | 規格 | 用途 | 優先級 |
|------|------|------|--------|
| HP Z2 Mini | 16GB RAM 起、含 1× M.2 SSD | 主機（已選） | 已備 |
| 陣列櫃 | HIKVISION 磁碟陣列硬碟櫃 + 2× HDD（同容量） | 盒內 RAID1 鏡像當資料碟 | 已備 |
| 系統碟 | Z2 Mini 內建 M.2 即可（建議 ≥512GB） | OS + Docker 映像 | 必備 |
| UPS | 入門塔式（500–1000VA，USB 通訊） | 防雷防瞬斷，避免 DB 損毀 | 強烈建議 |
| 抽取冷備碟 | 1–2 顆外接碟（可與陣列櫃分開，或用櫃上抽出來的碟） | 每日輪替離線備份 | 必備 |
| 網域 | 申請公司網域（如 company.com.tw） | 若需外網 HTTPS 憑證 | 外網才需 |

> 陣列櫃硬體 RAID 的**陷阱**：櫃子本身故障 = 整套陣列讀不到（單點）；
> 且跨廠牌/型號難遷移。故備份**不能只靠它**，仍要獨立冷備 + NAS。

---

## 四、關鍵決策

### 1. 作業系統：Ubuntu Server 22.04 LTS
免費、文件多、Docker 支援好。Z2 Mini G3 的 Intel 網卡與 USB3 均原生支援。

### 2. 一切容器化
內控系統已提供 `Dockerfile` + `docker-compose.yml`，掛載卷指向陣列櫃的 `/mnt/data`。
公司網站、資料庫、反向代理都跑容器，便於遷移與重建。

### 3. 資料庫：SQLite 先、PostgreSQL 後
- **現階段**（只有內控、人數 < 50）：SQLite 單檔夠用，`config.py` 已預留
  `DATABASE_URL` 切換，未來無痛換。
- **規模上來 / 多服務共用 / 外網並發**：把內控系統改連 **PostgreSQL**
  （同主機一個 `postgres` 容器，多服務共用）。不建議現在就過度工程。

### 4. 「陣列」的務實做法（受限於盒內硬體 RAID）
- 陣列櫃設 **RAID1（雙碟鏡像）** → 主機看到一顆 `/mnt/data`，防單碟故障。
- **但這不是備份**。再加兩層：
  - **每日備份** `/mnt/data` → 抽取冷備碟（離線輪替，防勒索/誤刪）
  - **同步備份** → Mage20 Pro（NAS，防主機/櫃被盜或火災）
- 3-2-1：線上(陣列櫃) + 冷備碟 + NAS；HDD + NAS 兩媒體；1 份離線。

### 5. 對外連線（若需要）
小主機前放 **Caddy** 做反向代理 + 自動 HTTPS；**不要**直接裸露容器埠。
內網先跑、確認穩定再考慮開外網（見 external-access-guide）。

### 6. 安全清單（上線前）
- 改預設 admin 密碼、為每位員建專屬帳號與角色
- `SECRET_KEY` 用環境變數、強隨機值
- 只開必要埠（443）；路由/防火牆擋其餘
- `.gitignore` 已排除 `app.db` / `uploads` / `.env`，公司資料不上倉庫
- 啟用 UPS，避免斷電損毀 DB

---

## 五、每日備份腳本草案（cron 執行）

```bash
#!/usr/bin/env bash
# /opt/backup/backup.sh —— 備份 controlflow 資料卷到冷備碟 + Mage20 Pro
set -euo pipefail
SRC=/mnt/data                       # 陣列櫃掛載點
COLD=/mnt/coldbackup                # 抽取冷備碟掛載點
NAS=/mnt/nas/controlflow            # Mage20 Pro (SMB 掛載)
DATE=$(date +%F)
ARCHIVE="/tmp/controlflow_${DATE}.tar.gz"

# 1) 暫停容器寫入（SQLite 建議；PostgreSQL 改用 pg_dump）
docker compose -f /opt/controlflow/docker-compose.yml stop controlflow || true
tar czf "$ARCHIVE" -C "$SRC" .
docker compose -f /opt/controlflow/docker-compose.yml start controlflow || true

# 2) 複製到冷備碟與 NAS
cp "$ARCHIVE" "$COLD/"
cp "$ARCHIVE" "$NAS/" 2>/dev/null || echo "NAS 未掛載，跳過"
rm -f "$ARCHIVE"

# 3) 保留最近 14 天
find "$COLD" -name 'controlflow_*.tar.gz' -mtime +14 -delete
echo "backup done: $DATE"
```
排程：`0 3 * * * /opt/backup/backup.sh >> /var/log/backup.log 2>&1`

> PostgreSQL 場景請改用 `pg_dump` 匯出 SQL 再打包，比直接 tar 資料目錄安全。

---

## 六、落地路徑（MVP → 完整）

1. **MVP**：Z2 Mini 裝 Ubuntu + Docker；陣列櫃設 RAID1 掛 `/mnt/data` →
   內控系統容器跑起來（內網）。
2. **加備份**：上面腳本排程 + Mage20 Pro 同步。
3. **加固**：UPS、防火牆、改密、角色帳號。
4. **加網站/DB**：公司網站容器、必要時 PostgreSQL。
5. **加對外**：Caddy + HTTPS（若需外網）。

---

## 七、注意事項
- 地端自管 = 可用性與備份由公司自己負責：停電、主機故障、被盜都要有對策。
- 陣列櫃是**硬體 RAID 單點**，故障時整套讀不到；備份必須獨立於它。
- 日後可把同套 Docker Compose 平滑搬到更強主機或支援 Docker 的 NAS，資料卷一併搬移。
