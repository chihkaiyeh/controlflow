# 外網連線指引手冊

本手冊說明如何讓**在外面的員工**也能連上這套公司內控系統。
系統本身是一個 Flask 網站，預設只跑在公司內網（`http://localhost:5000`）。要讓外網連得進來，重點不在「改程式」，而在**網路通道 + 加密 + 權限**。

> ⚠️ **最重要的一句話**：目前 `run.py` 預設是 `debug=True`（開發模式）。
> **絕對不要把開發模式直接對外開放**——debug 模式等於給外網一條遠端執行後門。
> 對外時務必改用生產模式（見下文「步驟 0」）。

---

## 步驟 0：切換到生產模式（必做）

生產模式會關閉 debug，改用較穩定的 waitress 伺服器。

```bash
pip install -r requirements.txt        # 已含 waitress
# Windows PowerShell：
$env:FLASK_ENV="production"
$env:SECRET_KEY="強隨機值"             # production 模式沒設會拒絕啟動
python run.py
# 訊息出現「生產模式 (waitress, debug 關閉)」即代表成功
```

首次建立資料庫也要改用新的初始化方式（不再有 `admin123`）：
```bash
$env:ADMIN_PASSWORD="你的強密碼（至少10字元）"
python seed.py
```

也可註冊成 Windows 排程/服務，讓公司電腦重開機後自動啟動（見附錄 A）。

---

## 三種讓外網連進來的方式

依公司網路環境與安全需求擇一。安全等級由高到低：

| 方式 | 適用情境 | 難度 | 安全 | 說明 |
|------|----------|------|------|------|
| **A. 反向代理 + 固定 IP/DDNS + HTTPS** | 公司有固定 IP 或申請 DDNS | 中 | ★★★★★ | 正規做法，建議長期使用 |
| **B. 反向代理 + 隧道服務（Cloudflare Tunnel / ngrok / Tailscale）** | 沒有固定 IP、不想動防火牆 | 低~中 | ★★★★ | 免開防火牆埠，最省事 |
| **C. 直接開路由器埠轉發（Port Forwarding）** | 臨時測試 | 低 | ★★ | 僅臨時用，長期不建議 |

> 無論哪種，**都必須走 HTTPS（加密）**，否則員工帳號密碼會在外網裸奔。

---

### 方式 A：反向代理 + 固定 IP / DDNS（推薦）

架構：`員工瀏覽器 → https://controlflow.公司網域 → 反向代理(Nginx/caddy) → 本機 127.0.0.1:5000`

1. 確認公司對外 IP 固定，或用服務商（如 No-IP、Dynu）申請 DDNS，把 `controlflow.公司網域` 指到該 IP。
2. 路由器把 `80/443` 轉到跑反向代理的那台機器。
3. 在該機器裝 **Caddy**（最簡單，自動申請 HTTPS 憑證）或 Nginx。
4. Caddy 設定範例（`Caddyfile`）：

   ```
   controlflow.公司網域 {
       reverse_proxy 127.0.0.1:5000
   }
   ```

   存檔後執行 `caddy run` 或 `caddy start`，Caddy 會自動幫你申請並續期 Let's Encrypt 憑證。
5. 啟動系統生產模式（`步驟 0`），員工即可用 `https://controlflow.公司網域` 登入。

---

### 方式 B：隧道服務（無固定 IP、不想動防火牆）

#### B-1 Cloudflare Tunnel（最推薦，免費、自帶 HTTPS、不需開埠）
1. 公司電腦安裝 `cloudflared`。
2. 登入 Cloudflare 後執行一次 `cloudflared tunnel login`。
3. 建立隧道：
   ```bash
   cloudflared tunnel create controlflow
   cloudflared tunnel route dns controlflow controlflow.公司網域
   ```
4. 設定檔 `config.yml`：
   ```yaml
   tunnel: controlflow
   ingress:
     - hostname: controlflow.公司網域
       service: http://localhost:5000
     - service: http_status:404
   ```
5. 啟動：`cloudflared tunnel run controlflow`
6. 員工連 `https://controlflow.公司網域` 即可（Cloudflare 自動 HTTPS）。

#### B-2 ngrok（最快試用，但有連線時間/帳號限制）
```bash
ngrok http 5000
# 終端會給一個 https://xxxx.ngrok-free.app 網址，直接給員工即可
```
> 免費版網址每次重啟會變；要固定網址需付費方案。

