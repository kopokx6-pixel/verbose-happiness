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
NUMBER_OF_SESSIONS = 5          # عدد الجلسات المطلوبة
WATCH_DURATION = 60             # مدة المشاهدة بالثواني (قابلة للتعديل)
MAX_WORKERS = 3                 # عدد المتصفحات التي تعمل في نفس الوقت (التوازي)
USE_PROXY = False               # ضع True إذا أردت استخدام بروكسي
PROXY_LIST = []                 # قائمة البروكسيات (إذا USE_PROXY = True)

# إعدادات التخفي
USE_STEALTH = True              # استخدام selenium-stealth
RANDOM_USER_AGENT = True        # استخدام User-Agent عشوائي
HEADLESS = False                # وضع بدون واجهة (قد يزيد الاكتشاف)
DISABLE_GPU = True              # تعطيل GPU
DISABLE_LOGGING = True          # تقليل السجلات
INCOGNITO = True                # وضع التخفي

# إعدادات التأخير العشوائي
RANDOM_DELAY_BETWEEN_SESSIONS = True
MIN_DELAY = 1
MAX_DELAY = 5

# إعدادات إعادة المحاولة
MAX_RETRIES = 2

# -------------------- إعداد السجل --------------------
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("youtube_bot.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# -------------------- قائمة User-Agents عشوائية --------------------
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/119.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15"
]

# -------------------- دوال مساعدة --------------------
def get_random_user_agent():
    return random.choice(USER_AGENTS)

def configure_driver():
    """إنشاء متصفح Chrome مهيأ بالكامل."""
    options = uc.ChromeOptions()

    # خيارات أساسية
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

    # إعدادات إضافية لتجنب الكشف
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-infobars")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-notifications")
    options.add_argument("--start-maximized")

    # User-Agent عشوائي
    if RANDOM_USER_AGENT:
        user_agent = get_random_user_agent()
        options.add_argument(f"--user-agent={user_agent}")

    # إضافة بروكسي إذا مطلوب
    if USE_PROXY and PROXY_LIST:
        proxy = random.choice(PROXY_LIST)
        options.add_argument(f'--proxy-server={proxy}')
        logger.info(f"استخدام البروكسي: {proxy}")

    # إنشاء المتصفح باستخدام undetected_chromedriver
    driver = uc.Chrome(options=options)

    # تطبيق selenium-stealth إذا مفعل
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
    """محاولة إغلاق نافذة الكوكيز إذا ظهرت."""
    try:
        # عدة محاولات لمحددات مختلفة
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
    """التأكد من أن الفيديو يعمل، وإذا لم يكن فاضغط play."""
    # انتظار وجود مشغل الفيديو
    try:
        video_element = wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "video.html5-main-video"))
        )
    except:
        logger.warning("لم يتم العثور على عنصر الفيديو")
        return False

    # التحقق من حالة التشغيل عبر JavaScript
    try:
        is_paused = driver.execute_script("return document.querySelector('video').paused;")
        if is_paused:
            # النقر على زر التشغيل
            play_button = wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "button.ytp-play-button"))
            )
            play_button.click()
            logger.info("تم الضغط على زر التشغيل")
        else:
            logger.info("الفيديو يعمل بالفعل")
        return True
    except:
        # محاولة التشغيل عبر JavaScript
        try:
            driver.execute_script("document.querySelector('video').play();")
            logger.info("تم التشغيل عبر JavaScript")
            return True
        except Exception as e:
            logger.error(f"فشل تشغيل الفيديو: {e}")
            return False

def watch_video_once(session_id):
    """تنفيذ جلسة مشاهدة كاملة."""
    driver = None
    retries = 0

    while retries <= MAX_RETRIES:
        try:
            logger.info(f"--- بدء الجلسة {session_id} (محاولة {retries+1}) ---")
            driver = configure_driver()
            wait = WebDriverWait(driver, 20)

            # فتح الرابط
            driver.get(VIDEO_URL)
            logger.info(f"جلسة {session_id}: تم فتح الصفحة")

            # إغلاق الكوكيز
            close_cookie_popup(driver, wait)

            # تشغيل الفيديو
            if not play_video(driver, wait):
                raise Exception("تعذر تشغيل الفيديو")

            # الانتظار لمدة المشاهدة
            logger.info(f"جلسة {session_id}: الانتظار {WATCH_DURATION} ثانية")
            time.sleep(WATCH_DURATION)

            logger.info(f"جلسة {session_id}: اكتملت بنجاح")
            return True

        except Exception as e:
            logger.error(f"جلسة {session_id}: خطأ - {e}")
            retries += 1
            if retries > MAX_RETRIES:
                logger.error(f"جلسة {session_id}: فشلت نهائيًا بعد {MAX_RETRIES} محاولات")
                return False
            else:
                # تأخير قبل إعادة المحاولة
                time.sleep(random.uniform(3, 7))

        finally:
            if driver:
                try:
                    driver.quit()
                    logger.info(f"جلسة {session_id}: تم إغلاق المتصفح")
                except:
                    pass

def main():
    """الوظيفة الرئيسية لتشغيل الجلسات بالتوازي."""
    logger.info(f"بدء التشغيل: {NUMBER_OF_SESSIONS} جلسة، مدة كل جلسة {WATCH_DURATION} ثانية، عدد المتوازيين {MAX_WORKERS}")

    successful = 0
    failed = 0

    # استخدام ThreadPoolExecutor للتوازي
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        # إنشاء قائمة بالمهام
        futures = [executor.submit(watch_video_once, i+1) for i in range(NUMBER_OF_SESSIONS)]

        # انتظار النتائج
        for future in as_completed(futures):
            if future.result():
                successful += 1
            else:
                failed += 1

            # تأخير عشوائي بين الجلسات (اختياري)
            if RANDOM_DELAY_BETWEEN_SESSIONS:
                delay = random.uniform(MIN_DELAY, MAX_DELAY)
                time.sleep(delay)

    logger.info(f"النتيجة النهائية: نجحت {successful} جلسة، فشلت {failed} جلسة")

if __name__ == "__main__":
    main()
