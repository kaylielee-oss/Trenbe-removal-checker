import streamlit as st
import pandas as pd
import re
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

# --- 1. 셀레니움 드라이버 설정 ---
def get_driver():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")
    
    try:
        service = Service("/usr/bin/chromedriver")
        return webdriver.Chrome(service=service, options=options)
    except:
        return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

# --- 2. 검색 결과 기반 상태 판별 함수 ---
def check_by_search(driver, url):
    try:
        # 1. URL에서 상품 코드 추출 (예: 68257506)
        product_code_match = re.search(r'(\d+)', url)
        if not product_code_match:
            return "URL 오류"
        target_code = product_code_match.group(1)

        # 2. 검색 결과 페이지로 바로 접속
        search_url = f"https://www.trenbe.com/search/?keyword={target_code}"
        driver.get(search_url)
        time.sleep(2.5) # 검색 결과 로딩 대기

        page_source = driver.page_source

        # [판별 로직 1] "해당 상품이 없습니다" 문구가 뜨거나 검색 결과가 없는 경우 -> Expired
        if "해당 상품이 없습니다" in page_source:
            return "Expired"

        # [판별 로직 2] 검색 결과 상품 리스트 확인
        # 트렌비 검색 결과의 상품 카드는 보통 a 태그의 href에 상품 번호를 포함함
        product_elements = driver.find_elements(By.CSS_SELECTOR, "a[href*='/product/']")
        
        if not product_elements:
            return "Expired"

        # [판별 로직 3] 검색 결과에 나타난 상품들 중 타겟 상품 번호가 포함되어 있는지 확인
        for elem in product_elements:
            href = elem.get_attribute("href")
            if target_code in href:
                # 검색된 상품들 중 입력한 번호와 일치하는 상품이 있으면 Active
                return "Active"

        # 검색 결과는 있으나 번호가 일치하는 상품이 없는 경우
        return "Expired"

    except Exception as e:
        return f"오류: {str(e)}"

# --- 3. 스트림릿 UI ---
st.title("🛍️ 트렌비 검색 기반 상태 검사기")
st.info("이미지 1(결과 없음)과 3(결과 있음)의 로직을 우선하여 판별합니다.")

uploaded_file = st.file_uploader("C열에 URL이 포함된 CSV 파일을 업로드하세요", type=['csv'])

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)
    
    if st.button("검사 시작"):
        driver = get_driver()
        results = []
        
        progress_bar = st.progress(0)
        status_text = st.empty()

        # C열(Index 2) URL 데이터 순회
        for i, url in enumerate(df.iloc[:, 2]):
            status_text.text(f"검사 중... ({i+1}/{len(df)}): {url}")
            # 검색 기반 판별 함수 실행
            res = check_by_search(driver, url)
            results.append(res)
            progress_bar.progress((i + 1) / len(df))
        
        driver.quit()

        # 결과를 D열(Index 3)에 저장
        if len(df.columns) >= 4:
            df.iloc[:, 3] = results
        else:
            # D열 자리에 'Status' 열 삽입
            df.insert(3, 'Status', results)

        st.success("검사가 완료되었습니다!")
        st.dataframe(df.head(10))

        # 다운로드 버튼 (D열이 포함된 최종 결과물)
        csv_data = df.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')
        st.download_button("결과 CSV 다운로드", csv_data, "trenbe_search_result.csv", "text/csv")
