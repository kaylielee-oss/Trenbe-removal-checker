import streamlit as st
import pandas as pd
import re
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
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

# --- 2. 검색 결과 기반 상태 판별 함수 (강화 버전) ---
def check_trenbe_status(driver, url):
    try:
        # URL에서 상품 코드 추출
        product_code_match = re.search(r'(\d+)', url)
        if not product_code_match:
            return "URL 오류"
        target_code = product_code_match.group(1)

        # 검색 페이지 접속
        search_url = f"https://www.trenbe.com/search/?keyword={target_code}"
        driver.get(search_url)
        
        # 최대 8초 대기: 상품 링크가 나타나거나 '결과 없음' 문구가 나타날 때까지
        wait = WebDriverWait(driver, 8)
        
        try:
            # 검색 결과 내 상품 링크(a 태그)가 나타날 때까지 대기
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "a[href*='/product/']")))
            
            # 현재 페이지의 모든 상품 링크 추출
            product_links = driver.find_elements(By.CSS_SELECTOR, "a[href*='/product/']")
            
            for link in product_links:
                href = link.get_attribute("href")
                if target_code in href:
                    return "Active"  # 일치하는 상품 번호를 찾으면 즉시 Active 반환
            
            return "Expired" # 결과는 떴으나 해당 번호가 없음
            
        except:
            # 대기 시간 초과 시: '해당 상품이 없습니다' 문구가 있는지 최종 확인
            page_source = driver.page_source
            if "해당 상품이 없습니다" in page_source:
                return "Expired"
            
            # 예외 케이스: 로딩이 느리지만 소스 코드에 번호가 포함되어 있는 경우
            if target_code in page_source and "/product/" in page_source:
                return "Active"
                
            return "Expired"

    except Exception as e:
        return f"오류: {str(e)}"

# --- 3. 스트림릿 UI ---
st.set_page_config(page_title="트렌비 상태 체크", layout="wide")
st.title("🛍️ 트렌비 상품 상태 검사기 (D열 자동 입력)")
st.markdown("""
- **C열**: 상품 URL (숫자 포함 필수)
- **D열**: 판별 결과 (Active / Expired) 가 입력됩니다.
""")

uploaded_file = st.file_uploader("검사할 CSV 파일을 업로드하세요", type=['csv'])

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)
    st.write("### 업로드 데이터 미리보기")
    st.dataframe(df.head())

    if st.button("🔍 검사 시작 (C열 기준)"):
        driver = get_driver()
        results = []
        
        progress_bar = st.progress(0)
        status_text = st.empty()

        # C열(Index 2) URL 데이터를 순회
        for i, url in enumerate(df.iloc[:, 2]):
            status_text.text(f"처리 중... ({i+1}/{len(df)}): {url}")
            
            # 상태 체크 실행
            status = check_trenbe_status(driver, str(url))
            results.append(status)
            
            # 진행률 업데이트
            progress_bar.progress((i + 1) / len(df))
        
        driver.quit()

        # 결과를 D열(Index 3)에 반영
        if len(df.columns) >= 4:
            df.iloc[:, 3] = results
        else:
            df.insert(3, 'Status', results)

        st.success("✅ 모든 검사가 완료되었습니다!")
        st.write("### 검사 결과 (상위 10개)")
        st.dataframe(df.head(10))

        # 다운로드 버튼 생성 (BOM 설정으로 한글 깨짐 방지)
        csv_data = df.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')
        st.download_button(
            label="📩 결과 CSV 다운로드",
            data=csv_data,
            file_name="trenbe_results_final.csv",
            mime="text/csv"
        )
