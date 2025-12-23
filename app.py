import streamlit as st
import pandas as pd
import time
import random
import re
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# --- [정밀 로직] 타임아웃 방어 및 재시도 ---
def check_trenbe_with_retry(url, driver, idx):
    try:
        match = re.search(r'\d+', str(url))
        if not match: return "Invalid URL"
        product_id = match.group()
        
        # 사람처럼 랜덤하게 쉬기 (요청 간격 불규칙화)
        time.sleep(random.uniform(3.0, 5.0))
        
        search_url = f"https://www.trenbe.com/search?keyword={product_id}"
        driver.get(search_url)
        
        # [핵심] 타임아웃 발생 시 'Expired' 대신 에러를 던져 브라우저 재시작 유도
        wait = WebDriverWait(driver, 15) # 대기 시간을 15초로 늘림
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "main")))
        
        # 1. '결과 없음' 문구 우선 확인
        page_text = driver.find_element(By.TAG_NAME, "body").text
        if any(kw in page_text for kw in ["검색 결과가 없습니다", "결과가 없습니다", "검색 결과 0"]):
            return "Expired"

        # 2. 메인 컨테이너 내 상품 ID 정밀 대조
        main_content = driver.find_element(By.TAG_NAME, "main")
        items = main_content.find_elements(By.CSS_SELECTOR, "a[href*='/product/']")
        
        found = any(f"/product/{product_id}" in (item.get_attribute('href') or "") for item in items)
        
        return "Active" if found else "Expired"
        
    except Exception as e:
        # 타임아웃 등 에러 발생 시 로그 반환
        return f"Error: {type(e).__name__}"

# --- [Selenium 설정] ---
def get_driver():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("window-size=1920x1080")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    # 이미지 차단 (네트워크 부하 감소)
    prefs = {"profile.managed_default_content_settings.images": 2}
    options.add_experimental_option("prefs", prefs)
    
    import os
    if os.path.exists("/usr/bin/chromium"):
        options.binary_location = "/usr/bin/chromium"
        service = Service("/usr/bin/chromedriver")
    else:
        service = Service(ChromeDriverManager().install())
        
    return webdriver.Chrome(service=service, options=options)

# --- [UI 및 실행 루프] ---
st.set_page_config(page_title="Trenbe Anti-Timeout Checker", layout="wide")
st.title("🚶‍♂️ 트렌비 정밀 판독 (타임아웃 방어 모드)")

uploaded_file = st.file_uploader("CSV 파일 업로드", type=["csv"])

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file, encoding='utf-8-sig')
    
    if st.button("분석 시작"):
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        driver = get_driver()
        total = len(df)
        
        for idx in range(total):
            url = str(df.iloc[idx, 2])
            platform = str(df.iloc[idx, 13]).lower()
            
            if 'trenbe' in platform:
                result = check_trenbe_with_retry(url, driver, idx)
                
                # [복구 로직] TimeoutException이 발생하면 브라우저를 껐다 켜서 세션 초기화
                if "TimeoutException" in result or "WebDriverException" in result:
                    status_text.text(f"⚠️ {idx+1}번에서 타임아웃 발생! 브라우저 재시작 중...")
                    driver.quit()
                    time.sleep(5)
                    driver = get_driver()
                    # 재시작 후 해당 행 다시 시도
                    result = check_trenbe_with_retry(url, driver, idx)

                df.iloc[idx, 3] = result
            
            progress_bar.progress((idx + 1) / total)
            status_text.text(f" 진행 중: {idx+1}/{total} | 결과: {result}")

        if driver: driver.quit()
        st.success("✅ 분석 완료!")
        st.download_button("📥 결과 다운로드", df.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig'), "final_result.csv", "text/csv")
