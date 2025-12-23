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
    options.add_argument("--headless")  # 서버 환경 필수
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    # 트렌비의 봇 탐지를 우회하기 위한 User-Agent 설정
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

# --- 2. 상태 판별 함수 ---
def check_trenbe_status(driver, url):
    try:
        # URL에서 상품 코드 추출
        product_code_match = re.search(r'(\d+)', url)
        if not product_code_match:
            return "Invalid URL"
        product_code = product_code_match.group(1)

        # [단계 1] 상품 상세 페이지 접속 확인
        driver.get(url)
        time.sleep(2)  # 로딩 대기

        # 페이지 소스에 '품절'이 있거나 버튼이 비활성화인지 확인
        buttons = driver.find_elements(By.TAG_NAME, "button")
        is_sold_out = False
        has_buy_button = False

        for btn in buttons:
            if "바로 구매하기" in btn.text:
                has_buy_button = True
                # 버튼 속성에 disabled가 있거나 텍스트에 품절이 포함된 경우
                if btn.get_attribute("disabled") or "품절" in btn.text:
                    is_sold_out = True
            elif "품절" in btn.text:
                is_sold_out = True

        if has_buy_button and not is_sold_out:
            return "Active"

        # [단계 2] 상세 페이지에서 판별이 모호할 경우 검색 결과 확인
        search_url = f"https://www.trenbe.com/search/?keyword={product_code}"
        driver.get(search_url)
        time.sleep(2)

        page_text = driver.page_source
        if "해당 상품이 없습니다" in page_text:
            return "Expired"
        
        # 검색 결과 리스트 확인 (상품 아이템 클래스 추출 시도)
        items = driver.find_elements(By.CSS_SELECTOR, "div[class*='ProductItem']")
        if len(items) > 0:
            return "Active"

        return "Expired"

    except Exception as e:
        return f"Error: {str(e)}"

# --- 3. 스트림릿 UI ---
st.title("🛍️ 트렌비 상품 상태 체크 도구")
st.write("C열에 URL이 있는 CSV 파일을 업로드하면 D열에 상태를 추가해 드립니다.")

uploaded_file = st.file_uploader("CSV 파일을 업로드하세요", type=['csv'])

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)
    st.write("파일 일부 미리보기:", df.head())

    if st.button("검사 시작"):
        driver = get_driver()
        results = []
        
        progress_bar = st.progress(0)
        status_text = st.empty()

        for i, url in enumerate(df.iloc[:, 2]):  # C열 (인덱스 2)
            status_text.text(f"검사 중 ({i+1}/{len(df)}): {url}")
            status = check_trenbe_status(driver, url)
            results.append(status)
            progress_bar.progress((i + 1) / len(df))

        driver.quit()

        # D열(인덱스 3)에 결과 추가
        df['Status (Active/Expired)'] = results
        
        st.success("검사 완료!")
        st.write(df.head())

        # 다운로드 버튼
        csv = df.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')
        st.download_button("결과 파일 다운로드", csv, "trenbe_results.csv", "text/csv")
