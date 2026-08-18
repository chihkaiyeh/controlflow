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
python run.py
# 訊息出現「生產模式 (waitress, debug 關閉)」即代表成功
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
- [ ] 修改預設 admin 密碼（`admin / admin123`），並用「成員管理」頁建立各員工專屬帳號，按角色（employee/manager/finance/warehouse）給權限
- [ ] `SECRET_KEY` 改用環境變數設定（不要留預設值）
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

用 Windows 工作排程器，讓公司電腦登入/開機後自動以生產模式啟動：

1. 工作排程器 → 建立基本工作。
2. 觸發程序：選「當電腦啟動時」或「使用者登入時」。
3. 動作：啟動程式 `python`，引數 `run.py`，「起始位置」設為專案目錄（如 `C:\Users\chihk\internal-control`）。
4. 在同一動作前先設定環境變數 `FLASK_ENV=production`（可在「編輯動作」的「新增引數」前用 `set` 或在工作裡設定）。

> 更穩健可改用 `nssm` 把 `python run.py` 註冊成 Windows 服務。

## 附錄 B：備份與還原

```bash
# 備份（複製整個 db 檔即可）
copy app.db app.db.bak.2026xxxx

# 還原
copy app.db.bak.2026xxxx app.db
```
建議每天自動備份一次（排程任務 + 上面的 copy 指令）。
