# NAS 部署指引手冊

本手冊說明如何把「公司內控系統」部署到 NAS / 容器環境。

> ⚠️ **關於 Hikvision Mage20 Pro 的重要說明**
> Mage20 Pro 使用的是海康自研的 **HIKSEMI OS**（ARM 家庭網盤系統），
> 定位為家庭私有雲，基礎功能（檔案、相簿、監控錄影）完善，但**並非像
> Synology DSM / QNAP QTS 那樣內建 Docker 套件中心**。目前沒有可靠證據顯示
> 它能直接安裝並執行第三方容器。
>
> 因此本系統**無法直接「跑在」Mage20 Pro 裡**。但 Mage20 Pro 仍非常適合做兩件事：
> 1. **集中存放資料**：把 DB 與附件掛載到它上面（透過掛載網路資料夾 / NFS / SMB）。
> 2. **自動備份**：定時把 `/data` 整個備份到 Mage20 Pro。
>
> 實際執行程式的地方，建議是另一台**能跑 Docker 的主機**（迷你 PC、舊電腦、
> 樹莓派、或未來升級到有 Docker 的 NAS）。下文以「能跑 Docker 的主機 + NAS 當儲存」
> 為架構說明。

---

## 架構（推薦）

```
員工瀏覽器
    │  HTTPS
    ▼
反向代理 (Caddy/Nginx)  ← 跑在 Docker 主機或獨立機
    │  http://localhost:5000
    ▼
controlflow 容器 (Flask + waitress)
    │  資料寫到 /data
    ▼
掛載卷 / NAS (Mage20 Pro 經 SMB/NFS 掛載)  ← 持久化 + 備份
```

---

## 第一步：在能跑 Docker 的主機上部署

### 1. 準備
```bash
# 安裝 Docker 與 docker-compose（以 Ubuntu 為例，其他系統類似）
sudo apt update
sudo apt install -y docker.io docker-compose-plugin
sudo systemctl enable --now docker
```

### 2. 取得程式碼
```bash
git clone https://github.com/chihkaiyeh/controlflow.git
cd controlflow
```

### 3. 設定環境變數（安全）
建立 `.env`（**不要 commit**，已寫入 .gitignore 預設排除 `.env`）：
```
SECRET_KEY=請改成一段夠長的隨機字串
# 若要把 DB/附件直接放在 NAS 掛載點，可改這兩行指向掛載目錄
# DATABASE_URL=sqlite:////mnt/nas/controlflow/app.db
# UPLOAD_FOLDER=/mnt/nas/controlflow/uploads
```
> 強烈建議 `SECRET_KEY` 用 `python -c "import secrets;print(secrets.token_hex(32))"` 產生。

### 4. 啟動
```bash
docker compose up -d --build
# 第一次啟動後，建立管理員帳號
docker compose exec controlflow python seed.py
```
瀏覽器開 `http://<主機IP>:5000` 即可登入（預設 admin / admin123，請立即改密）。

---

## 第二步：把資料放到 Mage20 Pro（NAS 當儲存）

有兩種做法：

### 做法 A：容器卷直接放在 NAS 掛載點（最簡單）
1. 在 Docker 主機把 Mage20 Pro 的共用資料夾掛載上來，例如掛到 `/mnt/nas`。
   （Mage20 Pro 的檔案分享通常是 SMB；Linux 掛 SMB 用 `mount -t cifs`。）
2. 修改 `docker-compose.yml` 的 volume 為：
   ```yaml
   volumes:
     - /mnt/nas/controlflow_data:/data
   ```
3. 重啟 `docker compose up -d`。

### 做法 B：用具名卷 + 定時備份到 NAS
不改 volume，而是每天把 `/data` 壓縮備份到 NAS：
```bash
# 排程（crontab -e）每天 03:00 備份
0 3 * * * docker run --rm -v controlflow_data:/data -v /mnt/nas/backups:/backup alpine \
  tar czf /backup/controlflow_$(date +\%F).tar.gz -C /data .
```

---

## 第三步：讓外網員工也能連（HTTPS）

請參考 [外網連線指引手冊](external-access-guide.md) 的「方式 A / B」。
重點：在 Docker 主機前面放 Caddy/Nginx 做反向代理 + 自動 HTTPS，
**不要**直接把容器的 5000 埠裸露到外網。

Caddy 範例（跑在 Docker 主機上）：
```
controlflow.公司網域 {
    reverse_proxy localhost:5000
}
```

---

## 維運指令速查

```bash
docker compose ps                 # 看狀態
docker compose logs -f controlflow # 看日誌
docker compose restart            # 重啟
docker compose down               # 停止並移除容器（資料仍在 volume）
docker compose exec controlflow python seed.py   # 重建 admin（若 DB 清空）
```

## 升級程式
```bash
git pull
docker compose up -d --build
```
（DB 與附件在 volume，不會被覆蓋；若有資料表變更，參考 `migrate_project_fields.py`。）

---

## 附錄：若 Mage20 Pro 其實有 Docker 入口

如果您進入 Mage20 Pro 的管理介面，發現裡面確實有「應用中心 / Docker / 容器」
之類的入口，請告訴我（最好截圖），我可以據此補寫專屬步驟。
在那之前，建議以上述「Docker 主機 + NAS 儲存」的方式部署。
