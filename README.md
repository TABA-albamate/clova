# 🤖 CLOVA OCR + Gemini 2.0 Flash 일정 등록 시스템

## 📋 개요
근무일정표 이미지를 CLOVA OCR로 분석하고, Gemini 2.0 Flash로 일정을 추출하여 Google Calendar에 자동 등록하는 시스템입니다.

## ✨ 주요 기능
- 📸 **이미지 업로드**: 근무표 이미지 자동 분석
- 🔍 **CLOVA OCR**: 정확한 텍스트 및 표 구조 추출
- 🤖 **Gemini 2.0 Flash**: 지능형 일정 분석 및 추출
- 📅 **Google Calendar**: 자동 일정 등록
- 🔐 **Google OAuth 2.0**: 안전한 인증
- 🌐 **범용 지원**: 다양한 근무표 형식 지원

## 🚀 빠른 시작

### Docker 배포 (권장)
```bash
# 1. 환경 변수 설정
cp env.example .env
# .env 파일 편집하여 API 키 입력

# 2. Docker 실행
docker-compose up -d

# 3. 서비스 접속
# OAuth: http://localhost:5000
# 메인: http://localhost:5001
```

### 직접 설치
```bash
# 1. 의존성 설치
pip install -r requirements.txt

# 2. 환경 변수 설정
export GEMINI_API_KEY=your_key
export CLOVA_URL=your_url
export CLOVA_SECRET=your_secret

# 3. 서버 실행
python app.py & python auto_server.py
```

## 🛠️ API 키 설정

### 1. Gemini 2.0 Flash API 키
1. [Google AI Studio](https://makersuite.google.com/app/apikey) 접속
2. "Create API Key" 클릭
3. API 키 복사

### 2. CLOVA OCR 설정
1. [NAVER Cloud Platform](https://clovadubbing.naver.com/) 접속
2. CLOVA OCR 서비스 신청
3. API Gateway에서 URL과 Secret 발급

### 3. Google OAuth 2.0 설정
1. [Google Cloud Console](https://console.cloud.google.com/apis/credentials) 접속
2. "Create Credentials" → "OAuth 2.0 Client IDs"
3. Application type: "Web application"
4. Authorized redirect URIs: `http://localhost:5000/oauth2callback`

## 📖 사용법

### 1. 초기 설정
```bash
# 브라우저에서 OAuth 인증
http://localhost:5000

# 토큰 확인
curl http://localhost:5000/get-token
```

### 2. API 호출 예시
```bash
# Postman 또는 curl 사용
POST http://localhost:5001/upload-image
Content-Type: multipart/form-data

- image: [근무표 이미지 파일]
- access_token: [Google OAuth 토큰]
- name: [직원 이름]
```

### 3. 응답 예시
```json
{
  "status": "success",
  "total_schedules": 3,
  "registered_schedules": 3,
  "data": [
    {
      "name": "김지성",
      "position": "포지션1",
      "date": "2025-07-07",
      "start": "09:00",
      "end": "10:00"
    }
  ]
}
```

## 🔧 지원하는 형식

### 날짜 형식
- ✅ "MM월 DD일" (07월 07일)
- ✅ "MM/DD" (7/7)
- ✅ "MM-DD" (7-7)

### 시간 형식
- ✅ "HH:MM" (09:00)
- ✅ "HH시 MM분" (9시 30분)
- ✅ "HH.MM" (9.30)

### 근무표 형식
- ✅ 월별 근무표
- ✅ 주별 근무표
- ✅ 일별 근무표
- ✅ 다양한 직원 이름

## 📊 주요 변경사항

### v2.0 - Gemini 2.0 Flash 통합
- ❌ 기존 수동 스케줄 매핑 코드 제거
- ✅ Gemini 2.0 Flash를 통한 지능형 일정 분석
- ✅ 범용적 근무표 형식 지원
- ✅ 정확도 향상 및 유지보수성 개선
- ✅ 열 인덱스 매칭을 통한 정확한 날짜-시간 연결

## 🐳 배포 옵션

### Docker 배포
- `docker-compose up -d`: 로컬 배포
- AWS EC2: 클라우드 서버 배포
- Google Cloud Run: 서버리스 배포

### 직접 배포
- Python 가상환경 설정
- 환경 변수 구성
- 서비스 실행

## 🔒 보안

- API 키는 환경 변수로 관리
- OAuth 2.0을 통한 안전한 인증
- HTTPS 사용 권장
- 정기적인 API 키 교체

## 📞 지원

- [배포 가이드](DEPLOYMENT.md) 참조
- 문제 해결: 로그 확인 및 환경 변수 점검
- API 키 유효성 확인

## �� 라이선스

MIT License
