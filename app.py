import re
import time
from selenium.webdriver.common.by import By

def check_status_advanced(url, driver):
    try:
        # 1. URL에서 상품 ID(숫자) 추출
        match = re.search(r'\d+', str(url))
        if not match:
            return "Invalid URL"
        
        product_id = match.group()
        # 트렌비의 검색 시스템을 활용하여 해당 ID가 여전히 결과에 나오는지 확인
        search_url = f"https://www.trenbe.com/search?keyword={product_id}"
        driver.get(search_url)
        
        # 2. 동적 로딩 대기 (트렌비는 로딩 속도가 중요하므로 3~5초 권장)
        time.sleep(3)

        # 3. [안정성 강화] 텍스트 기반 판별 (다양한 키워드 대응)
        # 검색 결과가 없을 때 나타나는 공통 문구들을 체크합니다.
        page_source = driver.page_source
        no_result_keywords = ['검색 결과가 없습니다', '검색결과가 없습니다', '결과가 없습니다']
        
        if any(keyword in page_source for keyword in no_result_keywords):
            return "Expired"

        # 4. [정밀 검증] 상품 리스트 영역 확인
        # 검색 결과가 있다면 보통 상품 썸네일을 담는 특정 클래스가 존재합니다.
        # 트렌비의 경우 상품 리스트 아이템의 존재 여부를 파악합니다.
        items = driver.find_elements(By.CSS_SELECTOR, "a[href*='/product/']") # 상품 링크 패턴
        if len(items) == 0:
            return "Expired"

        return "Active"

    except Exception as e:
        print(f"Error checking {url}: {e}")
        return "Error"
