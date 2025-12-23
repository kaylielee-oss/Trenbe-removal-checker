import streamlit as st
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import time
import re
import cv2
import numpy as np
import os
import io

# 앱 설정
st.set_page_config(page_title="트렌비 정밀 판별기", page_icon="🛍️")
st.title("🛍️ 트렌비 상태 판별기 (정밀 모드)")

current_dir = os.path.dirname(os.path.abspath(__file__))
icon_path = os.path.join(current_dir, 'no_product_icon.png')

uploaded_file = st.file_uploader("list.csv 또는 list.xlsx 업로드", type=["csv", "xlsx"])

@st.cache_resource
def get_driver():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("window-size=1920,1080")
    options.add_argument("user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

def check_status_precise(url, template_img):
    if not url or 'trenbe.com' not in str(url):
        return "-"
    try:
        driver = get_driver()
        product_id = re.search(r'\d+', str(url)).group()
        search_url = f"https://www.trenbe.com/search?keyword={product_id}"
        driver.get(search_url)
        
        # 1. 충분한 대기 시간 (로딩이 느릴 경우 대비)
        time.sleep(6) 

        # 2. 텍스트 기반 1차 검사 (이미지 인식 보완)
        page_source = driver.page_source
        if "검색 결과가 없습니다" in page_source or "해당 상품이 없습니다" in page_source:
            return "Expired"

        # 3. 이미지 기반 2차 검사 (보라색 상자 아이콘 찾기)
        nparr = np.frombuffer(driver.get_screenshot_as_png(), np.uint8)
        screen = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        res = cv2.matchTemplate(screen, template_img, cv2.TM_CCOEFF_NORMED)
        
        # 일치율을 0.7로 살짝 낮춰서 더 잘 잡히게 설정
        threshold = 0.7 
        if len(np.where(res >= threshold)[0]) > 0:
            return "Expired"
            
        return "Active"
    except:
        return "Error"

# 실행부 (기존과 동일하되 함수명만 교체)
if uploaded_file:
    if not os.path.exists(icon_path):
        st.error("아이콘 파일(no_product_icon.png)이 없습니다.")
    else:
        template_img = cv2.imread(icon_path, cv2.IMREAD_COLOR)
        if st.button("정밀 검사 시작"):
            # 파일 읽기 로직... (이전 코드와 동일)
            if uploaded_file.name.endswith('.csv'):
                df = pd.read_csv(uploaded_file, encoding='utf-8-sig')
            else:
                df = pd.read_excel(uploaded_file)
            
            results = []
            progress_bar = st.progress(0)
            for i, row in df.iterrows():
                status = check_status_precise(row.iloc[2], template_img)
                results.append(status)
                progress_bar.progress((i + 1) / len(df))
            
            df.iloc[:, 3] = results
            st.success("검사 완료!")
            st.download_button("결과 다운로드", df.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig'), "result.csv")
