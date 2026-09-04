import time
import random
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium_stealth import stealth

# -------------------- إعدادات عامة --------------------
VIDEO_URL = "https://youtu.be/TCza4Ml9xKs?si=93nVcyRP0u1iCPGU"
NUMBER_OF_SESSIONS = 3          # قلل العدد لتقليل الاستهلاك
WATCH_DURATION = 30             # مدة أقصر للتجربة
MAX_WORKERS = 2                 # توازي أقل لتفادي الحظر
USE_PROXY = False
PROXY_LIST = []

USE_STEALTH = True
RANDOM_USER_AGENT = True
HEADLESS = True                 # يجب أن يكون True في الخادم
DISABLE_GPU = True
DISABLE_LOGGING = True
INCOGNITO = True

RANDOM_DELAY_BETWEEN_SESSIONS = True
MIN_DELAY = 1
MAX_DELAY = 3

MAX_RETRIES = 1                 # قلل المحاولات لتفادي الحظر

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("youtube_bot.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
]

def get_random_user_agent():
    return random.choice(USER_AGENTS)

def configure_driver():
    options = uc.ChromeOptions()

    if HEADLESS:
        options.add_argument("--headless=new")
    if INCOGNITO:
        options.add_argument("--incognito")
    if DISABLE_GPU:
        options.add_argument("--disable-gpu")
    if DISABLE_LOGGING:
        options.add_argument("--log-level=3")
        options.add_argument("--silent")
        options.add_experimental_option("excludeSwitches", ["enable-logging"])

    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-infobars")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-notifications")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--autoplay-policy=no-user-gesture-required")
    options.add_argument("--use-fake-ui-for-media-stream")
    options.add_argument("--use-fake-device-for-media-stream")
    options.add_argument("--disable-software-rasterizer")

    if RANDOM_USER_AGENT:
        user_agent = get_random_user_agent()
        options.add_argument(f"--user-agent={user_agent}")

    if USE_PROXY and PROXY_LIST:
        proxy = random.choice(PROXY_LIST)
        options.add_argument(f'--proxy-server={proxy}')
        logger.info(f"استخدام البروكسي: {proxy}")

    driver = uc.Chrome(options=options)

    if USE_STEALTH:
        stealth(
            driver,
            languages=["en-US", "en"],
            vendor="Google Inc.",
            platform="Win32",
            webgl_vendor="Intel Inc.",
            renderer="Intel Iris OpenGL Engine",
            fix_hairline=True,
        )
        logger.info("تم تطبيق selenium-stealth")

    return driver

def close_cookie_popup(driver, wait):
    try:
        selectors = [
            '//button[contains(@aria-label, "Accept")]',
            '//button[contains(., "Accept all")]',
            '//button[contains(., "I agree")]',
            '//button[contains(@aria-label, "Agree")]',
            '//button[contains(@class, "yt-spec-button-shape-next--filled")]'
        ]
        for selector in selectors:
            try:
                element = wait.until(EC.element_to_be_clickable((By.XPATH, selector)))
                element.click()
                logger.info("تم إغلاق نافذة الكوكيز")
                time.sleep(1)
                return True
            except:
                continue
        return False
    except:
        return False

def play_video(driver, wait):
    try:
        video_element = wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "video.html5-main-video"))
        )
    except:
        logger.warning("لم يتم العثور على عنصر الفيديو")
        return False

    # كتم الصوت
    try:
        driver.execute_script("document.querySelector('video').muted = true;")
    except:
        pass

    # محاولة التشغيل عبر JavaScript
    try:
        driver.execute_script("document.querySelector('video').play();")
        time.sleep(2)
        is_playing = driver.execute_script("return !document.querySelector('video').paused;")
        if is_playing:
            logger.info("الفيديو يعمل الآن")
            return True
    except:
        pass

    # محاولة النقر على زر التشغيل كخطة بديلة
    try:
        play_button = driver.find_element(By.CSS_SELECTOR, "button.ytp-play-button")
        driver.execute_script("arguments[0].click();", play_button)
        logger.info("تم النقر على زر التشغيل")
        time.sleep(2)
        return True
    except:
        logger.error("فشل تشغيل الفيديو")
        return False

def watch_video_once(session_id):
    driver = None
    retries = 0

    while retries <= MAX_RETRIES:
        try:
            logger.info(f"--- بدء الجلسة {session_id} (محاولة {retries+1}) ---")
            driver = configure_driver()
            wait = WebDriverWait(driver, 20)

            driver.get(VIDEO_URL)
            logger.info(f"جلسة {session_id}: تم فتح الصفحة")
            time.sleep(5)
            driver.execute_script("window.scrollBy(0, 300);")
            time.sleep(2)

            # فحص إذا تم التحويل لصفحة تحقق
            current_url = driver.current_url
            if "consent" in current_url or "sorry" in current_url:
                logger.error("تم التحويل إلى صفحة تحقق/حظر")
                return False

            close_cookie_popup(driver, wait)

            if not play_video(driver, wait):
                raise Exception("تعذر تشغيل الفيديو")

            logger.info(f"جلسة {session_id}: الانتظار {WATCH_DURATION} ثانية")
            time.sleep(WATCH_DURATION)

            logger.info(f"جلسة {session_id}: اكتملت بنجاح")
            return True

        except Exception as e:
            logger.error(f"جلسة {session_id}: خطأ - {e}")
            retries += 1
            if retries > MAX_RETRIES:
                logger.error(f"جلسة {session_id}: فشلت نهائيًا")
                return False
            else:
                time.sleep(random.uniform(3, 7))

        finally:
            if driver:
                try:
                    driver.quit()
                    logger.info(f"جلسة {session_id}: تم إغلاق المتصفح")
                except:
                    pass

def main():
    logger.info(f"بدء التشغيل: {NUMBER_OF_SESSIONS} جلسة، مدة كل جلسة {WATCH_DURATION} ثانية، عدد المتوازيين {MAX_WORKERS}")

    successful = 0
    failed = 0

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = [executor.submit(watch_video_once, i+1) for i in range(NUMBER_OF_SESSIONS)]

        for future in as_completed(futures):
            if future.result():
                successful += 1
            else:
                failed += 1

            if RANDOM_DELAY_BETWEEN_SESSIONS:
                delay = random.uniform(MIN_DELAY, MAX_DELAY)
                time.sleep(delay)

    logger.info(f"النتيجة النهائية: نجحت {successful} جلسة، فشلت {failed} جلسة")

if __name__ == "__main__":
    main()
