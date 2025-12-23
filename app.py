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
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# --- [정밀 로직] 트렌비 전용 영역 한정 검증 ---
def check_trenbe_status(url, driver):
    try:
        # 1. URL에서 상품 번호 추출
        match = re.search(r'\d+', str(url))
        if not match: return "Invalid URL"
        product_id = match.group()
        
        # 2. 검색 페이지 접속
        search_url = f"https://www.trenbe.com/search?keyword={product_id}"
        driver.get(search_url)

        # 3. [핵심] 검색 결과 메인 컨테이너가 로딩될 때까지 대기
        # 트렌비의 검색 결과 본문 영역 클래스 타겟팅
        try:
            wait = WebDriverWait(driver, 8)
            # 검색 결과 리스트나 '결과 없음' 알림창이 뜰 때까지 대기
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "main, .search-result-list, .search_no_result")))
        except:
            pass # 타임아웃 시 일단 진행

        # 4. '결과 없음' 문구가 상단에 명시적으로 있는지 우선 확인
        page_text = driver.find_element(By.TAG_NAME, "body").text
        if any(kw in page_text for kw in ["검색 결과가 없습니다", "결과가 없습니다", "검색 결과 0"]):
            return "Expired"

        # 5. [중요] 추천 상품 영역을 배제하고 '검색 결과 섹션' 내의 링크만 추출
        # 트렌비는 보통 main 태그 내부에 검색 결과가 위치함
        main_content = driver.find_element(By.TAG_NAME, "main")
        items = main_content.find_elements(By.CSS_SELECTOR, "a[href*='/product/']")
        
        # 6. 추출된 링크들 중 나의 product_id와 완벽하게 일치하는 것이 있는지 검사
        found_real_product = False
        for item in items:
            href = item.get_attribute('href') or ""
            # 링크 경로의 마지막 숫자가 나의 product_id와 같은지 대조
            # 예: /product/12345?source=search -> 12345 추출
            link_id_match = re.search(r'product/(\d+)', href)
            if link_id_match and link_id_match.group(1) == product_id:
                found_real_product = True
                break
        
        return "Active" if found_real_product else "Expired"
        
    except Exception:
        return "Error"

# --- [Selenium 설정] Streamlit Cloud용 ---
def get_driver():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("window-size=1920x1080")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    # 이미지 로딩 차단 (속도 및 정확도 향상)
    prefs = {"profile.managed_default_content_settings.images": 2}
    options.add_experimental_option("prefs", prefs)
    
    # 서버 경로 설정 (자동 감지)
    import os
    if os.path.exists("/usr/bin/chromium"):
        options.binary_location = "/usr/bin/chromium"
        service = Service("/usr/bin/chromedriver")
    else:
        service = Service(ChromeDriverManager().install())
        
    return webdriver.Chrome(service=service, options=options)

# --- [UI 구성] ---
st.set_page_config(page_title="Trenbe Precision Checker", layout="wide")
st.title("🎯 트렌비 상품 상태 정밀 확인")
st.info("검색 결과 영역만 한정하여 분석하므로 추천 상품에 낚이지 않습니다.")

uploaded_file = st.file_uploader("CSV 파일 업로드 (C열: URL / N열: 플랫폼)", type=["csv"])

if uploaded_file is not None:
    try:
        df = pd.read_csv(uploaded_file, encoding='utf-8-sig')
    except:
        df = pd.read_csv(uploaded_file, encoding='cp949')

    if st.button("정밀 분석 시작"):
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        driver = get_driver()
        total = len(df)
        
        for idx in range(total):
            url = str(df.iloc[idx, 2])
            platform = str(df.iloc[idx, 13]).lower()
            
            result = "Skipped"
            if 'trenbe' in platform:
                result = check_trenbe_status(url, driver)
                df.iloc[idx, 3] = result # D열 기록
            
            progress_bar.progress((idx + 1) / total)
            status_text.text(f"[{idx+1}/{total}] {platform} 판독 중... 결과: {result}")

        driver.quit()
        st.success("분석 완료!")
        st.dataframe(df.head(20))
        
        csv_data = df.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')
        st.download_button("📥 결과 다운로드", csv_data, "trenbe_final_result.csv", "text/csv")
