# Windows-native 部署指引（HP Z2 Mini G3 + Unitek 2-bay JBOD）

適用情境：**不重灌作業系統**，直接在 Z2 Mini G3 內建的 Windows 11 Pro 上，
用 `waitress` 跑內控系統；Unitek 2-bay 設 **JBOD**，兩顆 WD Purple 2TB
分別當「即時資料碟」與「冷備碟」，冗餘與備份交給備份流程而非 USB 鏡像。

> 為什麼 Windows 上不用軟體鏡像（Storage Spaces / RAID）：USB 外接碟容易被
> Windows 判定為可移除裝置而掉出集區、重建易出錯。改用「一碟即時 + 一碟冷備
> + NAS 第三份」的 3-2-1 策略，更穩也更簡單。
>
> **路線說明**：本文是 **Windows 原生路線（Unitek JBOD）**。另一份
> [地端設備架構規劃](on-prem-infra-plan.md) 是 **Ubuntu + Docker 路線（ACASIS JBOD + mdadm RAID1）**。
> 兩者硬體配置不同是刻意的，請依實際作業系統選擇對應文件，不要混用。

---

## 〇、硬體接線與磁碟初始化（一次性）

1. 兩顆 WD Purple 2TB 裝進 Unitek 2-bay，**盒子背面的模式開關撥到 JBOD**
   （每顆碟獨立暴露，不是 RAID0/RAID1）。
2. Unitek 用 **USB 3.0 線**接上 Z2 Mini G3（接到藍色 USB3 埠，別插 USB2）。
3. 開機進 Windows 後，`Win+R` 輸入 `diskmgmt.msc` 開啟磁碟管理。
4. 會看到兩顆「未知／未初始化」的 2TB 碟（確認容量約 1863 GiB）。
   - 每顆：**初始化磁碟 → 選 GPT** → 在未配置空間按右鍵 **新增簡單磁碟區** → 一路下一步 → 格式化 **NTFS**。
   - 第一顆指定磁碟機代號 **`D:`**，磁碟區標籤 `controlflow-data`（即時資料碟）。
   - 第二顆指定磁碟機代號 **`E:`**，磁碟區標籤 `controlflow-coldbackup`（冷備碟）。
5. 在 `D:` 建兩個資料夾：`D:\controlflow-data`、`D:\controlflow-data\uploads`。

驗證：檔案總管能看到 `D:`（controlflow-data）與 `E:`（controlflow-coldbackup）。

---

## 一、安裝 Python 3.11

- 官網下載 **Python 3.11.x**（Windows installer 64-bit）。別裝 3.13，先求穩。
- 安裝第一個畫面**務必勾選「Add python.exe to PATH」**，選 Customize 也可，其餘預設。
- 驗證（開新的 PowerShell 或 cmd）：
  ```powershell
  python --version     # 應顯示 Python 3.11.x
  pip --version
  ```

---

## 二、取得程式碼

```powershell
git clone https://github.com/chihkaiyeh/controlflow.git C:\controlflow
cd C:\controlflow
```

---

## 三、建立虛擬環境並安裝依賴

```powershell
cd C:\controlflow
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
```

驗證：`pip show waitress flask` 都有版本號。

---

## 四、產生 SECRET_KEY

```powershell
python -c "import secrets;print(secrets.token_hex(32))"
```
複製輸出（64 字元 hex），下一步用它。

---

## 五、建立啟動批次檔 `C:\controlflow\start.bat`

```bat
@echo off
cd /d C:\controlflow
call venv\Scripts\activate
set FLASK_ENV=production
set SECRET_KEY=貼上第四步產生的64字元
set DATABASE_URL=sqlite:///D:/controlflow-data/app.db
set UPLOAD_FOLDER=D:\controlflow-data\uploads
python run.py
```

> `DATABASE_URL` 用**正斜線**（SQLAlchemy 在 Windows 吃這個格式）；
> `UPLOAD_FOLDER` 用 Windows 原生反斜線路徑即可（程式直接當本機路徑用）。
> 資料庫與附件都落在 `D:\controlflow-data`，程式碼與資料分離，重灌/搬移無痛。

---

## 六、第一次初始化資料庫（建 admin）

```powershell
cd C:\controlflow
call venv\Scripts\activate
$env:FLASK_ENV="production"
$env:SECRET_KEY="貼上第四步產生的64字元"   # production 模式沒設會拒絕啟動
$env:DATABASE_URL="sqlite:///D:/controlflow-data/app.db"
$env:UPLOAD_FOLDER="D:\controlflow-data\uploads"
$env:ADMIN_PASSWORD="換成你自己的強密碼（至少10字元）"
python seed.py
```

