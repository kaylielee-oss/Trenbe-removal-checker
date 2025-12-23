from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def check_by_search(driver, url):
    try:
        # 1. URL에서 상품 코드 추출
        product_code_match = re.search(r'(\d+)', url)
        if not product_code_match:
            return "URL 오류"
        target_code = product_code_match.group(1)

        # 2. 검색 페이지 접속
        search_url = f"https://www.trenbe.com/search/?keyword={target_code}"
        driver.get(search_url)
        
        # 3. 유연한 대기 설정 (최대 10초)
        wait = WebDriverWait(driver, 10)
        
        try:
            # [조건 A] 검색 결과 리스트나 상품 아이템이 나타날 때까지 대기
            # 트렌비 상품 아이템의 공통적인 특징을 가진 요소를 기다립니다.
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "a[href*='/product/']")))
            
            # 검색 결과에 나타난 모든 상품 링크 확인
            product_elements = driver.find_elements(By.CSS_SELECTOR, "a[href*='/product/']")
            for elem in product_elements:
                href = elem.get_attribute("href")
                if target_code in href:
                    return "Active" # 일치하는 번호 발견 시 즉시 반환
            
            return "Expired" # 리스트는 떴으나 해당 번호가 없음

        except:
            # [조건 B] 대기 시간 내에 상품이 안 뜬 경우 -> '결과 없음' 문구나 아이콘 확인
            page_source = driver.page_source
            if "해당 상품이 없습니다" in page_source:
                return "Expired"
            
            # 간혹 로딩이 너무 느린 경우를 대비해 한 번 더 체크
            if target_code in page_source and "/product/" in page_source:
                return "Active"
            
            return "Expired"

    except Exception as e:
        return f"오류: {str(e)}"
