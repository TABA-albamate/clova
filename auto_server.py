# auto_server.py
from flask import Flask, request, jsonify
import os, json, base64, time, uuid, requests, re
from datetime import datetime, timedelta
import google.oauth2.credentials
from googleapiclient.discovery import build


# ─────────────────────────────────────────
# 0. 기본 설정
# ─────────────────────────────────────────
app = Flask(__name__)
app.secret_key = "your_secret_key"

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Google OAuth 클라이언트 정보 (credentials.json → “web” 블록)
with open("credentials.json") as f:
    google_creds = json.load(f)["web"]

# CLOVA OCR 엔드포인트 & 시크릿 (테스트용 하드코딩)
CLOVA_URL = (
    "각자의 url"
)
CLOVA_SECRET = "각자의 시크릿"
HEADERS = {"X-OCR-SECRET": CLOVA_SECRET, "Content-Type": "application/json"}


# ─────────────────────────────────────────
# 1. Google Calendar
# ─────────────────────────────────────────
def insert_to_calendar(ev: dict, token: str):
    """
    ev   : extract_schedule()가 반환한 일정 dict
    token: 사용자의 Google OAuth access_token
    """
    creds = google.oauth2.credentials.Credentials(
        token,
        token_uri=google_creds["token_uri"],
        client_id=google_creds["client_id"],
        client_secret=google_creds["client_secret"],
        scopes=["https://www.googleapis.com/auth/calendar.events"],
    )
    svc = build("calendar", "v3", credentials=creds)

    body = {
        "summary": f'{ev["name"]} ({ev["position"]})',  # 이름 + 포지션
        "start": {
            "dateTime": f'{ev["date"]}T{ev["start"]}:00',
            "timeZone": "Asia/Seoul",
        },
        "end": {
            "dateTime": f'{ev["date"]}T{ev["end"]}:00',
            "timeZone": "Asia/Seoul",
        },
        # 'description': f'포지션: {ev["position"]}',   # 필요 시 메모 칸
    }
    svc.events().insert(calendarId="primary", body=body).execute()


# ─────────────────────────────────────────
# 2. CLOVA OCR 호출
# ─────────────────────────────────────────
def call_clova(path: str) -> dict:
    """이미지 파일 경로 → CLOVA OCR JSON 응답"""
    with open(path, "rb") as f:
        img64 = base64.b64encode(f.read()).decode()

    payload = {
        "version": "V2",
        "requestId": str(uuid.uuid4()),
        "timestamp": int(time.time() * 1000),
        "enableTableDetection": True,
        "lang": "ko",
        "images": [
            {
                "name": "upload",
                "format": "jpg",
                "data": img64,
            }
        ],
    }
    res = requests.post(CLOVA_URL, headers=HEADERS, json=payload)
    res.raise_for_status()
    return res.json()


# ─────────────────────────────────────────
# 3. 표(JSON) → 근무일정 + 포지션
# ─────────────────────────────────────────
def extract_schedule(data: dict, target: str, year: int = 2025) -> list[dict]:
    """
    · data   : CLOVA OCR JSON
    · target : 찾을 이름(직원)
    · year   : 날짜에 연도가 없을 때 기본값

    반환 예시:
        {
          "name":     "김지성",
          "position": "포지션2",
          "date":     "2025-07-08",
          "start":    "09:00",
          "end":      "15:30"
        }
    """
    cells = data["images"][0]["tables"][0]["cells"]

    # 1. 셀 → 2-D 그리드 -----------------------------------------------------
    R = max(c["rowIndex"] for c in cells) + 1
    C = max(c["columnIndex"] for c in cells) + 1
    grid = [["" for _ in range(C)] for _ in range(R)]

    for c in cells:
        r, cidx = c["rowIndex"], c["columnIndex"]
        txt = " ".join(
            w["inferText"] for ln in c["cellTextLines"] for w in ln["cellWords"]
        ).strip()
        grid[r][cidx] = txt

    # 2. 날짜 행 (“날짜”가 맨 앞) -------------------------------------------
    date_row = next(i for i, row in enumerate(grid) if row[0].startswith("날짜"))
    date_map: dict[int, str | None] = {}
    cur_date = None
    for c, cell in enumerate(grid[date_row]):
        if m := re.search(r"(\d{1,2})\s*월\s*(\d{1,2})", cell):
            mm, dd = map(int, m.groups())
            cur_date = f"{year}-{mm:02d}-{dd:02d}"
        date_map[c] = cur_date

    # 3. 포지션 헤더 행 ------------------------------------------------------
    position_row = next(i for i, row in enumerate(grid) if row[0].startswith("포지션"))

    # 4. 시간대 영역(행) ------------------------------------------------------
    first_time_row = next(
        i for i, row in enumerate(grid) if re.fullmatch(r"\d{1,2}:\d{2}", row[0])
    )
    last_time_row = (
        next(i for i, row in enumerate(grid) if row[0].startswith("총 인원")) - 1
    )

    # 5. 본격 파싱 ----------------------------------------------------------
    schedules: list[dict] = []
    for r in range(first_time_row, last_time_row + 1):
        start_time = grid[r][0]  # 행 첫 칸이 시작시각
        for c in range(1, C):
            cell_txt = grid[r][c]
            if target not in cell_txt:
                continue

            # ── 종료시각 추출 ---------------------------------------
            end_time = None
            if m := re.search(rf"{re.escape(target)}\s*([\d.:]+)", cell_txt):
                raw = m.group(1)
                if ":" in raw:  # HH:MM
                    end_time = raw
                elif "." in raw:  # 13.5 → 13:30
                    h, frac = raw.split(".")
                    mm = int(float("0." + frac) * 60)
                    end_time = f"{int(h):02d}:{mm:02d}"
                else:  # 18 → 18:00
                    end_time = f"{int(raw):02d}:00"

            if not end_time:  # 종료시각 없으면 +1h
                hh, mm = map(int, start_time.split(":"))
                dt_end = datetime(year, 1, 1, hh, mm) + timedelta(hours=1)
                end_time = dt_end.strftime("%H:%M")

            date_str = date_map.get(c)
            if not date_str:
                continue

            position = grid[position_row][c].strip()

            schedules.append(
                {
                    "name": target,
                    "position": position,
                    "date": date_str,
                    "start": start_time,
                    "end": end_time,
                }
            )

    return schedules


# ─────────────────────────────────────────
# 4. Flask 엔드포인트
# ─────────────────────────────────────────
@app.route("/upload-image", methods=["POST"])
def upload_image():
    img   = request.files.get("image")
    token = request.form.get("access_token")
    name  = request.form.get("name")

    if not (img and token and name):
        return jsonify(error="image · name · access_token 모두 필요"), 400

    path = os.path.join(UPLOAD_FOLDER, img.filename)
    img.save(path)

    ocr_json  = call_clova(path)
    schedules = extract_schedule(ocr_json, name)

    for ev in schedules:
        insert_to_calendar(ev, token)

    return jsonify(status="success", count=len(schedules), data=schedules)


# ─────────────────────────────────────────
# 5. 실행
# ─────────────────────────────────────────
if __name__ == "__main__":
    app.run(debug=True, port=5001)