- 會在 `D:\controlflow-data\app.db` 建好資料庫與管理員帳號 `admin`。
- **不再有 `admin123` 預設密碼**：初始密碼就是上面設定的 `ADMIN_PASSWORD`。
- 提醒：這行指令會留在 PowerShell 歷程記錄中；若在意，可改用
  `$env:ADMIN_PASSWORD = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto([System.Runtime.InteropServices.Marshal]::SecureStringToBSTR((Read-Host 'Admin password' -AsSecureString)))` 輸入。
- 登入後仍建議到「成員管理」為每位員工建立專屬帳號，不要用共用 admin。

---

## 七、手動啟動測試

```powershell
cd C:\controlflow
.\start.bat
```

- 終端機出現 `=== 生產模式 (waitress, debug 關閉) ===` 與 `監聽 http://0.0.0.0:5000`。
- 另開 PowerShell 驗證：
  ```powershell
  curl.exe http://localhost:5000/login
  ```
  回傳 HTTP 200 的登入頁 HTML 即成功。
- 公司內網其他電腦開瀏覽器 `http://<Z2 Mini 的IP>:5000` 應能登入。
- 測試完按 `Ctrl+C` 停掉。

---

## 八、設成開機自動啟動 + 崩潰自動重啟（工作排程器）

1. `Win+R` → `taskschd.msc` → 右側 **建立工作**。
2. **一般**：名稱 `ControlFlow Server`，勾**「不論使用者是否登入都執行」**、勾**「以最高權限執行」**。
3. **觸發程序**：**開機時**（At startup）。
4. **動作**：啟動程式 →
   - 程式/指令碼：`C:\controlflow\start.bat`
   - 開始位置：`C:\controlflow`
5. **設定**：勾**「如果工作失敗，則每…重新啟動」**（如每 1 分鐘，最多 3 次）。
6. 存檔，右鍵該工作 →**執行**測試，`curl.exe http://localhost:5000/login` 應 200。
7. 重開機驗證一次：重開後服務自己起來。

---

## 九、每日自動備份（冷備碟 E: + Mage20 Pro）

1. 在 Mage20 Pro 開一個 SMB 共用（例如 `\\<NAS-IP>\controlflow`），記住用戶/密碼。
2. 建立 `C:\controlflow\backup.bat`：
   ```bat
   @echo off
   setlocal
   set PY=C:\controlflow\venv\Scripts\python.exe
   set SRC=D:\controlflow-data
   set COLD=E:\controlflow-coldbackup
   set NAS=\\<NAS-IP>\controlflow

   REM 1) 用 SQLite 在線備份產生一致性快照，不需停服務
   if not exist "%SRC%\snapshots" mkdir "%SRC%\snapshots"
   for /f %%i in ('powershell -NoProfile -Command "Get-Date -Format yyyyMMdd_HHmmss"') do set STAMP=%%i
   "%PY%" -c "import sqlite3; a=sqlite3.connect(r'%SRC%\app.db'); b=sqlite3.connect(r'%SRC%\snapshots\app_%STAMP%.db'); a.backup(b); b.close(); a.close()"
   if errorlevel 1 goto :fail

   REM 2) 驗證快照完整性；損壞就不往外複製
   "%PY%" -c "import sqlite3; c=sqlite3.connect(r'%SRC%\snapshots\app_%STAMP%.db'); print(c.execute('PRAGMA integrity_check').fetchone()[0])" > "%SRC%\snapshots\integrity_%STAMP%.txt"
   findstr /x "ok" "%SRC%\snapshots\integrity_%STAMP%.txt" >nul || goto :fail

   REM 3) 複製到冷備碟與 NAS。用 /E 不用 /MIR，避免來源異常時反向刪除備份
   if not exist "%COLD%" mkdir "%COLD%"
   robocopy "%SRC%" "%COLD%\latest" /E /R:1 /W:1
   robocopy "%SRC%" "%COLD%\%STAMP%" /E /R:1 /W:1
   robocopy "%SRC%" "%NAS%" /E /R:1 /W:1
   echo Backup done %STAMP%
   exit /b 0

   :fail
   echo Backup FAILED %STAMP% 1>&2
   exit /b 1
   ```
   - 時間戳改用 `Get-Date -Format yyyyMMdd_HHmmss`，不受 Windows 地區設定影響。
   - 資料庫用 `sqlite3.backup()` 在線快照 + `PRAGMA integrity_check`，比直接 copy 正在寫入的 `app.db` 安全。
   - `robocopy` 改 `/E`：只新增/更新，不做鏡像刪除；舊備份另外用 `forfiles` 依日期清理，避免一次誤刪。
