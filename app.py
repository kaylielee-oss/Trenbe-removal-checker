# Trenbe 폴더 안에 실제 파일명이랑 똑같이 적어주세요
EXPIRED_IMAGES = [
    'no_product_icon.png',    # 트렌비 검색없음 아이콘
    '11st_no_product.png',   # 11번가 검색없음 아이콘
    'stop_popup_trenbe.png', # 트렌비 판매중지 문구 캡처
    'stop_popup_11st.png'    # 11번가 판매중지 문구 캡처
]

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
st.write("이미지 조각 매칭 + 가격 데이터 검증으로 오판율을 최소화합니다.")

current_dir = os.path.dirname(os.path.abspath(__file__))

# 검사할 이미지 조각들 (Trenbe 폴더 안에 해당 파일들이 있어야 함)
EXPIRED_IMAGES = ['no_product_icon.png', '11st_no_product.png', 'stop_popup.png']

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
    if not url: return "-"
    driver = get_driver()
    
    try:
        # --- 1단계: 상세 페이지 직접 접속 및 '가격' 확인 ---
        driver.get(url)
        time.sleep(5) # 충분한 로딩 대기
        
        # 트렌비 전용 가격 태그 확인 (가격이 있으면 일단 Active 가능성 높음)
        if 'trenbe.com' in url:
            prices = driver.find_elements(By.CLASS_NAME, "PriceWithTag__Price")
            if len(prices) > 0 and prices[0].text.strip() != "":
                # 가격이 존재하면 일단 Active로 간주하되, 팝업이 있는지 한번 더 체크
                page_text = driver.find_element(By.TAG_NAME, "body").text
                if "판매 중지" in page_text or "삭제된 상품" in page_text:
                    return "Expired"
                return "Active"

        # --- 2단계: 이미지 조각 매칭 (검색 결과 페이지 등) ---
        # 11번가나 트렌비 검색 결과 확인이 필요한 경우
        product_id_match = re.search(r'\d+', str(url))
        if product_id_match:
            product_id = product_id_match.group()
            search_url = f"https://www.trenbe.com/search?keyword={product_id}" if 'trenbe' in url else f"https://www.11st.co.kr/search?kwd={product_id}"
            driver.get(search_url)
            time.sleep(4)

            nparr = np.frombuffer(driver.get_screenshot_as_png(), np.uint8)
            screen = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

            for img_name in EXPIRED_IMAGES:
                img_path = os.path.join(current_dir, img_name)
                if os.path.exists(img_path):
                    template = cv2.imread(img_path, cv2.IMREAD_COLOR)
                    res = cv2.matchTemplate(screen, template, cv2.TM_CCOEFF_NORMED)
                    if len(np.where(res >= 0.8)[0]) > 0: # 일치율 80%
                        return "Expired"
        
        return "Active"
    except:
        return "Error"

# (이하 실행 및 엑셀 업로드 로직은 이전과 동일)
uploaded_file = st.file_uploader("list.csv 또는 list.xlsx 업로드", type=["csv", "xlsx"])
if uploaded_file and st.button("정밀 분석 시작"):
    # ... (데이터 처리 및 결과 다운로드 버튼 코드)
