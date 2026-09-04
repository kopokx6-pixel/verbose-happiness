import time
import random
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# -------------------- الإعدادات --------------------
VIDEO_URL = "https://youtu.be/TCza4Ml9xKs?si=93nVcyRP0u1iCPGU"
NUMBER_OF_SESSIONS = 3
WATCH_DURATION = 30
MAX_WORKERS = 2
HEADLESS = True

# -------------------- السجل --------------------
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

def create_driver():
    """إنشاء متصفح Chrome."""
    chrome_options = Options()
    if HEADLESS:
        chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-notifications")
    chrome_options.add_argument("--mute-audio")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--autoplay-policy=no-user-gesture-required")
    chrome_options.add_argument("--lang=en-US")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option("useAutomationExtension", False)

    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36"
    ]
    chrome_options.add_argument(f"--user-agent={random.choice(user_agents)}")

    driver = webdriver.Chrome(options=chrome_options)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    return driver

def watch_video(session_id):
    """تشغيل جلسة مشاهدة واحدة."""
    driver = None
    try:
        logger.info(f"بدء الجلسة {session_id}")
        driver = create_driver()
        driver.get(VIDEO_URL)
        time.sleep(5)

        # إغلاق نافذة الكوكيز
        try:
            consent_button = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, '//button[contains(@aria-label, "Accept")] | //button[contains(., "Accept all")]'))
            )
            consent_button.click()
            time.sleep(1)
        except:
            pass

        # تشغيل الفيديو
        video = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "video.html5-main-video"))
        )
        driver.execute_script("arguments[0].muted = true;", video)
        driver.execute_script("arguments[0].play();", video)
        logger.info(f"جلسة {session_id}: تم تشغيل الفيديو")

        time.sleep(WATCH_DURATION)
        logger.info(f"جلسة {session_id}: انتهت بنجاح")
        return True

    except Exception as e:
        logger.error(f"جلسة {session_id} فشلت: {e}")
        return False
    finally:
        if driver:
            driver.quit()

def main():
    logger.info(f"بدء التشغيل: {NUMBER_OF_SESSIONS} جلسة، {MAX_WORKERS} متوازي")
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = [executor.submit(watch_video, i+1) for i in range(NUMBER_OF_SESSIONS)]
        results = [f.result() for f in as_completed(futures)]
    success = sum(results)
    logger.info(f"اكتمل: {success} نجح، {NUMBER_OF_SESSIONS - success} فشل")

if __name__ == "__main__":
    main()
