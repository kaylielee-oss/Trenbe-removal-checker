import streamlit as st
import pandas as pd
import requests
import time
import re
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By

# --- [로직 1] 핀터레스트 검증 (Requests 방식) ---
def check_pinterest_status(url):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"}
    try:
        response = requests.get(url, headers=headers, timeout=10, allow_redirects=True)
        # URL의 마지막 숫자(Pin ID) 추출
        pin_id = url.strip('/').split('/')[-1]
        
        # 상태코드 200이며, 최종 URL에 원래의 Pin ID가 포함되어 있어야 함
        if response.status_code == 200 and pin_id in response.url:
            if 'pinterestapp:pin' in response.text or 'og:title' in response.text:
                return "Active"
        return "Dead"
    except:
        return "Error"

# --- [로직 2] 트렌비 검증 (Selenium + ID 정밀 대조 방식) ---
def check_trenbe_status(url, driver):
    try:
        # 1. URL에서 상품 ID 추출
        match = re.search(r'\d+', str(url))
        if not match: return "Invalid URL"
        product_id = match.group()
        
        # 2. 검색 페이지 접속
        search_url = f"https://www.trenbe.com/search?keyword={product_id}"
        driver.get(search_url)
        time.sleep(4) # 동적 컨텐츠 로딩 대기

        # 3. '검색 결과 없음' 문구 체크
        page_source = driver.page_source
        no_result_keywords = ['검색 결과가 없습니다', '검색결과가 없습니다', '결과가 없습니다']
        if any(keyword in page_source for keyword in no_result_keywords):
            return "Expired"

        # 4. 정밀 검증: 검색된 상품 리스트 중 내 상품 ID가 포함된 링크가 있는지 확인
        # 트렌비가 결과가 없을 때 '추천 상품'을 띄우는 경우를 대비함
        items = driver.find_elements(By.CSS_SELECTOR, "a[href*='/product/']")
        is_exact_match = any(product_id in item.get_attribute('href') for item in items)

        if is_exact_match:
            return "Active"
        else:
            return "Expired" # 추천 상품만 뜨고 내 상품은 없는 경우
    except:
        return "Error"

# --- [Selenium 설정] Streamlit Cloud 환경용 ---
def get_driver():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    # 로그를 줄여서 깔끔하게 표시
    options.add_experimental_option("excludeSwitches", ["enable-logging"])
    return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

# --- [UI 구성] ---
st.set_page_config(page_title="URL Multi-Checker", layout="wide")
st.title("📌 통합 URL 상태 확인 도구")
st.info("C열(URL)을 읽어 분석한 뒤, 결과를 D열에 기록합니다. (대상: Pinterest, Trenbe)")

uploaded_file = st.file_uploader("분석할 CSV 파일을 업로드하세요", type=["csv"])

if uploaded_file is not None:
    try
