import streamlit as st
import pandas as pd
import requests
import time
import re
import io
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

# --- [로직 2] 트렌비 검증 ---
def check_trenbe_status(url, driver):
    try:
        match = re.search(r'\d+', str(url))
        if not match: return "Invalid URL"
        product_id = match.group()
        
        search_url = f"https://www.trenbe.com/search?keyword={product_id}"
        driver.get(search_url)
        time.sleep(4) 

        page_source = driver.page_source
        no_result_keywords = ['검색 결과가 없습니다', '검색결과가 없습니다', '결과가 없습니다']
        
        if any(keyword in page_source for keyword in no_result_keywords):
            return "Expired"

        items = driver.find_elements(By.CSS_SELECTOR, "a[href*='/product/']")
        is_exact_match = any(product_id in str(item.get_attribute('href')) for item in items)

        return "Active" if is_exact_match else "Expired"
    except:
        return "Error"

# --- [Selenium 설정] ---
def get_driver():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    
    # 로컬 환경과 Streamlit Cloud 환경 모두 호환되도록 설정
    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
    except:
        # Streamlit Cloud (Linux) 환경 대응
        options.binary_location = "/usr/bin/chromium"
        service = Service("/usr/bin/chromedriver")
        driver = webdriver.Chrome(service=service, options=options)
    return driver

# --- [UI 구성] ---
st.set_page_config(page_title="URL Checker", layout="wide")
st.title("📌 통합 URL 상태 확인 도구")
st.markdown("""
이 도구는 **CSV 파일** 또는 **공개된 구글 스프레드시트**의 데이터를 분석합니다.  
분석이 끝나면 엑셀(.xlsx) 파일로 결과물을 받을 수 있습니다.
""")

# 1. 입력 방식 선택
input_method = st.radio("데이터 입력 방식을 선택하세요", ["CSV 파일 업로드", "구글 스프레드시트 URL 입력"])

df = None

# 2. 데이터 불러오기
if input_method == "CSV 파일 업로드":
    uploaded_file = st.file_uploader("분석할 CSV 파일을 업로드하세요", type=["csv"])
    if uploaded_file is not None:
        try:
            df = pd.read_csv(uploaded_file, encoding='utf-8-sig')
        except:
            df = pd.read_csv(uploaded_file, encoding='cp949')

elif input_method == "구글 스프레드시트 URL 입력":
    sheet_url = st.text_input("구글 스프레드시트 주소를 붙여넣으세요 (공유 설정: '링크가 있는 모든 사용자')")
    if sheet_url:
        try:
            if "/d/" in sheet_url:
                sheet_id = sheet_url.split("/d/")[1].split("/")[0]
                export_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv"
                df = pd.read_csv(export_url)
                st.success("✅ 구글 시트 데이터를 가져왔습니다.")
            else:
                st.error("올바른 구글 시트 주소가 아닙니다.")
        except Exception as e:
            st.error("시트를 읽을 수 없습니다. 시트가 '공유 가능' 상태인지 확인해주세요.")

# 3. 분석 실행
if df is not None:
    st.write(f"📊 로드된 데이터: {len(df)}행")
    
    if st.button("분석 시작"):
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        driver = None
        # N열(인덱스 13)에 'trenbe'가 포함되어 있는지 확인
        platforms = df.iloc[:, 13].astype(str).str.lower().values
        if any('trenbe' in p for p in platforms):
            with st.spinner("브라우저를 구동 중입니다..."):
                driver = get_driver()
        
        total = len(df)
        for idx in range(total):
            url = df.iloc[idx, 2]         # C열 (인덱스 2)
            platform = str(df.iloc[idx, 13]).lower() # N열 (인덱스 13)
            
            result = "Skipped"
            if 'pinterest' in platform:
                result = check_pinterest_status(url)
            elif 'trenbe' in platform:
                if driver:
                    result = check_trenbe_status(url, driver)
                else:
                    result = "Driver Error"
            
            # D열(인덱스 3)에 결과 저장
            df.iloc[idx, 3] = result
            
            progress_bar.progress((idx + 1) / total)
            status_text.text(f"[{idx+1}/{total}] {platform} 분석 중... 현재 결과: {result}")

        if driver: driver.quit()
        
        st.success("✅ 분석 완료!")
        st.dataframe(df.head(20)) # 상위 20개 결과 미리보기
        
        # 엑셀 파일 다운로드 로직
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Result')
        
        st.download_button(
            label="결과 엑셀(.xlsx) 파일 다운로드",
            data=buffer.getvalue(),
            file_name="url_check_result.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

# --- 사용 팁 ---
with st.sidebar:
    st.header("💡 사용 팁")
    st.info("""
    1. **구글 시트 사용 시**: 시트 우측 상단 '공유' -> '링크가 있는 모든 사용자'로 변경 후 URL을 복사하세요.
    2. **확장 프로그램 연동**: 결과 엑셀 파일을 구글 시트에 복사한 뒤, 우리가 만든 **체인 아이콘**을 눌러 한 번에 확인하세요!
    """)