3. 測試：執行 `C:\controlflow\backup.bat`，確認 `E:` 與 NAS 出現檔案，且 `integrity_*.txt` 內容為 `ok`。
4. 排程：工作排程器**建立基本工作** → 每日 03:00 → 執行程式 `C:\controlflow\backup.bat`。
5. 清理舊備份：每月一次 `forfiles /p E:\controlflow-coldbackup /m "app_*.db" /d -30 /c "cmd /c del @path"`，並同步清掉對應的 `integrity_*.txt`。

> **每月至少做一次還原演練**：把某份快照複製到另一個路徑，用 `DATABASE_URL` 指向它啟動，
> 實際登入確認資料可讀。沒有還原演練的備份只能算「可能有用」。

> 建議**每周至少一次把冷備碟 E: 拔下離線存放**（旋轉式輪替），防勒索軟體一併加密。

---

## 十、Caddy 反向代理 + HTTPS（員工用網域）

- 公司 DNS 加一筆 A record：`controlflow.<公司網域>` → Z2 Mini 的固定 IP。
- 下載 Caddy Windows 版，建 `Caddyfile`：
  ```
  controlflow.yourcompany.com.tw {
      reverse_proxy localhost:5000
  }
  ```
- 跑 `caddy run`，Caddy 自動向 Let's Encrypt 申請憑證（網域需指向本機、開 80/443）。
- 員工開 `https://controlflow.yourcompany.com.tw` 即可。
- Caddy 也設成開機自啟（可用 NSSM 或工作排程器包成服務）。

---

## 十一、上線前安全清單

- [ ] `ADMIN_PASSWORD` 已設定強密碼，`seed.py` 建立 admin 時使用；沒有殘留 `admin123`。
- [ ] 為每位員工建專屬帳號與角色，不要用共用 admin。
- [ ] `start.bat` 的 `SECRET_KEY` 是唯一隨機值，不要提交進 git；production 模式下用預設值會拒絕啟動。
- [ ] 所有表單都有 CSRF token（程式碼已內建）；每日備份與還原演練已排程。
- [ ] Windows 防火牆：只對公司網段開放 5000（或經 Caddy 的 443），別對外網開放 5000。
- [ ] **Windows 更新**：設定 → Windows Update →**使用時段**設成非上班時間（如 01:00–05:00），並開啟「盡快取得最新更新」以外的延後，避免上班時間自動重開機中斷服務。
- [ ] 電源選項：**高效能/永不睡眠、永不休眠**，合上筆電螢幕不休眠。
- [ ] 加裝 **UPS**（不斷電系統），避免斷電導致 SQLite 寫入中損毀。
- [ ] `D:\controlflow-data` 若日後變大，隨時可整個搬去 NAS 或換大碟。

---

## 快速總覽（最終架構）

```
員工瀏覽器
  → https://controlflow.<公司網域>        (Caddy 反向代理 + HTTPS)
  → localhost:5000                        (waitress 跑內控系統)
  → D:\controlflow-data\app.db + uploads  (WD Purple 碟 1，即時資料)
  → 每日 03:00 備份
      → E:\controlflow-coldbackup         (WD Purple 碟 2，冷備，可離線輪替)
      → Mage20 Pro SMB 共用               (NAS 第三份)
系統碟：Z2 Mini 內建 M.2 SSD 跑 Windows 11 Pro + Python + 程式碼
```

## 常見卡關

| 現象 | 原因 / 解法 |
|------|------|
| `python` 找不到 | 安裝時沒勾 Add to PATH；重裝或手動加 PATH |
| 啟動報 `SECRET_KEY` 相關 | 確認 `start.bat` 的 `set SECRET_KEY=` 有值 |
| 內網連不到 :5000 | Windows 防火牆擋了；加「允許 5000 入站」規則 |
| 資料寫進程式碼目錄而非 D: | 確認 `DATABASE_URL`/`UPLOAD_FOLDER` 已設（用 `start.bat` 啟動才有） |
| 重開機服務沒起 | 工作排程器的「開始位置」與「以最高權限」要設對；手動執行測試 |
| Unitek 兩顆只看到一顆 | 盒子模式開關確認在 JBOD；USB 線換 USB3 埠 |
