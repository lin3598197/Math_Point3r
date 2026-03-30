# Math_Point3r

這是一個利用 MediaPipe 手勢辨識與 WebRTC、WebSocket 即時串流進行算數過關的小遊戲。

## 專案結構

- `backend/`: FastAPI 與 WebSocket 後端，利用 MediaPipe Tasks API 即時解析手勢並計算。
  - `server.py`: 主程式，包含 WebSocket 伺服器與 MediaPipe 整合邏輯。
  - `test_mp.py`: MediaPipe 測試程式。
  - `requirements.txt`: 專案依賴套件。
  - `hand_landmarker.task`: MediaPipe 的手勢辨識模型
  - `Dockerfile`: Docker 容器設定檔。
- `frontend/`: Hexo 生成的純靜態網頁，透過瀏覽器存取攝影機並即時顯示題目及辨識結果。

### 此專案已透過Hexo Deploy 部署至 GitHub Pages，網址為：https://lin3598197.github.io/Math_Point3r/
