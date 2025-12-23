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
    try:
        df = pd.read_csv(uploaded_file, encoding='utf-8-sig')
    except:
        df = pd.read_csv(uploaded_file, encoding='cp949')

    if st.button("분석 시작"):
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # 트렌비 대상이 있을 경우에만 드라이버 초기화
        driver = None
        platforms = df.iloc[:, 13].astype(str).str.lower().values
        if any('trenbe' in p for p in platforms):
            with st.spinner("브라우저를 초기화 중입니다..."):
                driver = get_driver()
        
        total = len(df)
        for idx in range(total):
            url = df.iloc[idx, 2]       # C열
            platform = str(df.iloc[idx, 13]).lower() # N열
            
            result = "Skipped"
            if 'pinterest' in platform:
                result = check_pinterest_status(url)
            elif 'trenbe' in platform:
                result = check_trenbe_status(url, driver)
            
            # D열(인덱스 3)에 결과 기록
            df.iloc[idx, 3] = result
            
            # 진행 상태 업데이트
            progress = (idx + 1) / total
            progress_bar.progress(progress)
            status_text.text(f"진행 중: {idx+1}/{total} (플랫폼: {platform} | 결과: {result})")

        if driver: driver.quit()
        
        st.success("분석 완료!")
        st.write("### 결과 미리보기 (상위 10개)")
        st.dataframe(df.head(10))
        
        # 다운로드 버튼
        csv_data = df.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')
        st.download_button(
            label="결과 파일(.csv) 다운로드",
            data=csv_data,
            file_name="url_check_result.csv",
            mime="text/csv"
        )
