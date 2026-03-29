"""
Math_Point3r — 後端 WebSocket 伺服器
FastAPI + MediaPipe 手勢辨識 + 算數題目生成
"""

import asyncio
import base64
import json
import logging
import operator
import random
from typing import Optional

import cv2
import mediapipe as mp
import numpy as np
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

# ─────────────────────────────────────────────
#  Logging
# ─────────────────────────────────────────────
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("math_pointer")

# ─────────────────────────────────────────────
#  FastAPI App
# ─────────────────────────────────────────────
app = FastAPI(title="Math_Point3r Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─────────────────────────────────────────────
#  MediaPipe Tasks 初始化
# ─────────────────────────────────────────────
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision

# ─────────────────────────────────────────────
#  手勢辨識核心
# ─────────────────────────────────────────────

# MediaPipe landmark indices
WRIST       = 0
THUMB_CMC   = 1
THUMB_MCP   = 2
THUMB_IP    = 3
THUMB_TIP   = 4
INDEX_MCP   = 5
INDEX_PIP   = 6
INDEX_DIP   = 7
INDEX_TIP   = 8
MIDDLE_MCP  = 9
MIDDLE_PIP  = 10
MIDDLE_DIP  = 11
MIDDLE_TIP  = 12
RING_MCP    = 13
RING_PIP    = 14
RING_DIP    = 15
RING_TIP    = 16
PINKY_MCP   = 17
PINKY_PIP   = 18
PINKY_DIP   = 19
PINKY_TIP   = 20


def count_fingers(hand_landmarks, handedness_label: str) -> int:
    """
    計算一隻手伸出的手指數 (0~5)。
    hand_landmarks: mediapipe NormalizedLandmarkList
    handedness_label: 'Left' 或 'Right'（MediaPipe 回傳的手性，是鏡像視角的）
    """
    lm = hand_landmarks

    # ── 判斷各手指是否伸直 ──────────────────────────────────
    
    # 拇指：MediaPipe handedness 是鏡像視角
    thumb_straight = False
    if handedness_label == "Right":
        if lm[THUMB_TIP].x > lm[THUMB_IP].x:
            thumb_straight = True
    else:
        if lm[THUMB_TIP].x < lm[THUMB_IP].x:
            thumb_straight = True

    # 其餘四指
    index_straight  = lm[INDEX_TIP].y < lm[INDEX_PIP].y
    middle_straight = lm[MIDDLE_TIP].y < lm[MIDDLE_PIP].y
    ring_straight   = lm[RING_TIP].y < lm[RING_PIP].y
    pinky_straight  = lm[PINKY_TIP].y < lm[PINKY_PIP].y

    T, I, M, R, P = thumb_straight, index_straight, middle_straight, ring_straight, pinky_straight

    # ── 根據規則對應數字 ──────────────────────────────────
    # 6: 彎曲食指中指無名指，只剩下大拇指跟小拇指
    if T and not I and not M and not R and P: return 6
    # 7: 彎曲中指無名指小拇指，只剩下大拇指跟食指
    if T and I and not M and not R and not P: return 7
    # 8: 彎曲無名指跟小拇指，只剩下大拇指食指跟中指
    if T and I and M and not R and not P: return 8
    # 9: 只彎曲小拇指，其他4隻手指都伸直
    if T and I and M and R and not P: return 9
    # 4: 只彎曲大拇指，其他手指伸直
    if not T and I and M and R and P: return 4
    # 3: 彎曲大拇指跟小拇指
    if not T and I and M and R and not P: return 3
    # 2: 只伸直食指跟中指
    if not T and I and M and not R and not P: return 2
    # 1: 伸直食指
    if not T and I and not M and not R and not P: return 1
    
    # 補充常規的 0 與 5
    if T and I and M and R and P: return 5
    if not T and not I and not M and not R and not P: return 0

    return 0  # 未符合以上規則時，回傳 0


def decode_frame(base64_data: str) -> Optional[np.ndarray]:
    """將 Base64 字串解碼成 OpenCV BGR 影像。"""
    # 移除 data URL 前綴（若存在）
    if "," in base64_data:
        base64_data = base64_data.split(",", 1)[1]
    try:
        img_bytes = base64.b64decode(base64_data)
        arr = np.frombuffer(img_bytes, dtype=np.uint8)
        frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        return frame
    except Exception as e:
        logger.warning(f"Frame decode error: {e}")
        return None


def detect_gesture(frame: np.ndarray, detector) -> dict:
    """
    對單一影像幀執行手勢辨識。
    回傳：
      {
        "left_hand":  int | None,   # 畫面左側手指數
        "right_hand": int | None,   # 畫面右側手指數
        "detected_number": int | None,
      }
    """
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
    
    try:
        detection_result = detector.detect(mp_image)
    except Exception as e:
        logger.warning(f"Detection error: {e}")
        return {"left_hand": None, "right_hand": None, "detected_number": None}

    if not detection_result.hand_landmarks:
        return {"left_hand": None, "right_hand": None, "detected_number": None}

    # 收集偵測到的每隻手：(wrist_x, finger_count)
    detected_hands = []
    for idx, hand_lm in enumerate(detection_result.hand_landmarks):
        label = detection_result.handedness[idx][0].category_name  # 'Left' or 'Right'
        wrist_x = hand_lm[WRIST].x        # 0.0（最左）~ 1.0（最右）
        count = count_fingers(hand_lm, label)
        detected_hands.append((wrist_x, count))

    if len(detected_hands) == 0:
        return {"left_hand": None, "right_hand": None, "detected_number": None}

    if len(detected_hands) == 1:
        _, count = detected_hands[0]
        return {
            "left_hand": None,
            "right_hand": None,
            "detected_number": count,
        }

    # 雙手：依 wrist_x 排序，x 較小者為畫面左側（十位數）
    detected_hands.sort(key=lambda h: h[0])
    left_count  = detected_hands[0][1]   # 十位數
    right_count = detected_hands[1][1]   # 個位數
    number = left_count * 10 + right_count

    return {
        "left_hand":        left_count,
        "right_hand":       right_count,
        "detected_number":  number,
    }


# ─────────────────────────────────────────────
#  題目生成（模式 B：答案 10~99）
# ─────────────────────────────────────────────

OPERATORS = {
    "+": operator.add,
    "-": operator.sub,
    "*": operator.mul,
}


def generate_question_mode_a() -> dict:
    """模式 A：answer ∈ [0, 10]"""
    answer = random.randint(0, 10)
    # 簡單加減法
    a = random.randint(0, answer)
    b = answer - a
    op = "+"
    return {"question": f"{a} + {b}", "answer": answer}


def generate_question_mode_b() -> dict:
    """模式 B：answer ∈ [10, 99]"""
    max_attempts = 200
    for _ in range(max_attempts):
        op_sym = random.choice(["+", "-", "*"])
        op_fn  = OPERATORS[op_sym]

        if op_sym == "+":
            a = random.randint(1, 90)
            b = random.randint(1, 90)
        elif op_sym == "-":
            a = random.randint(10, 99)
            b = random.randint(0, a - 10)
        else:  # *
            a = random.randint(2, 9)
            b = random.randint(2, 9)

        result = op_fn(a, b)
        if 10 <= result <= 99:
            op_display = "×" if op_sym == "*" else op_sym
            return {"question": f"{a} {op_display} {b}", "answer": int(result)}

    # Fallback
    return {"question": "10 + 10", "answer": 20}


# ─────────────────────────────────────────────
#  遊戲狀態管理
# ─────────────────────────────────────────────

class GameSession:
    def __init__(self, mode: str):
        self.mode    = mode          # 'A' or 'B'
        self.score   = 0
        self.total   = 0
        self.current = self._new_question()

        # 防抖：連續 N 幀辨識一致才算答對
        self._stable_count    = 0
        self._stable_number   = None
        self.STABLE_THRESHOLD = 3    # 因遠端伺服器算力有限，大幅降低連續一致門檻（從 8 降為 3）

    def _new_question(self) -> dict:
        if self.mode.upper() == "B":
            return generate_question_mode_b()
        return generate_question_mode_a()

    def check(self, detected: Optional[int]) -> dict:
        """
        檢查辨識數字是否與答案相符（含防抖）。
        回傳 is_correct=True 時表示「這一幀觸發了答對」。
        """
        if detected is None:
            self._stable_count  = 0
            self._stable_number = None
            return {"is_correct": False, "just_answered": False}

        if detected == self._stable_number:
            self._stable_count += 1
        else:
            self._stable_count  = 1
            self._stable_number = detected

        if (
            self._stable_count >= self.STABLE_THRESHOLD
            and self._stable_number == self.current["answer"]
        ):
            # 答對！
            self.score         += 1
            self.total         += 1
            self.current        = self._new_question()
            self._stable_count  = 0
            self._stable_number = None
            return {"is_correct": True, "just_answered": True}

        return {"is_correct": False, "just_answered": False}


# ─────────────────────────────────────────────
#  WebSocket 端點
# ─────────────────────────────────────────────

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    logger.info("WebSocket connected")

    session: Optional[GameSession] = None

    base_options = mp_python.BaseOptions(model_asset_path='hand_landmarker.task')
    options = vision.HandLandmarkerOptions(
        base_options=base_options,
        num_hands=2,
        min_hand_detection_confidence=0.6,
        min_hand_presence_confidence=0.5,
        min_tracking_confidence=0.5
    )
    
    with vision.HandLandmarker.create_from_options(options) as detector:
        try:
            while True:
                raw = await websocket.receive_text()

                # ── 解析訊息 ──────────────────
                try:
                    msg = json.loads(raw)
                except json.JSONDecodeError:
                    # 相容舊版：純 base64 字串
                    msg = {"type": "frame", "data": raw}

                msg_type = msg.get("type", "frame")

                # ── 初始化遊戲 ────────────────
                if msg_type == "init":
                    mode    = msg.get("mode", "A")
                    session = GameSession(mode)
                    logger.info(f"Game initialized: mode={mode}")
                    await websocket.send_text(json.dumps({
                        "type":     "init_ok",
                        "question": session.current["question"],
                        "answer":   session.current["answer"],
                        "score":    session.score,
                        "total":    session.total,
                    }))
                    continue

                # ── 影像幀處理 ────────────────
                if msg_type == "frame":
                    frame_b64 = msg.get("data", "")
                    if not frame_b64:
                        continue

                    # 在執行緒池執行 CPU 密集作業，不阻塞事件迴圈
                    loop = asyncio.get_event_loop()
                    frame = await loop.run_in_executor(
                        None, decode_frame, frame_b64
                    )
                    if frame is None:
                        continue

                    gesture = await loop.run_in_executor(
                        None, detect_gesture, frame, detector
                    )

                    detected_number = gesture["detected_number"]

                    # 初始化前不做答案驗證
                    just_answered = False
                    if session is not None:
                        result = session.check(detected_number)
                        just_answered = result["just_answered"]

                    response = {
                        "type":             "frame_result",
                        "detected_number":  detected_number,
                        "left_hand":        gesture["left_hand"],
                        "right_hand":       gesture["right_hand"],
                        "question":         session.current["question"] if session else None,
                        "answer":           session.current["answer"]   if session else None,
                        "score":            session.score               if session else 0,
                        "total":            session.total               if session else 0,
                        "just_answered":    just_answered,
                    }
                    await websocket.send_text(json.dumps(response))

                # ── 重置遊戲 ──────────────────
                elif msg_type == "reset":
                    if session:
                        mode    = session.mode
                        session = GameSession(mode)
                        await websocket.send_text(json.dumps({
                            "type":     "init_ok",
                            "question": session.current["question"],
                            "answer":   session.current["answer"],
                            "score":    session.score,
                            "total":    session.total,
                        }))

        except WebSocketDisconnect:
            logger.info("WebSocket disconnected")
        except Exception as e:
            logger.error(f"Unexpected error: {e}", exc_info=True)


# ─────────────────────────────────────────────
#  健康檢查
# ─────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok"}


# ─────────────────────────────────────────────
#  Entry point
# ─────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
