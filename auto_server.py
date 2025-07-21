# auto_server.py
from flask import Flask, request, jsonify
import os, json, base64, time, uuid, requests, re
from datetime import datetime, timedelta
import google.oauth2.credentials
from googleapiclient.discovery import build
import google.generativeai as genai
from config import *


# ─────────────────────────────────────────
# 0. 기본 설정
# ─────────────────────────────────────────
app = Flask(__name__)
app.secret_key = SECRET_KEY

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Google OAuth 클라이언트 정보 (credentials.json → "web" 블록)
with open("credentials.json") as f:
    google_creds = json.load(f)["web"]

# CLOVA OCR 헤더 설정
HEADERS = {"X-OCR-SECRET": CLOVA_SECRET, "Content-Type": "application/json"}

# Gemini 2.0 Flash API 설정
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-2.0-flash-exp')


# ─────────────────────────────────────────
# 1. Google Calendar
# ─────────────────────────────────────────
def insert_to_calendar(ev: dict, token: str):
    """
    ev   : Gemini가 분석한 일정 dict
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
# 3. Gemini 2.0 Flash로 OCR 결과 분석
# ─────────────────────────────────────────
def analyze_schedule_with_gemini(ocr_data: dict, target_name: str, year: int = 2025) -> list[dict]:
    """
    CLOVA OCR 결과를 Gemini 2.0 Flash로 분석하여 근무일정 추출
    
    Args:
        ocr_data: CLOVA OCR JSON 결과
        target_name: 찾을 직원 이름
        year: 연도 (기본값: 2025)
    
    Returns:
        근무일정 리스트
    """
    
    # 디버깅: OCR 데이터 구조 확인
    print(f"🔍 OCR 데이터 구조 분석:")
    try:
        if "images" in ocr_data and len(ocr_data["images"]) > 0:
            image = ocr_data["images"][0]
            if "tables" in image and len(image["tables"]) > 0:
                table = image["tables"][0]
                cells = table.get("cells", [])
                print(f"   📊 테이블 정보: {len(cells)}개 셀")
                
                # 날짜 정보가 있는 셀들 찾기
                date_cells = []
                for cell in cells:
                    cell_text = " ".join(
                        w["inferText"] for ln in cell.get("cellTextLines", []) 
                        for w in ln.get("cellWords", [])
                    ).strip()
                    # 월/일 패턴 찾기 (1월~12월, 01월~12월, 1/1~12/31 등)
                    if any(pattern in cell_text for pattern in ["월", "/", "-"]) and any(str(i) in cell_text for i in range(1, 32)):
                        date_cells.append(f"행{cell['rowIndex']}열{cell['columnIndex']}: {cell_text}")
                
                print(f"   📅 날짜 관련 셀들:")
                for date_cell in date_cells[:10]:  # 처음 10개만
                    print(f"      {date_cell}")
                
                # 대상 직원이 있는 셀들 찾기
                target_cells = []
                for cell in cells:
                    cell_text = " ".join(
                        w["inferText"] for ln in cell.get("cellTextLines", []) 
                        for w in ln.get("cellWords", [])
                    ).strip()
                    if target_name in cell_text:
                        target_cells.append(f"행{cell['rowIndex']}열{cell['columnIndex']}: {cell_text}")
                
                print(f"   👤 {target_name} 관련 셀들:")
                for target_cell in target_cells:
                    print(f"      {target_cell}")
                
                # 날짜와 직원 매칭 정보 출력
                print(f"   🔗 날짜-직원 매칭 분석:")
                for target_cell in target_cells:
                    # 셀 정보에서 열 인덱스 추출
                    if "열" in target_cell:
                        col_info = target_cell.split("열")[1].split(":")[0]
                        try:
                            col_idx = int(col_info)
                            # 해당 열의 날짜 찾기
                            for date_cell in date_cells:
                                if f"열{col_idx}:" in date_cell:
                                    date_info = date_cell.split(": ")[1]
                                    print(f"      {target_cell} → {date_info}")
                                    break
                        except ValueError:
                            pass
            else:
                print("   ❌ 테이블 데이터 없음")
        else:
            print("   ❌ 이미지 데이터 없음")
    except Exception as e:
        print(f"   ❌ 데이터 분석 실패: {e}")
    
    # Gemini에게 전달할 프롬프트 구성
    prompt = f"""
당신은 근무일정표를 분석하는 전문가입니다.
CLOVA OCR로 추출된 표 데이터를 분석하여 특정 직원의 근무일정을 JSON 형태로 반환해주세요.

**분석 대상 직원**: {target_name}
**기준 연도**: {year}년

**CLOVA OCR 결과**:
{json.dumps(ocr_data, ensure_ascii=False, indent=2)}

**분석 방법**:
1. **단계별 분석**:
   - 먼저 표의 헤더 행에서 모든 날짜를 찾으세요
   - 각 날짜 열에서 {target_name}이 언급된 셀을 찾으세요
   - 해당 셀의 시간 정보를 추출하세요

2. **날짜 매칭**:
   - 헤더의 날짜와 {target_name}이 있는 셀의 열 인덱스를 매칭하세요
   - 예: 헤더에 "07월 11일"이 열17에 있다면, 열17에서 {target_name} 찾기

3. **시간 추출**:
   - {target_name}이 있는 셀에서 시간 정보 추출
   - "HH:MM" 형식으로 변환
   - 종료 시간이 없으면 시작 시간 + 1시간

**날짜 형식 처리**:
- "MM월 DD일" 형식 → "YYYY-MM-DD"로 변환
- "MM/DD" 형식 → "YYYY-MM-DD"로 변환
- "MM-DD" 형식 → "YYYY-MM-DD"로 변환
- 연도가 없는 경우 {year}년 사용

