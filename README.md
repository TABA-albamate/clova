# clova
clova ocr code


auto_server.py 코드의 이 부분은 각자의 clova api로 수정 필요!
# CLOVA OCR 엔드포인트 & 시크릿 (테스트용 하드코딩)
CLOVA_URL = (
    "https://r5hblmakxq.apigw.ntruss.com/custom/v1/"
    "43855/ce0fa66e74d324fba49bbe8f32c5638ad6f218fa5e522a96d3f8a33a863d17a5/general"
)
CLOVA_SECRET = "c0hRUmJQT2NIY1FtcFVYRGZnSnpheVZRYXlLZGRmZ1k="
HEADERS = {"X-OCR-SECRET": CLOVA_SECRET, "Content-Type": "application/json"}
