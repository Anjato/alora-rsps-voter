from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager


def create_driver():
    # Add options to chrome
    options = webdriver.ChromeOptions()
    options.add_experimental_option("useAutomationExtension", False)
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                         "Chrome/113.0.0.0 Safari/537.36")
    options.add_argument("--disable-infobars")
    options.add_argument("--disable-notifications")
    options.add_argument("--disable-blink-features")

    # Create a ChromeService instance with the Chrome driver executable
    service = ChromeService(ChromeDriverManager().install())

    # Open browser
    driver = webdriver.Chrome(service=service, options=options)

    return driver


def create_wait(driver, timeout=3):
    wait = WebDriverWait(driver, timeout)
    return wait
