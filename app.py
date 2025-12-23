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
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# --- [정밀 로직] 사람처럼 검색하기 ---
def check_trenbe_human_style(url, driver, idx):
    try:
        # 1. 상품번호 추출
        match = re.search(r'\d+', str(url))
        if not match: return "Invalid URL"
        product_id = match.group()
        
        # 2. 랜덤 대기 (사람처럼 행동하기)
        # 너무 일정한 간격은 봇으로 의심받기 쉬움
        time.sleep(random.uniform(2.5, 4.5))
        
        # 3. 검색창으로 직접 이동 (referer를 검색 페이지로 설정하여 자연스럽게)
        search_url = f"https://www.trenbe.com/search?keyword={product_id}"
        driver.get(search_url)
        
        # 4. 페이지 하단으로 살짝 스크롤 (사람이 보는 것처럼)
        if idx % 3 == 0: # 3번에 한 번씩 실행
            driver.execute_script("window.scrollTo(0, 300);")
            time.sleep(1)

        # 5. 결과 판독 (이전 정밀 로직 적용)
        wait = WebDriverWait(driver, 10)
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "main")))
        
        page_text = driver.find_element(By.TAG_NAME, "body").text
        if any(kw in page_text for kw in ["검색 결과가 없습니다", "결과가 없습니다", "검색 결과 0"]):
            return "Expired"

        main_content = driver.find_element(By.TAG_NAME, "main")
        items = main_content.find_elements(By.CSS_SELECTOR, "a[href*='/product/']")
        
        found = False
        for item in items:
            href = item.get_attribute('href') or ""
            if f"/product/{product_id}" in href:
                found = True
                break
        
        return "Active" if found else "Expired"
        
    except Exception as e:
        return f"Error: {type(e).__name__}"

# --- [Selenium 설정: 봇 감지 우회 추가] ---
def get_driver():
    options = Options()
    options.add_argument("--headless") # 실제 환경에서는 headless 유지
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("window-size=1920x1080")
    
    # [중요] 봇 감지 우회를 위한 설정
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

    import os
    if os.path.exists("/usr/bin/chromium"):
        options.binary_location = "/usr/bin/chromium"
        service = Service("/usr/bin/chromedriver")
    else:
        service = Service(ChromeDriverManager().install())
        
    driver = webdriver.Chrome(service=service, options=options)
    
    # 봇 감지 우회 스크립트 실행
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    return driver

# --- [UI 및 실행 루프] ---
st.set_page_config(page_title="Human-Like Trenbe Checker", layout="wide")
st.title("🚶‍♂️ 트렌비 상태 확인 (사람 행동 모방 모드)")

uploaded_file = st.file_uploader("CSV 파일 업로드", type=["csv"])

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file, encoding='utf-8-sig')
    
    if st.button("사람 모드로 분석 시작"):
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        driver = get_driver()
        total = len(df)
        
        for idx in range(total):
            # [메모리 관리] 25개 상품마다 브라우저를 재시작하여 에러 방지
            if idx > 0 and idx % 25 == 0:
                status_text.text(f"♻️ 브라우저가 지쳤습니다. 재시작 중... (현재 {idx}번)")
                driver.quit()
                time.sleep(5)
                driver = get_driver()

            url = str(df.iloc[idx, 2])
            platform = str(df.iloc[idx, 13]).lower()
            
            if 'trenbe' in platform:
                result = check_trenbe_human_style(url, driver, idx)
                df.iloc[idx, 3] = result
            
            progress_bar.progress((idx + 1) / total)
            status_text.text(f" 진행 중: {idx+1}/{total} | 현재 결과: {result}")

        driver.quit()
        st.success("✅ 모든 분석이 완료되었습니다!")
        st.dataframe(df.head(20))
        
        csv_data = df.to_csv(index=False, encoding='utf-8-sig').encode('utf-8-sig')
        st.download_button("📥 최종 결과 다운로드", csv_data, "trenbe_human_result.csv", "text/csv")
