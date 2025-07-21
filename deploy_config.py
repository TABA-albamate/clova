# deploy_config.py
# 배포 환경 설정 파일

import os

# 환경 변수에서 설정 가져오기 (보안을 위해)
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '')
CLOVA_URL = os.getenv('CLOVA_URL', '')
CLOVA_SECRET = os.getenv('CLOVA_SECRET', '')

# Flask 설정
SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key-change-this')
UPLOAD_FOLDER = "uploads"

# 서버 포트
OAUTH_SERVER_PORT = int(os.getenv('OAUTH_SERVER_PORT', 5000))
AUTO_SERVER_PORT = int(os.getenv('AUTO_SERVER_PORT', 5001))

# Google OAuth 설정
GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID', '')
GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET', '')

# 배포 환경 설정
DEBUG = os.getenv('DEBUG', 'False').lower() == 'true'
HOST = os.getenv('HOST', '0.0.0.0')  # 모든 IP에서 접근 허용 