# test_ocr_performance.py
# CLOVA OCR + Gemini 2.0 Flash 표 인식 성능 테스트 스크립트

import requests
import json
import base64
import time
import uuid
import os
import google.generativeai as genai
from config import CLOVA_URL, CLOVA_SECRET, GEMINI_API_KEY

# CLOVA OCR 설정
HEADERS = {"X-OCR-SECRET": CLOVA_SECRET, "Content-Type": "application/json"}

# Gemini 2.0 Flash 설정
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-2.0-flash-exp')

def call_clova_ocr(image_path):
    """이미지 파일을 CLOVA OCR로 분석"""
    try:
        with open(image_path, "rb") as f:
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
        
        print(f"🔄 {image_path} 분석 중...")
        res = requests.post(CLOVA_URL, headers=HEADERS, json=payload, timeout=30)
        res.raise_for_status()
        
        return res.json()
    
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        return None

def analyze_ocr_result(ocr_data, image_name):
    """OCR 결과 분석"""
    print(f"\n📊 {image_name} 분석 결과:")
    print("=" * 50)
    
    if not ocr_data:
        print("❌ OCR 데이터가 없습니다.")
        return
    
    # 기본 정보
    images = ocr_data.get("images", [])
    if not images:
        print("❌ 이미지 데이터가 없습니다.")
        return
    
    image_data = images[0]
    
    # 텍스트 추출 결과
    fields = image_data.get("fields", [])
    print(f"📝 추출된 텍스트 필드 수: {len(fields)}")
    
    # 표 인식 결과
    tables = image_data.get("tables", [])
    print(f"📋 인식된 표 수: {len(tables)}")
    
    if tables:
        for i, table in enumerate(tables):
            print(f"\n📋 표 {i+1}:")
            cells = table.get("cells", [])
            print(f"   - 셀 수: {len(cells)}")
            
            # 표 구조 분석
            if cells:
                max_row = max(c["rowIndex"] for c in cells)
                max_col = max(c["columnIndex"] for c in cells)
                print(f"   - 행 수: {max_row + 1}")
                print(f"   - 열 수: {max_col + 1}")
                
                # 셀 내용 샘플 출력
                print("   - 셀 내용 샘플:")
                for cell in cells[:10]:  # 처음 10개 셀만 출력
                    row = cell["rowIndex"]
                    col = cell["columnIndex"]
                    text = " ".join(
                        w["inferText"] for ln in cell["cellTextLines"] 
                        for w in ln["cellWords"]
                    ).strip()
                    if text:
                        print(f"     [{row},{col}]: {text}")
    
    # 전체 텍스트 샘플
    print(f"\n📝 전체 텍스트 샘플 (처음 10개):")
    for i, field in enumerate(fields[:10]):
        text = field.get("inferText", "")
        if text.strip():
            print(f"   {i+1}. {text}")
    
    print("\n" + "=" * 50)

def test_gemini_analysis(ocr_data, image_name, test_names=["김지성", "홍길동"]):
    """Gemini 2.0 Flash로 일정 분석 테스트"""
    print(f"\n🤖 {image_name} Gemini 분석 테스트:")
    print("=" * 50)
    
    if not ocr_data:
        print("❌ OCR 데이터가 없습니다.")
        return
    
    for test_name in test_names:
        print(f"\n🔍 '{test_name}' 일정 분석 중...")
        
        prompt = f"""
당신은 근무일정표를 분석하는 전문가입니다. 
CLOVA OCR로 추출된 표 데이터를 분석하여 특정 직원의 근무일정을 JSON 형태로 반환해주세요.

**분석 대상 직원**: {test_name}
**기준 연도**: 2025년

**CLOVA OCR 결과**:
{json.dumps(ocr_data, ensure_ascii=False, indent=2)}

**분석 요구사항**:
1. 표(tables) 데이터에서 {test_name}이 근무하는 모든 시간대를 찾으세요
2. 각 근무일정에 대해 다음 정보를 추출하세요:
   - 날짜 (YYYY-MM-DD 형식)
   - 시작 시간 (HH:MM 형식)
   - 종료 시간 (HH:MM 형식)
   - 포지션/역할

3. 종료 시간이 명시되지 않은 경우, 시작 시간 + 1시간으로 추정하세요
4. 날짜에 연도가 없는 경우 2025년을 사용하세요

**반환 형식** (JSON 배열):
[
  {{
    "name": "{test_name}",
    "position": "포지션명",
    "date": "YYYY-MM-DD",
    "start": "HH:MM",
    "end": "HH:MM"
  }}
]

**주의사항**:
- 정확한 JSON 형식으로만 응답하세요
- 설명이나 추가 텍스트는 포함하지 마세요
- 날짜와 시간 형식을 정확히 지켜주세요
- 찾을 수 없는 경우 빈 배열 []을 반환하세요
"""

        try:
            response = model.generate_content(prompt)
            response_text = response.text.strip()
            
            try:
                schedules = json.loads(response_text)
                if isinstance(schedules, list):
                    print(f"✅ '{test_name}' 일정 발견: {len(schedules)}개")
                    for schedule in schedules:
                        print(f"   - {schedule.get('date')} {schedule.get('start')}-{schedule.get('end')} ({schedule.get('position')})")
                else:
                    print(f"⚠️ '{test_name}' 일정 없음")
                    
            except json.JSONDecodeError as e:
                print(f"❌ '{test_name}' JSON 파싱 실패: {e}")
                print(f"응답: {response_text[:200]}...")
                
        except Exception as e:
            print(f"❌ '{test_name}' Gemini API 호출 실패: {e}")
    
    print("\n" + "=" * 50)

def test_image_ocr(image_path, image_name):
    """이미지 OCR 테스트"""
    print(f"\n🔍 {image_name} 테스트 시작")
    print(f"📁 파일 경로: {image_path}")
    
    # 파일 존재 확인
    if not os.path.exists(image_path):
        print(f"❌ 파일이 존재하지 않습니다: {image_path}")
        return
    
    # OCR 실행
    ocr_result = call_clova_ocr(image_path)
    
    # 결과 분석
    analyze_ocr_result(ocr_result, image_name)
    
    # Gemini 분석 테스트
    test_gemini_analysis(ocr_result, image_name)
    
    return ocr_result

def main():
    """메인 테스트 함수"""
    print("🚀 CLOVA OCR + Gemini 2.0 Flash 표 인식 성능 테스트")
    print("=" * 60)
    
    # 테스트할 이미지들
    test_images = [
        ("uploads/6월 3주차(영화관).jpg", "영화관 근무일정표"),
        ("uploads/김지성씨 근무표표.jpg", "투썸플레이스 근무일정표")
    ]
    
    results = {}
    
    for image_path, image_name in test_images:
        result = test_image_ocr(image_path, image_name)
        results[image_name] = result
    
    # 종합 분석
    print("\n🎯 종합 분석 결과")
    print("=" * 60)
    
    for image_name, result in results.items():
        if result and "images" in result:
            images = result["images"]
            if images and "tables" in images[0]:
                tables = images[0]["tables"]
                print(f"✅ {image_name}: {len(tables)}개 표 인식 성공")
            else:
                print(f"⚠️ {image_name}: 표 인식 실패")
        else:
            print(f"❌ {image_name}: OCR 처리 실패")
    
    print("\n💡 테스트 완료!")
    print("📋 CLOVA OCR과 Gemini 2.0 Flash의 성능을 비교 평가하세요.")

if __name__ == "__main__":
    main() 