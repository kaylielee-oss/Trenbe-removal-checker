import pandas as pd
import re
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

# 1. 셀레니움 설정 (브라우저 창을 띄우지 않는 headless 모드)
chrome_options = Options()
# chrome_options.add_argument("--headless") 
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")

driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)

def check_status(url):
    try:
        # URL에서 상품 코드 추출 (숫자 부분)
        product_code = re.findall(r'\d+', url)[0]
        
        # 방법 A: 상품 상세 페이지 접속 후 버튼 상태 확인
        driver.get(url)
        time.sleep(2) # 페이지 로딩 대기
        
        try:
            # '바로 구매하기' 버튼 텍스트 확인
            # 트렌비는 품절 시 버튼 내부에 '품절' 텍스트가 포함되거나 클래스명이 변경됨
            buy_button = driver.find_element(By.XPATH, "//button[contains(text(), '구매하기')]")
            if "품절" in buy_button.text:
                return "Expired"
        except:
            pass # 버튼을 못 찾은 경우 검색 페이지로 2차 검증

        # 방법 B: 검색 결과 페이지 확인 (제공해주신 1, 3번 이미지 로직)
        search_url = f"https://www.trenbe.com/search/?keyword={product_code}"
        driver.get(search_url)
        time.sleep(2)

        page_source = driver.page_source
        
        # "해당 상품이 없습니다" 문구가 있거나 보라색 상자 아이콘(특정 클래스)이 있는 경우
        if "해당 상품이 없습니다" in page_source:
            return "Expired"
        
        # 상품 리스트가 존재하고, 검색한 상품 코드가 결과에 보이면 Active
        # (3번째 사진처럼 상품이 하나라도 뜨면 Active로 간주)
        product_list = driver.find_elements(By.CSS_SELECTOR, "div[class*='ProductItem']") # 실제 클래스명 확인 필요
        if len(product_list) > 0:
            return "Active"
        
        return "Expired" # 기본값

    except Exception as e:
        print(f"Error checking {url}: {e}")
        return "Error"

# 2. CSV 파일 불러오기 및 처리
input_file = 'products.csv'  # 파일 경로를 수정하세요
df = pd.read_csv(input_file)

# C열(url) 데이터를 읽어서 처리 (인덱스로 접근하거나 열 이름 사용)
# URL이 C열에 있다고 하셨으므로 df.iloc[:, 2] 또는 df['url']
results = []
for index, row in df.iterrows():
    url = row.iloc[2] # C열
    print(f"Checking: {url}")
    status = check_status(url)
    results.append(status)
    print(f"Result: {status}")

# 3. D열에 결과 저장
df['Status'] = results # 혹은 df.insert(3, 'Status', results)

# 결과 저장
df.to_csv('products_result.csv', index=False, encoding='utf-8-sig')

driver.quit()
print("작업 완료!")
