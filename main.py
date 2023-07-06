# my modules
import topg
import runelocus
import moparscape
import captchasolver
import rspslist
import piavpn

# other modules
import requests
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.ui import WebDriverWait, Select
from webdriver_manager.chrome import ChromeDriverManager

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

# Default wait time in seconds
wait = WebDriverWait(driver, 5)
driver.set_window_size(1920, 1080)

# Set vote url
vote_url = "https://www.alora.io/vote/"
ip_url = "https://api.my-ip.io/ip"
all_votable_sites = {1: "RuneLocus", 2: "", 3: "TopG", 4: "RSPS-List", 5: "", 6: "", 7: "MoparScape", 8: "", 9: ""}


def main():
    #change_ip()
    vote()


def vote():
    current_ip = requests.get(ip_url).text
    driver.get(vote_url)

    try:
        # Check if already voted
        already_voted_element = ".vote_content > h2:nth-child(2)"
        already_voted = wait.until(ec.presence_of_element_located((By.CSS_SELECTOR, already_voted_element)))
        print(f"{current_ip} | {already_voted.text}")
    except TimeoutException as e:
        print(f"{current_ip} | You have not voted yet. Proceeding to vote...")

    votable_sites_dict = check_votable_sites()

    for siteid, value in votable_sites_dict.items():
        if not value:
            votable_site = driver.find_element(By.CSS_SELECTOR, f'a[siteid="{siteid}"]')
            votable_site.click()
            site_name = all_votable_sites.get(int(siteid), "")
            print(f"Voting on site: {site_name} (Id: {siteid})")


def check_votable_sites():
    response = requests.get('https://www.alora.io/vote_includes/load.php?id=vote_data')
    json_data = response.json()

    data = json_data['data']

    button_selector = ".vote_content > .btn-oldstyle2"

    votable_sites_dict = {}

    for button in driver.find_elements(By.CSS_SELECTOR, button_selector):
        siteid = button.get_attribute('siteid')
        value = data.get(siteid, 0)
        votable_sites_dict[siteid] = bool(value)

    return votable_sites_dict


main()
driver.quit()
