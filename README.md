# BMI 計算器

使用 Flask 製作的成人 BMI 網頁計算器。輸入身高（公分）和體重（公斤）後，頁面會顯示 BMI（小數點後一位）、以儀表板刻度圖（Gauge Chart）呈現目前體位區間，並提供體位分類、生活建議與風險提醒。

## 功能

- **自動計算 BMI**：送出身高與體重後立即計算，並顯示至小數點後一位。
- **儀表板刻度圖**：以伺服器端產生的 inline SVG 半圓儀表板呈現，刻度範圍 15–35，依臺灣成人體位標準劃分「過輕、正常、過重、肥胖」四個色帶，並標示 18.5 / 24 / 27 三個分界值；指針指向目前 BMI 位置，所在區間會加粗強調。BMI 超出刻度範圍時，指針停在端點並顯示提示。儀表板不依賴任何 JavaScript 或外部圖表函式庫。
- **健康建議與風險提醒**：依體位區間顯示健康風險等級（較低 / 中等 / 較高）、生活建議，以及對應的健康風險提醒清單。

體位分類、建議與風險提醒集中定義在 `app.py` 的 `BMI_CATEGORIES`，儀表板色帶與分界刻度也由同一份資料產生，調整門檻時只需修改一處。

## 啟動

需安裝 Python 3.9 以上版本。在專案資料夾執行：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```

接著開啟 http://127.0.0.1:5000/ 。若 PowerShell 不允許啟用虛擬環境，也可以使用 `.\.venv\Scripts\python.exe -m pip install -r requirements.txt` 和 `.\.venv\Scripts\python.exe app.py`。

## 計算方式

BMI = 體重（公斤）÷ 身高（公尺）²。分類採臺灣成人體位參考標準：低於 18.5 為體重過輕、18.5 至未滿 24 為健康體位、24 至未滿 27 為體重過重、27 以上為肥胖。頁面以顯示至小數點後一位的 BMI 進行分類，儀表板指針位置亦以同一數值計算，確保指針與分類一致。

這只是成人體位參考，不能取代專業醫療評估，也不適用於兒童、青少年或孕婦。

執行測試：`python -m unittest discover -s tests`

## 部署到 Azure Web App

`.github/workflows/deploy-azure.yml` 在 `main` 分支的應用程式、測試或 workflow 異動時執行，也可以從 GitHub Actions 手動觸發。流程會在 Windows runner 上執行測試、下載官方 Python 3.14.8 可嵌入版本，將 Python 與相依套件一起部署到 `NTUSTweb00`（資源群組 `NTUSTlab2026`）。站點透過 `web.config` 的 IIS HttpPlatformHandler 啟動 `serve.py`，以 Waitress 提供 Flask 服務。

此方法使用**隨部署包提供的 Python**，不依賴 Windows App Service 內建 Python 執行環境；HttpPlatformHandler 必須在目標站點可用。`NTUSTweb00` 目前是 Windows Web App，部署時會確認作業系統。

在 GitHub 儲存庫 **Settings → Secrets and variables → Actions** 確認：

- Repository secret `AZURE_CREDENTIALS`：Azure 服務主體的 `clientId`、`clientSecret`、`subscriptionId`、`tenantId` 組成的 JSON。此 Secret 已設定，不要把內容寫進程式碼。

請確認該服務主體對 `NTUSTweb00` 具有部署權限（例如該站點的 **Website Contributor**）。推送符合上述條件的 `main` 分支異動，或從 GitHub Actions 手動執行工作流程即可部署。
