# 地端設備架構規劃（辦公室小主機 + 抽取盒陣列）

> 本文檔為**規劃層級**：架構圖、採購清單、關鍵決策。
> 不含逐條安裝指令；實作細節請參考同倉的
> [NAS 部署指引](nas-deployment-guide.md) 與 [外網連線指引](external-access-guide.md)。

---

## 〇、已確認硬體與相容性核對

| 設備 | 型號 | 結論 |
|------|------|------|
| 小主機 | **HP Z2 Mini G3** | ✅ 合適。迷你靜音、GbE 網孔；儲存有 **1× M.2 NVMe (PCIe Gen3 x1) + 1× 2.5" SATA**（G3 的 M.2 為 Gen3 x1，對內控低負載無影響）；跑 Ubuntu + Docker 綽綽有餘。注意：**無內建 3.5" 碟位**，資料碟需用 2.5" SATA SSD 或全走外接抽取盒。 |
| 抽取盒 | **ACASIS 阿卡西斯 雙盤位 3.5" 硬碟盒（EC-7352 類，支援 RAID0/1/JBOD/SPAN）** | ✅ 設成 **JBOD 模式**後，盒體純透傳，Ubuntu 會**個別看到兩顆獨立碟**（`/dev/sdX` 各一），RAID1 鏡像由主機上的 **mdadm/ZFS** 軟體做。避開了 HIKVISION 那種「盒內硬體 RAID、主機只看一顆碟、櫃子變單點」的坑。⚠️ 注意：**不要把盒上開關設到盒子的 RAID1**，否則又回到硬體 RAID；保持 JBOD。 |

> 選型原則：要「每碟獨立暴露給主機」的 JBOD 盒，不要「盒內硬體 RAID 合併成一顆」的陣列櫃。ACASIS 這款有 RAID 切換開關，但只用其 **JBOD** 模式即可。

---

## 一、目標

在辦公室用 **HP Z2 Mini G3** 當伺服器，**外接 ACASIS 雙盤位硬碟盒（JBOD 模式）**，把公司的
**內控系統 + 公司網站 + 資料庫**全部在地端設備上運行，不依賴公有雲。
陣列的鏡像由主機上的軟體 RAID（mdadm）做，盒體只當純透傳。

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
                        │  ACASIS 雙盤位 (USB3, JBOD)   │
                        │  主機看到 2 顆獨立碟 sda/sdb   │
                        │  └─ mdadm RAID1 鏡像          │
                        │     → /dev/md0 → /mnt/data     │
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
| 陣列櫃 | ACASIS 雙盤位 3.5" 硬碟盒（EC-7352 類）+ 2× HDD（同容量） | 設 **JBOD 模式**，由主機 mdadm 做 RAID1 鏡像當資料碟 | 已備 |
| 系統碟 | Z2 Mini 內建 M.2 即可（建議 ≥512GB） | OS + Docker 映像 | 必備 |
| UPS | 入門塔式（500–1000VA，USB 通訊） | 防雷防瞬斷，避免 DB 損毀 | 強烈建議 |
| 抽取冷備碟 | 1–2 顆外接碟（可與陣列櫃分開，或用櫃上抽出來的碟） | 每日輪替離線備份 | 必備 |
| 網域 | 申請公司網域（如 company.com.tw） | 若需外網 HTTPS 憑證 | 外網才需 |

> 選型原則回顧：要「每碟獨立暴露給主機」的 JBOD 盒（如 ACASIS），
> 不要「盒內硬體 RAID 合併成一顆」的陣列櫃。軟體 RAID 讓您保有控制權與可移植性。

---

## 四、關鍵決策

### 1. 作業系統：Ubuntu Server 22.04 LTS
免費、文件多、Docker 支援好。Z2 Mini G3 的 Intel 網卡與 USB3 均原生支援。

### 2. 一切容器化
內控系統已提供 `Dockerfile` + `docker-compose.yml`，掛載卷指向軟體 RAID 的 `/mnt/data`。
公司網站、資料庫、反向代理都跑容器，便於遷移與重建。

