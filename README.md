# Math_Point3r

這是一個利用 MediaPipe 手勢辨識與 WebRTC、WebSocket 即時串流進行算數過關的小遊戲。

## 專案結構
- `backend/`: FastAPI 與 WebSocket 後端，利用 MediaPipe Tasks API 即時解析手勢並計算。
- `frontend/`: Hexo 生成的純靜態網頁，極簡設計，透過瀏覽器存取攝影機並即時顯示題目及辨識結果。
