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

# --- [로직 1] 핀터레스트 검증 ---
def check_pinterest_status(url):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"}
    try:
        response = requests.get(url, headers=headers, timeout=10, allow_redirects=True)
        pin_id = url.strip('/').split('/')[-1]
        if response.status_code == 200 and pin_id in response.url:
            if 'pinterestapp:pin' in response.text or 'og:title' in response.text:
                return "Active"
        return "Dead"
    except:
        return "Error"

# --- [로직 2] 트렌비 검증 (ID 대조 로직 포함) ---
def check_trenbe_status(url, driver):
    try:
        match = re.search(r'\d+', str(url))
        if not match: return "Invalid URL"
        product_id = match.group()
        
        search_url = f"https://www.trenbe.com/search?keyword={product_id}"
        driver.get(search_url)
        time.sleep(4) # 동적 컨텐츠 로드 대기

        page_source = driver.page_source
        no_result_keywords = ['검색 결과가 없습니다', '검색결과가 없습니다', '결과가 없습니다']
        
        # 1차 문구 체크
        if any(keyword in page_source for keyword in no_result_keywords):
            return "Expired"

        # 2차 ID 정밀 대조 (추천 상품 예외 처리)
        items = driver.find_elements(By.CSS_SELECTOR, "a[href*='/product/']")
        is_exact_match = any(product_id in str(item.get_attribute('href')) for item in items)

        return "Active" if is_exact_match else "Expired"
    except:
        return "Error"

# --- [Selenium 설정] Streamlit Cloud 전용 드라이버 초기화 ---
def get_driver():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    
    # 설치된 크롬 실행 파일 경로 명시
    options.binary_location = "/usr/bin/chromium"

    try:
        # webdriver_manager를 사용하지 않고 시스템에 설치된 드라이버 직접 연결
        service = Service("/usr/bin/chromedriver")
        driver = webdriver.Chrome(service=service, options=options)
    except Exception as e:
        # 실패 시 자동 설치 시도
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
    return driver

# --- [UI 구성] ---
st.set_page_config(page_title="URL Checker", layout="wide")
st.title("📌 통합 URL 상태 확인 도구 (Pinterest & Trenbe)")

uploaded_file = st.file_uploader("분석할 CSV 파일을 업로드하세요", type=["csv"])

if uploaded_file is not None:
    try:
        df = pd.read_csv(uploaded_file, encoding='utf-8-sig')
    except:
        df = pd.read_csv(uploaded_file, encoding='cp949')

    if st.button("분석 시작"):
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # 트렌비 대상 유무 확인 후 드라이버 로드
        driver = None
        platforms = df.iloc[:, 13].astype(str).str.lower().values
        if any('trenbe' in p for p in platforms):
            with st.spinner("서버 환경에서 브라우저를 구동 중입니다..."):
                driver = get_driver()
        
        total = len(df)
        for idx in range(total):
            url = df.iloc[idx, 2]       # C열
            platform = str(df.iloc[idx, 13]).lower() # N열
            
            result = "Skipped"
            if 'pinterest' in platform:
                result = check_pinterest_status(url)
            elif 'trenbe' in platform:
                result = check_trenbe_status(url, driver)
            
            # D열(인덱스 3)에 저장
            df.iloc[idx, 3] = result
            
            progress_bar.progress((idx + 1) / total)
            status_text.text(f"[{idx+1}/{total}] {platform} 분석 중... 결과: {result}")

        if driver: driver.quit()
        
        st.success("모든 분석이 완료되었습니다!")
        st.dataframe(df.head(10))
        
        csv_data = df.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')
        st.download_button("결과 파일(.csv) 다운로드", csv_data, "check_result.csv", "text/csv")