### 3. 資料庫：SQLite 先、PostgreSQL 後
- **現階段**（只有內控、人數 < 50）：SQLite 單檔夠用，`config.py` 已預留
  `DATABASE_URL` 切換，未來無痛換。
- **規模上來 / 多服務共用 / 外網並發**：把內控系統改連 **PostgreSQL**
  （同主機一個 `postgres` 容器，多服務共用）。不建議現在就過度工程。

### 4. 「陣列」的做法：盒設 JBOD + 主機軟體 RAID1（mdadm）
- ACASIS 設 **JBOD 模式** → 主機個別看到兩顆碟（如 `/dev/sda`、`/dev/sdb`）。
- 在主機上用 **mdadm 建 RAID1**：`mdadm --create /dev/md0 --level=1 --raid-devices=2 /dev/sda /dev/sdb`
  → 格式化 → 掛載 `/mnt/data`。
- **務必用磁碟穩定識別符**：USB 重插順序會變，RAID 組態與 `/etc/fstab` 都要用
  `/dev/disk/by-id/...` 或陣列 `UUID`，**不要用 `/dev/sda`/`sdb`**，否則重開機可能認錯碟。
- RAID1 防「一顆碟掛掉服務不中斷」；**但這不是備份**，再加兩層：
  - **每日備份** `/mnt/data` → 抽取冷備碟（離線輪替，防勒索/誤刪）
  - **同步備份** → Mage20 Pro（NAS，防主機/盒被盜或火災）
- 3-2-1：線上(RAID1) + 冷備碟 + NAS；HDD + NAS 兩媒體；1 份離線。

> 為什麼不用盒子的硬體 RAID1：盒內合併後主機只看一顆碟，櫃子本身成單點、
> 跨廠牌難遷移；軟體 RAID 則碟壞了隨時抽去別台 Linux 用 `mdadm` 救資料。

### 5. 對外連線（若需要）
小主機前放 **Caddy** 做反向代理 + 自動 HTTPS；**不要**直接裸露容器埠。
內網先跑、確認穩定再考慮開外網（見 external-access-guide）。

### 6. 安全清單（上線前）
- 改預設 admin 密碼、為每位員建專屬帳號與角色
- `SECRET_KEY` 用環境變數、強隨機值
- 只開必要埠（443）；路由/防火牆擋其餘
- `.gitignore` 已排除 `app.db` / `uploads` / `.env`，公司資料不上倉庫
- 啟用 UPS，避免斷電損壞 RAID/DB（mdadm 有 bitmap 可加速重建，建議開）

---

## 五、每日備份腳本草案（cron 執行）

```bash
#!/usr/bin/env bash
# /opt/backup/backup.sh —— 備份 controlflow 資料卷到冷備碟 + Mage20 Pro
set -euo pipefail
SRC=/mnt/data                       # mdadm RAID1 掛載點
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
> 若 RAID1 其中一顆碟故障：`mdadm --detail /dev/md0` 看狀態，換上新碟後
> `mdadm --add /dev/md0 /dev/sdX` 即可自動重建，服務不中斷。

---

## 六、落地路徑（MVP → 完整）

1. **MVP**：Z2 Mini 裝 Ubuntu + Docker；ACASIS 設 JBOD，主機 mdadm 建 RAID1 掛 `/mnt/data` →
   內控系統容器跑起來（內網）。
2. **加備份**：上面腳本排程 + Mage20 Pro 同步。
3. **加固**：UPS、防火牆、改密、角色帳號。
4. **加網站/DB**：公司網站容器、必要時 PostgreSQL。
5. **加對外**：Caddy + HTTPS（若需外網）。

---

## 七、注意事項
- 地端自管 = 可用性與備份由公司自己負責：停電、主機故障、被盜都要有對策。
- **軟體 RAID 不是備份**：mdadm RAID1 只防單碟故障，仍須獨立冷備 + NAS。
- USB 外接盒做軟體 RAID 要注意：用 `by-id`/UUID 識別碟，避免重插認錯順序。
- 日後可把同套 Docker Compose 平滑搬到更強主機或支援 Docker 的 NAS，資料卷一併搬移。
