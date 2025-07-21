# config.py
# 설정 파일

# Gemini 2.0 Flash API 키
# https://makersuite.google.com/app/apikey 에서 발급받으세요
GEMINI_API_KEY = "AIzaSyA83Ym8uZw1UNInAASgYkBCu0wIgWIEgQU"

# CLOVA OCR 설정
CLOVA_URL = (
    "https://qadl0cvsw0.apigw.ntruss.com/custom/v1/"
    "43963/b35c0f2c30668154bd4239a45381baa3d91748646e460ff927f9f2010305fb0b/general"
)
CLOVA_SECRET = "U0xKTGFPeUhjaXhaWXpVUVZPTlFUSVVlUUZWWGlXYWw="

# Flask 설정
SECRET_KEY = "clova_schedule_2025_secure_key_8f7e6d5c4b3a2918"  # 안전한 랜덤 키
UPLOAD_FOLDER = "uploads"

# 서버 포트
OAUTH_SERVER_PORT = 5000
AUTO_SERVER_PORT = 5001 