#### B-3 Tailscale（零信任 VPN，適合小團隊）
把公司電腦與員工裝置都加入同一個 Tailscale 網，員工就能用公司電腦的 Tailscale IP 直接連 `http://<tailscale-ip>:5000`，**完全不用開埠、不用 DNS**。最適合「幾個人、重視安全」的場景。

---

### 方式 C：直接埠轉發（僅臨時測試用）

1. 路由器把外部 `443 → 內網機器 5000`（**不要**直接轉 5000 裸 HTTP，至少用 443 + 自行簽章/Let's Encrypt）。
2. 員工連 `https://公司IP:443`。
3. **長期不建議**：直接暴露 Flask 在本機 IP 上，攻擊面大、憑證難管理的。

---

## 上線前安全清單（必做）

- [ ] 系統已用**生產模式**啟動（debug 關閉）
- [ ] 對外網址**全程 HTTPS**（憑證有效、自動續期）
- [ ] 修改預設管理員：`seed.py` 以 `ADMIN_PASSWORD` 建立 admin（至少 10 字元），沒有殘留 `admin123`；並用「成員管理」頁建立各員工專屬帳號，按角色（employee/manager/finance/warehouse）給權限
- [ ] `SECRET_KEY` 改用環境變數設定（不要留預設值；production 模式會拒絕啟動）
- [ ] 確認所有 POST 表單都有 CSRF token（程式碼已內建）
- [ ] 路由器/防火牆只開必要的 443，關掉其他對外埠
- [ ] 確認 `.gitignore` 已排除 `app.db`、`uploads/`（這些含公司資料，絕不上傳）
- [ ] 定期備份 `app.db`（公司所有專案/採購/請款/庫存資料都在這）
- [ ] 若走方式 A/B-1，建議加登入失敗次數限制或 Cloudflare 的 WAF 擋暴力破解

---

## 員工使用方式（給員工看的版本）

1. 打開瀏覽器，輸入公司給的網址（如 `https://controlflow.公司網域`）。
2. 用管理員發的帳號密碼登入。
3. 依權限看到：專案管理、採購申請、請款、耗材庫存等模組。
4. 手機瀏覽器也能開（介面已做響應式）。

---

## 附錄 A：讓系統開機自啟（Windows 排程）

**不要在工作排程器的「動作」裡直接跑 `python run.py`**：環境變數（`FLASK_ENV`、
`SECRET_KEY`、`DATABASE_URL`、`UPLOAD_FOLDER`）在工作排程器裡沒有可靠的設定方式，
而且 production 模式現在會檢查 `SECRET_KEY`。

正確做法是把所有環境變數寫進 `start.bat`（範例見
[Windows 原生部署指引](windows-deployment-guide.md) 第五節），然後：

1. 工作排程器 → 建立基本工作。
2. 觸發程序：選「當電腦啟動時」；勾「不論使用者是否登入都執行」與「以最高權限執行」。
3. 動作：啟動程式 `C:\controlflow\start.bat`，「開始位置」設 `C:\controlflow`。
4. 設定：勾「如果工作失敗，則每 1 分鐘重新啟動，最多 3 次」。
5. 存檔後再手動執行一次，確認 `curl.exe http://localhost:5000/login` 回 200。

> 更穩健的做法是用 `nssm` 把 `start.bat` 註冊成 Windows **服務**，有統一的啟停、
> 失敗重啟與事件紀錄；工作排程器適合作為簡易替代方案。

## 附錄 B：備份與還原

```bash
# 備份：用 SQLite 在線快照，不要直接 copy 正在寫入的 app.db
python -c "import sqlite3; a=sqlite3.connect('app.db'); b=sqlite3.connect('app.db.bak.20261123'); a.backup(b); b.close(); a.close()"

# 驗證快照
python -c "import sqlite3; c=sqlite3.connect('app.db.bak.20261123'); print(c.execute('PRAGMA integrity_check').fetchone()[0])"
# 應輸出 ok

# 還原：先停掉服務，再用快照覆蓋
copy app.db.bak.20261123 app.db
```

Windows 上的完整批次檔（含冷備碟、NAS、`integrity_check` 與時間戳）見
[Windows 原生部署指引](windows-deployment-guide.md) 第九節。
建議每天自動備份一次，**每月至少做一次還原演練**。
