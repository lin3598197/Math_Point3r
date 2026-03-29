/**
 * Math_Point3r — 前端主邏輯
 * 負責：選單設定 → WebSocket 連線 → WebRTC 串流 → UI 更新
 */
(function () {
  'use strict';

  // ═══════════════════════════════════════════════════════
  //  設定常數
  // ═══════════════════════════════════════════════════════
  const WS_URL        = 'wss://atom-requested-deborah-workshop.trycloudflare.com/ws';
  const FRAME_INTERVAL = 100;   // ms，每 100ms 傳一幀
  const JPEG_QUALITY   = 0.5;   // canvas toDataURL 壓縮品質

  // ═══════════════════════════════════════════════════════
  //  DOM 元素
  // ═══════════════════════════════════════════════════════
  // 畫面
  const screenMenu   = document.getElementById('screen-menu');
  const screenGame   = document.getElementById('screen-game');
  const screenResult = document.getElementById('screen-result');

  // 選單
  const modeGroup       = document.getElementById('mode-group');
  const timeGroup       = document.getElementById('time-group');
  const cameraToggle    = document.getElementById('camera-toggle');
  const cameraToggleText = document.getElementById('camera-toggle-text');
  const btnStart        = document.getElementById('btn-start');

  // 遊戲
  const scoreDisplay   = document.getElementById('score-display');
  const timerBox       = document.getElementById('timer-box');
  const timerDisplay   = document.getElementById('timer-display');
  const btnMenu        = document.getElementById('btn-menu');
  const cameraVideo    = document.getElementById('camera-video');
  const captureCanvas  = document.getElementById('capture-canvas');
  const cameraOffLabel = document.getElementById('camera-off-label');
  const questionDisplay = document.getElementById('question-display');
  const gestureDisplay  = document.getElementById('gesture-display');
  const handDetail      = document.getElementById('hand-detail');
  const leftHandVal     = document.getElementById('left-hand-val');
  const rightHandVal    = document.getElementById('right-hand-val');
  const feedbackText    = document.getElementById('feedback-text');
  const wsDot          = document.getElementById('ws-dot');
  const wsLabel        = document.getElementById('ws-label');

  // 結算
  const resultScore  = document.getElementById('result-score');
  const resultTotal  = document.getElementById('result-total');
  const btnPlayAgain = document.getElementById('btn-play-again');
  const btnBackMenu  = document.getElementById('btn-back-menu');

  // ═══════════════════════════════════════════════════════
  //  遊戲狀態
  // ═══════════════════════════════════════════════════════
  let selectedMode       = 'A';
  let selectedTimeLimit  = 0;       // 0 = 無限制
  let showCamera         = true;

  let ws               = null;
  let streamHandle     = null;    // MediaStream
  let frameTimer       = null;    // setInterval ID
  let countdownTimer   = null;    // setInterval ID
  let timeRemaining    = 0;
  let gameActive       = false;
  let isProcessingFrame = false; // 防堆積鎖定

  // ═══════════════════════════════════════════════════════
  //  工具函數：切換畫面
  // ═══════════════════════════════════════════════════════
  function showScreen(screen) {
    [screenMenu, screenGame, screenResult].forEach(s => s.classList.remove('active'));
    screen.classList.add('active');
  }

  // ═══════════════════════════════════════════════════════
  //  選單：分組按鈕選擇
  // ═══════════════════════════════════════════════════════
  function initSegmentedGroup(groupEl, onSelect) {
    groupEl.querySelectorAll('.seg-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        groupEl.querySelectorAll('.seg-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        onSelect(btn.dataset.value);
      });
    });
  }

  initSegmentedGroup(modeGroup, val => { selectedMode = val; });
  initSegmentedGroup(timeGroup, val => { selectedTimeLimit = parseInt(val, 10); });

  cameraToggle.addEventListener('change', () => {
    showCamera = cameraToggle.checked;
    cameraToggleText.textContent = showCamera ? '開啟' : '關閉';
  });

  // ═══════════════════════════════════════════════════════
  //  WebSocket 管理
  // ═══════════════════════════════════════════════════════
  function connectWS(onOpen) {
    if (ws && ws.readyState === WebSocket.OPEN) {
      if (onOpen) onOpen();
      return;
    }
    ws = new WebSocket(WS_URL);

    ws.onopen = () => {
      setWsStatus(true);
      if (onOpen) onOpen();
    };

    ws.onmessage = (evt) => {
      let data;
      try { data = JSON.parse(evt.data); } catch { return; }
      handleServerMessage(data);
    };

    ws.onclose = () => {
      setWsStatus(false);
      ws = null;
    };

    ws.onerror = (e) => {
      console.error('WS error', e);
      setWsStatus(false);
    };
  }

  function sendJSON(obj) {
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify(obj));
    }
  }

  function setWsStatus(connected) {
    if (connected) {
      wsDot.className = 'ws-dot connected';
      wsLabel.textContent = '已連線';
    } else {
      wsDot.className = 'ws-dot disconnected';
      wsLabel.textContent = '未連線';
    }
  }

  // ═══════════════════════════════════════════════════════
  //  處理後端訊息
  // ═══════════════════════════════════════════════════════
  function handleServerMessage(data) {
    if (!gameActive) return;

    if (data.type === 'init_ok') {
      updateQuestion(data.question, data.answer);
      updateScore(data.score, data.total);
      feedbackText.textContent = '舉起手指示意答案';
      feedbackText.className = 'feedback-idle';
      return;
    }

    if (data.type === 'frame_result') {
      isProcessingFrame = false; // 解除鎖定
      // 辨識數字
      const num = data.detected_number;
      gestureDisplay.textContent = (num !== null && num !== undefined) ? num : '—';

      // 雙手細節（僅模式 B 且有雙手時）
      if (data.left_hand !== null && data.left_hand !== undefined &&
          data.right_hand !== null && data.right_hand !== undefined) {
        handDetail.classList.remove('hidden');
        leftHandVal.textContent  = data.left_hand;
        rightHandVal.textContent = data.right_hand;
      } else {
        handDetail.classList.add('hidden');
      }

      // 答題回饋
      if (data.just_answered) {
        feedbackText.textContent = '✓ 答對！';
        feedbackText.className = 'feedback-correct';
        // 200ms 後復原提示
        setTimeout(() => {
          if (gameActive) {
            feedbackText.textContent = '舉起手指示意答案';
            feedbackText.className = 'feedback-idle';
          }
        }, 200);
      }

      // 更新題目與分數
      if (data.question) updateQuestion(data.question, data.answer);
      updateScore(data.score, data.total);
    }
  }

  function updateQuestion(q, _a) {
    questionDisplay.textContent = q || '—';
  }

  function updateScore(score, total) {
    scoreDisplay.textContent = score || 0;
    // 結算用
    resultScore.textContent = score || 0;
    resultTotal.textContent = total || 0;
  }

  // ═══════════════════════════════════════════════════════
  //  WebRTC 攝影機
  // ═══════════════════════════════════════════════════════
  async function startCamera() {
    try {
      streamHandle = await navigator.mediaDevices.getUserMedia({
        video: { width: { ideal: 640 }, height: { ideal: 480 }, facingMode: 'user' },
        audio: false,
      });
      cameraVideo.srcObject = streamHandle;
      await cameraVideo.play();
    } catch (err) {
      console.error('Camera error:', err);
      alert('無法存取攝影機：' + err.message);
    }
  }

  function stopCamera() {
    if (streamHandle) {
      streamHandle.getTracks().forEach(t => t.stop());
      streamHandle = null;
    }
    cameraVideo.srcObject = null;
  }

  // ═══════════════════════════════════════════════════════
  //  影像幀擷取與傳送
  // ═══════════════════════════════════════════════════════
  function startFrameCapture() {
    const ctx = captureCanvas.getContext('2d');
    frameTimer = setInterval(() => {
      if (!ws || ws.readyState !== WebSocket.OPEN) return;
      if (!cameraVideo.videoWidth) return;
      if (isProcessingFrame) return; // 沒處理完不要送新圖

      isProcessingFrame = true;
      const scale = 0.5; // 降低解度
      captureCanvas.width  = cameraVideo.videoWidth * scale;
      captureCanvas.height = cameraVideo.videoHeight * scale;
      ctx.drawImage(cameraVideo, 0, 0, captureCanvas.width, captureCanvas.height);

      const b64 = captureCanvas.toDataURL('image/jpeg', 0.3);
      sendJSON({ type: 'frame', data: b64 });
    }, FRAME_INTERVAL);
  }

  function stopFrameCapture() {
    if (frameTimer) { clearInterval(frameTimer); frameTimer = null; }
  }

  // ═══════════════════════════════════════════════════════
  //  倒數計時
  // ═══════════════════════════════════════════════════════
  function startCountdown(seconds) {
    timeRemaining = seconds;
    timerDisplay.textContent = timeRemaining;
    countdownTimer = setInterval(() => {
      timeRemaining -= 1;
      timerDisplay.textContent = timeRemaining;
      if (timeRemaining <= 0) {
        endGame();
      }
    }, 1000);
  }

  function stopCountdown() {
    if (countdownTimer) { clearInterval(countdownTimer); countdownTimer = null; }
  }

  // ═══════════════════════════════════════════════════════
  //  遊戲流程
  // ═══════════════════════════════════════════════════════
  async function startGame() {
    gameActive = true;

    // 更新 UI 顯示設定
    if (selectedTimeLimit > 0) {
      timerBox.classList.remove('hidden');
    } else {
      timerBox.classList.add('hidden');
    }

    // 攝影機顯示/隱藏
    if (showCamera) {
      cameraVideo.style.display = '';
      cameraOffLabel.classList.add('hidden');
    } else {
      cameraVideo.style.display = 'none';
      cameraOffLabel.classList.remove('hidden');
    }

    showScreen(screenGame);

    // 啟動攝影機
    await startCamera();

    // 連線 WebSocket，連線後送 init
    connectWS(() => {
      sendJSON({ type: 'init', mode: selectedMode });
    });

    // 開始傳幀
    startFrameCapture();

    // 計時（若有）
    if (selectedTimeLimit > 0) {
      startCountdown(selectedTimeLimit);
    }
  }

  function endGame() {
    gameActive = false;
    stopFrameCapture();
    stopCountdown();
    stopCamera();

    // 關閉 WS
    if (ws) { ws.close(); ws = null; }

    showScreen(screenResult);
  }

  function returnToMenu() {
    gameActive = false;
    stopFrameCapture();
    stopCountdown();
    stopCamera();
    if (ws) { ws.close(); ws = null; }
    setWsStatus(false);

    // 重置 feedback
    feedbackText.textContent = '舉起手指示意答案';
    feedbackText.className = 'feedback-idle';
    gestureDisplay.textContent = '—';
    questionDisplay.textContent = '—';
    handDetail.classList.add('hidden');

    showScreen(screenMenu);
  }

  // ═══════════════════════════════════════════════════════
  //  事件綁定
  // ═══════════════════════════════════════════════════════
  btnStart.addEventListener('click', startGame);
  btnMenu.addEventListener('click', returnToMenu);
  btnPlayAgain.addEventListener('click', startGame);
  btnBackMenu.addEventListener('click', () => { showScreen(screenMenu); });

  // ═══════════════════════════════════════════════════════
  //  初始畫面
  // ═══════════════════════════════════════════════════════
  showScreen(screenMenu);

})();
