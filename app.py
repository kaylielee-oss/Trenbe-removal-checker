import streamlit as st
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
import time
import re
import cv2
import numpy as np
import os
import io

# 앱 설정
st.set_page_config(page_title="트렌비/11번가 정밀 판별기", page_icon="🔍")
st.title("🛍️ 통합 상품 상태 판별기")

current_dir = os.path.dirname(os.path.abspath(__file__))

# 1. 이미지 파일명 리스트 확인 (폴더 내 파일명과 정확히 일치해야 함)
EXPIRED_IMAGES = ['no_product_icon.png', '11st_no_product.png']

@st.cache_resource
def get_driver():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("window-size=1920,1080")
    options.add_argument("user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

def check_status_final(url):
    if not url or not isinstance(url, str): return "-"
    driver = get_driver()
    
    try:
        # --- 1단계: 상세 페이지 접속 검사 (팝업 문구 체크) ---
        driver.get(url)
        time.sleep(4) 
        
        # 페이지 전체 텍스트에서 '판매중지' 관련 키워드 검색
        page_text = driver.find_element(By.TAG_NAME, "body").text
        stop_keywords = ["판매 중지", "삭제된 상품", "판매 종료", "존재하지 않는", "현재 판매하지 않는"]
        if any(word in page_text for word in stop_keywords):
            return "Expired"

        # --- 2단계: 사이트별 검색 결과 이미지 매칭 ---
        search_url = ""
        # 11번가: products/ 뒤의 숫자 추출
        if '11st.co.kr' in url:
            match = re.search(r'products/(\d+)', url)
            if match:
                search_url = f"https://www.11st.co.kr/search?kwd={match.group(1)}"
        # 트렌비: URL 내의 모든 숫자 조합 중 가장 긴 것 추출
        elif 'trenbe.com' in url:
            nums = re.findall(r'\d+', url)
            if nums:
                product_id = max(nums, key=len)
                search_url = f"https://www.trenbe.com/search?keyword={product_id}"

        if search_url:
            driver.get(search_url)
            time.sleep(4)
            
            # 스크린샷 캡처
            nparr = np.frombuffer(driver.get_screenshot_as_png(), np.uint8)
            screen = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

            for img_name in EXPIRED_IMAGES:
                img_path = os.path.join(current_dir, img_name)
                if os.path.exists(img_path):
                    template = cv2.imread(img_path, cv2.IMREAD_COLOR)
                    if template is None: continue
                    
                    res = cv2.matchTemplate(screen, template, cv2.TM_CCOEFF_NORMED)
                    # 일치율을 0.8로 설정 (너무 안 잡히면 0.7로 낮추세요)
                    if len(np.where(res >= 0.8)[0]) > 0:
                        return "Expired"
        
        return "Active"
    except Exception as e:
        return f"Error"

# --- 엑셀 처리 로직 ---
uploaded_file = st.file_uploader("검사할 파일을 올려주세요", type=["csv", "xlsx"])

if uploaded_file and st.button("정밀 분석 시작"):
    if uploaded_file.name.endswith('.csv'):
        try: df = pd.read_csv(uploaded_file, encoding='utf-8-sig')
        except: df = pd.read_csv(uploaded_file, encoding='cp949')
    else:
        df = pd.read_excel(uploaded_file)

    progress_bar = st.progress(0)
    results = []
    
    for i, row in df.iterrows():
        url = row.iloc[2] # C열
        status = check_status_final(url)
        results.append(status)
        progress_bar.progress((i + 1) / len(df))
    
    df.iloc[:, 3] = results # D열에 저장
    st.success("🎉 검사 완료!")
    
    # 다운로드 버튼
    csv = df.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')
    st.download_button("📥 결과 다운로드", csv, "result.csv", "text/csv")