**시간 형식 처리**:
- "HH:MM" 형식 유지
- "HH시 MM분" → "HH:MM"으로 변환
- "HH.MM" → "HH:MM"으로 변환

**반환 형식** (JSON 배열):
[
  {{
    "name": "{target_name}",
    "position": "포지션명",
    "date": "YYYY-MM-DD",
    "start": "HH:MM",
    "end": "HH:MM"
  }}
]

**매우 중요한 주의사항**:
- 정확한 JSON 형식으로만 응답하세요
- 설명이나 추가 텍스트는 포함하지 마세요
- 날짜와 시간 형식을 정확히 지켜주세요
- 찾을 수 없는 경우 빈 배열 []을 반환하세요
- **{target_name}이 언급된 모든 셀을 반드시 포함하세요**
- **열 인덱스를 정확히 매칭하여 날짜와 시간을 연결하세요**
- **하나도 빠뜨리지 마세요**
"""

    try:
        # Gemini API 호출
        response = model.generate_content(prompt)
        
        # 응답에서 JSON 추출
        response_text = response.text.strip()
        
        # 코드 블록 제거 (```json ... ```)
        if response_text.startswith("```json"):
            response_text = response_text[7:]  # ```json 제거
        if response_text.endswith("```"):
            response_text = response_text[:-3]  # ``` 제거
        
        response_text = response_text.strip()
        
        # 디버깅: Gemini 응답 로그 출력
        print(f"🤖 Gemini 응답:")
        print(f"   {response_text}")
        
        # JSON 파싱
        try:
            schedules = json.loads(response_text)
            
            # 결과 검증
            if isinstance(schedules, list):
                print(f"✅ Gemini 분석 완료: {len(schedules)}개 일정 발견")
                for schedule in schedules:
                    print(f"   - {schedule.get('date')} {schedule.get('start')}-{schedule.get('end')} ({schedule.get('position')})")
                return schedules
            else:
                print("❌ Gemini 응답이 리스트 형식이 아닙니다")
                return []
                
        except json.JSONDecodeError as e:
            print(f"❌ Gemini 응답 JSON 파싱 실패: {e}")
            print(f"응답 내용: {response_text}")
            return []
            
    except Exception as e:
        print(f"❌ Gemini API 호출 실패: {e}")
        return []


# ─────────────────────────────────────────
# 4. Flask 엔드포인트
# ─────────────────────────────────────────
@app.route("/")
def index():
    return """
    <h1>🤖 CLOVA OCR + Gemini 2.0 Flash 일정 등록 서버</h1>
    <p>서버가 정상적으로 실행 중입니다!</p>
    <h2>📋 사용 방법</h2>
    <ul>
        <li><strong>POST /upload-image</strong> - 이미지 업로드 및 일정 등록</li>
        <li><strong>GET /health</strong> - 서버 상태 확인</li>
    </ul>
    <h2>🔧 API 호출 예시</h2>
    <pre>
POST http://localhost:5001/upload-image
Content-Type: multipart/form-data

- image: [파일]
- access_token: [Google OAuth 토큰]
- name: [직원 이름]
    </pre>
    """

@app.route("/health")
def health():
    return jsonify({"status": "healthy", "message": "서버가 정상 작동 중입니다"})

@app.route("/upload-image", methods=["POST"])
def upload_image():
    print("=== POST /upload-image 요청 받음 ===")
    
    img   = request.files.get("image")
    token = request.form.get("access_token")
    name  = request.form.get("name")

    print(f"📁 이미지: {img.filename if img else 'None'}")
    print(f"🔑 토큰: {token[:20] + '...' if token else 'None'}")
    print(f"👤 이름: {name}")

    if not (img and token and name):
        print("❌ 필수 파라미터 누락")
        return jsonify(error="image · name · access_token 모두 필요"), 400

    path = os.path.join(UPLOAD_FOLDER, img.filename)
    img.save(path)
    print(f"💾 파일 저장: {path}")

    # CLOVA OCR 호출
    print(f"🔄 CLOVA OCR 분석 중: {img.filename}")
    try:
        ocr_json = call_clova(path)
        print(f"✅ CLOVA OCR 성공: {len(ocr_json.get('images', []))}개 이미지")
    except Exception as e:
        print(f"❌ CLOVA OCR 실패: {e}")
        return jsonify(error=f"CLOVA OCR 실패: {e}"), 500
    
    # Gemini로 일정 분석
    print(f"🤖 Gemini 2.0 Flash로 일정 분석 중: {name}")
    try:
        schedules = analyze_schedule_with_gemini(ocr_json, name)
        print(f"✅ Gemini 분석 완료: {len(schedules)}개 일정")
    except Exception as e:
        print(f"❌ Gemini 분석 실패: {e}")
        return jsonify(error=f"Gemini 분석 실패: {e}"), 500

    # Google Calendar에 일정 등록
    success_count = 0
    for ev in schedules:
        try:
            insert_to_calendar(ev, token)
            success_count += 1
            print(f"✅ 일정 등록 완료: {ev['date']} {ev['start']}-{ev['end']}")
        except Exception as e:
            print(f"❌ 일정 등록 실패: {e}")

    print(f"=== 요청 완료: {success_count}/{len(schedules)}개 일정 등록 ===")
    return jsonify(
        status="success", 
        total_schedules=len(schedules),
        registered_schedules=success_count,
        data=schedules
    )


# ─────────────────────────────────────────
# 5. 실행
# ─────────────────────────────────────────
if __name__ == "__main__":
    app.run(debug=True, port=5001)
