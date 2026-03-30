# Math_Point3r 

這是一個結合了 **MediaPipe 手勢辨識**、**FastAPI WebSocket** 與 **WebRTC 即時串流** 的互動式算數遊戲。玩家可以透過手勢來回答隨機生成的數學題目，享受即時回饋的遊戲體驗。

---

## 核心特色 (Core Features)

- **精準手勢辨識**：利用 MediaPipe Tasks API，即時捕捉並計算指尖座標，實現手指計數與手勢解析。
- **低延遲 WebSocket 通訊**：前端將擷取的攝影機幀（Base64）即時傳送至後端進行處理，並於毫秒內回收結果。
- **兩種遊戲模式**：支援「模式 A（單手模式）」與「模式 B（雙手進階模式）」，可自定義是否要計時。
- **即時回饋系統**：具備動態出題、自動改題、結算計分介面，並有視覺化的答題震盪反饋。

---

## 技術棧

### **Backend (Python 後端)**
- **FastAPI / Uvicorn**: 處理高效併發的 WebSocket 與 HTTP 連線。
- **MediaPipe**: 核心 AI 模型，進行 Hand Landmarking。
- **OpenCV**: 影像前處理與解析。

### **Frontend (靜態前端)**
- **Hexo / Vanilla JS**: 輕量、高效的靜態網站構架。
- **WebRTC (MediaDevices)**: 於瀏覽器存取攝影機串流。
- **WebSocket API**: 實現前後端低延遲的長連接通信。

---

## 專案結構

```text
Math_Point3r/
├── backend/             # 後端 logic
│   ├── server.py        # FastAPI 主程式 & WebSocket 邏輯
│   ├── requirements.txt # Python 套件依賴
│   └── hand_landmarker.task # MediaPipe 預訓練模型
├── frontend/            # 前端 logic
│   ├── source/          # 頁面原始碼
│   └── themes/          # 自定義遊戲主題（包含 main.js 核心邏輯）
└── README.md
```

---

## 🚀 快速上手 (Getting Started)

### 1. 設置並啟動後端
```bash
cd backend
# 建立虛擬環境 (建議)
python -m venv venv
source venv/bin/activate 
# 安裝依賴
pip install -r requirements.txt
# 執行伺服器
python server.py
```

### 2. 設置並啟動前端
```bash
cd frontend
npm install
npm run dev
# 瀏覽器打開 http://localhost:4000
```

## 🌐 部署資訊 (Deployment)

- **前端部署**: 本專案已透過 Hexo 部署至 GitHub Pages。
- **試玩網址**: [https://lin3598197.github.io/Math_Point3r/](https://lin3598197.github.io/Math_Point3r/)

