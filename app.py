from flask import Flask, redirect, request, session, url_for, jsonify
import os
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
import google.oauth2.credentials

# Google OAuth 로그인 및 토큰 발급 테스트용 서버 

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # 세션 암호화용 비밀키
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'  # HTTPS 없어도 인증 허용 (테스트)

CLIENT_SECRETS_FILE = "credentials.json" #OAuth 클라이언트 키 파일
SCOPES = [
  'https://www.googleapis.com/auth/calendar.events',
  'https://www.googleapis.com/auth/calendar'
]
# 홈페이지 라우트 : 링크 클릭시 구글 인증 시작 
@app.route('/')
def index():
    return '<a href="/authorize">📆 구글 캘린더 연결</a>'

# ==== 구글 인증 URL 생성 후 리디렉션 =====
@app.route('/authorize')
def authorize():
    redirect_uri = url_for('oauth2callback', _external=True)
    print(f"📢 현재 redirect_uri: {redirect_uri}")  # 터미널에서 리디렉션 주소 확인용

    flow = Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE,
        scopes=SCOPES,
        redirect_uri=redirect_uri,
    )
    auth_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true'
    )
    session['state'] = state
    return redirect(auth_url)

# ==== 인증 완료 후 Google 이 콜백해주는 엔드포인트 ====
@app.route('/oauth2callback')
def oauth2callback():
    state = session['state']
    flow = Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE,
        scopes=SCOPES,
        state=state,
        redirect_uri=url_for('oauth2callback', _external=True)
    )
    flow.fetch_token(authorization_response=request.url)

    credentials = flow.credentials

    # Access token 출력!
    print("🔑 access_token:", credentials.token)

    #세션에 credentials 저장
    session['credentials'] = credentials_to_dict(credentials)
    return redirect(url_for('create_event'))

# ==== 테스트용 일정 생성 (1개 등록) ====
@app.route('/create_event')
def create_event():
    credentials = google.oauth2.credentials.Credentials(**session['credentials'])
    service = build('calendar', 'v3', credentials=credentials)

    event = {
        'summary': 'AI 자동 등록 테스트',
        'start': {'dateTime': '2025-07-03T10:00:00', 'timeZone': 'Asia/Seoul'},
        'end': {'dateTime': '2025-07-03T11:00:00', 'timeZone': 'Asia/Seoul'},
    }

    created_event = service.events().insert(calendarId='primary', body=event).execute()
    return f'✅ 일정 생성 완료! 👉 <a href="{created_event.get("htmlLink")}">{created_event.get("summary")}</a>'

# === access_token을 JSON으로 반환하는 라우트 (Postman용) ===
@app.route('/get-token')
def get_token():
    creds = session.get('credentials')
    return jsonify({"access_token": creds['token']})

# credentials 객체를 딕셔너리로 변환
def credentials_to_dict(creds):
    return {
        'token': creds.token,
        'refresh_token': creds.refresh_token,
        'token_uri': creds.token_uri,
        'client_id': creds.client_id,
        'client_secret': creds.client_secret,
        'scopes': creds.scopes
    }


if __name__ == '__main__':
    app.run(debug=True)