import streamlit as st
import pandas as pd
import requests
import time
import re
import os
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By

# --- [디버깅 도구: 스크린샷 저장] ---
def save_error_screenshot(driver, name):
    if driver:
        if not os.path.exists("debug_pics"):
            os.makedirs("debug_pics")
        driver.save_screenshot(f"debug_pics/{name}.png")

# --- [로직 2] 트렌비 검증 (디버깅 강화 버전) ---
def check_trenbe_status(url, driver, idx):
    try:
        match = re.search(r'\d+', str(url))
        if not match: return "Invalid URL"
        product_id = match.group()
        
        search_url = f"https://www.trenbe.com/search?keyword={product_id}"
        st.write(f"🔍 {idx+1}번 상품({product_id}) 검색 시도 중...")
        
        driver.get(search_url)
        time.sleep(5) # 충분히 대기

        page_source = driver.page_source
        
        # '검색 결과 없음' 문구 체크
        no_result_keywords = ['검색 결과가 없습니다', '검색결과가 없습니다', '결과가 없습니다']
        if any(keyword in page_source for keyword in no_result_keywords):
            return "Expired"

        items = driver.find_elements(By.CSS_SELECTOR, "a[href*='/product/']")
        is_exact_match = any(product_id in (item.get_attribute('href') or "") for item in items)

        if is_exact_match:
            return "Active"
        else:
            # 예상과 다를 때 스크린샷 저장
            save_error_screenshot(driver, f"check_{idx}_{product_id}")
            return "Expired"
    except Exception as e:
        st.error(f"❌ {idx+1}번에서 에러 발생: {str(e)}")
        save_error_screenshot(driver, f"error_{idx}")
        return "Error"

# --- [Selenium 설정] ---
def get_driver():
    options = Options()
    options.add_argument("--headless") # 서버용
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("window-size=1920x1080")
    options.add_experimental_option("excludeSwitches", ["enable-logging"])
    
    # 서버/로컬 겸용 경로 설정
    if os.path.exists("/usr/bin/chromium"):
        options.binary_location = "/usr/bin/chromium"
        service = Service("/usr/bin/chromedriver")
    else:
        service = Service(ChromeDriverManager().install())
        
    return webdriver.Chrome(service=service, options=options)

# --- [UI 구성] ---
st.set_page_config(page_title="Debug Mode Checker", layout="wide")
st.title("📌 트렌비 상태 확인 (디버깅 모드)")
st.info("진행 과정이 아래에 텍스트로 자세히 표시됩니다.")

uploaded_file = st.file_uploader("CSV 파일 업로드", type=["csv"])

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file, encoding='utf-8-sig') if 'utf' in str(uploaded_file) else pd.read_csv(uploaded_file, encoding='cp949')

    if st.button("디버깅 분석 시작"):
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        driver = None
        try:
            st.write("🛠 브라우저를 켜고 있습니다...")
            driver = get_driver()
            st.write("✅ 브라우저 준비 완료!")
            
            total = len(df)
            for idx in range(total):
                url = str(df.iloc[idx, 2])
                platform = str(df.iloc[idx, 13]).lower()
                
                if 'trenbe' in platform:
                    result = check_trenbe_status(url, driver, idx)
                    df.iloc[idx, 3] = result
                
                progress = (idx + 1) / total
                progress_bar.progress(progress)
                status_text.text(f"현재 위치: {idx+1}/{total} | 결과: {result}")
                
        except Exception as top_e:
            st.error(f"🚨 치명적 오류 발생: {top_e}")
        finally:
            if driver:
                driver.quit()
                st.write("🚪 브라우저를 닫았습니다.")
        
        st.success("분석 종료!")
        st.dataframe(df.head(20))

        # 결과 저장
        csv_data = df.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')
        st.download_button("📥 최종 결과(.csv) 다운로드", csv_data, "debug_result.csv", "text/csv")
