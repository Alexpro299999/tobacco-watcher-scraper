import time
import random
import logging
from urllib.parse import urlparse, parse_qs
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from selenium_stealth import stealth

START_URL = "https://tobaccowatcher.globaltobaccocontrol.org/articles/?st=&e=&lang=en&section=keywords&dups=0&sort=timestamp"
OUTPUT_FILE = "collected_domains_v2.txt"

IGNORE_DOMAINS = [
    "tobaccowatcher.globaltobaccocontrol.org",
    "twitter.com", "facebook.com", "linkedin.com", "instagram.com",
    "youtube.com", "t.co", "goo.gl", "bit.ly", "javascript", "localhost", "whatsapp.com"
]

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger()


def extract_real_domain(url):
    if not url or len(url) < 4:
        return None
    if "globaltobaccocontrol.org" not in url and "http" in url:
        try:
            return urlparse(url).netloc.replace("www.", "").lower()
        except:
            return None
    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    for key in query:
        val = query[key][0]
        if val.startswith("http"):
            try:
                res = urlparse(val).netloc.replace("www.", "").lower()
                if res: return res
            except:
                pass
    return None


def save_domains_to_file(domains):
    try:
        with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
            for d in sorted(list(domains)):
                f.write(f"{d}\n")
    except Exception as e:
        logger.error(f"IO Error: {e}")


def nuke_walkthrough(driver):
    try:
        driver.execute_script("""
            const selectors = [
                '.introjs-overlay', '.introjs-helperLayer', '.introjs-tooltip', 
                '.hopscotch-bubble', '.joyride-tip-guide', '.guide-tour-container',
                '.introjs-fixedTooltip', '.introjs-skipbutton'
            ];
            selectors.forEach(s => {
                document.querySelectorAll(s).forEach(el => el.remove());
            });
        """)
    except:
        pass


def run_scraper():
    chrome_options = Options()
    chrome_options.add_argument("--start-maximized")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)

    stealth(driver,
            languages=["en-US", "en"],
            vendor="Google Inc.",
            platform="Win32",
            webgl_vendor="Intel Inc.",
            renderer="Intel Iris OpenGL Engine",
            fix_hairline=True,
            )

    unique_domains = set()
    try:
        with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    unique_domains.add(line.strip())
    except FileNotFoundError:
        pass

    logger.info(f"Loaded {len(unique_domains)} existing domains.")

    try:
        driver.get(START_URL)
        time.sleep(10)
        nuke_walkthrough(driver)

        idle_cycles = 0
        total_scrolls = 0

        while True:
            nuke_walkthrough(driver)

            steps = random.randint(5, 10)
            for _ in range(steps):
                offset = random.randint(400, 800)
                driver.execute_script(f"window.scrollBy(0, {offset});")
                time.sleep(random.uniform(0.2, 0.5))

            time.sleep(random.uniform(2, 4))

            links = driver.find_elements(By.TAG_NAME, "a")
            new_found = 0

            for link in links:
                try:
                    href = link.get_attribute("href")
                    domain = extract_real_domain(href)
                    if domain and "." in domain:
                        if not any(bad in domain for bad in IGNORE_DOMAINS):
                            if domain not in unique_domains:
                                unique_domains.add(domain)
                                new_found += 1
                                logger.info(f"Found new: {domain}")
                except:
                    continue

            total_scrolls += 1
            if new_found > 0:
                save_domains_to_file(unique_domains)
                idle_cycles = 0
                logger.info(f"Progress: {len(unique_domains)} total domains.")
            else:
                idle_cycles += 1
                if idle_cycles % 5 == 0:
                    logger.info(f"Scrolling... (Scroll #{total_scrolls}, no new domains for {idle_cycles} cycles)")

            if idle_cycles > 40:
                logger.info("Reached end of new content.")
                break

    except KeyboardInterrupt:
        logger.info("Stopped.")
    finally:
        save_domains_to_file(unique_domains)
        driver.quit()


if __name__ == "__main__":
    run_scraper()