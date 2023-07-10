# my modules
import sql_database
from driver_utils import create_driver, create_wait

# other modules
import atexit
import colorlog
import importlib
import json
import logging as log
import random
import requests
import subprocess
import sys
import time
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as ec

driver = create_driver()
wait = create_wait(driver, 10)
driver.set_window_size(1920, 1080)

# Set vote url
vote_url = "https://www.alora.io/vote/"
all_votable_sites = {1: "RuneLocus", 2: "", 3: "TopG", 4: "RSPS-List", 5: "", 6: "", 7: "MoparScape", 8: "", 9: ""}
vpn_regions_list = []


def main():
    vote()
    change_ip()


def vote():
    current_ip = get_ip()
    driver.get(vote_url)

    try:
        # Check if already voted on all websites
        already_voted_element = ".vote_content > h2:nth-child(2)"
        already_voted = wait.until(ec.presence_of_element_located((By.CSS_SELECTOR, already_voted_element)))
        log.info(f"{current_ip} | {already_voted.text}")
        save_auth_json()
        return
    except TimeoutException:
        log.info(f"{current_ip} | You have not voted on all sites within the past 12 hours. Proceeding to vote!")

    votable_sites_dict = check_votable_sites()

    log.info(votable_sites_dict)

    for siteid, value in votable_sites_dict.items():
        if not value:
            log.debug(siteid, value)
            votable_site = driver.find_element(By.CSS_SELECTOR, f'a[siteid=\'{siteid}\']')
            votable_site.click()

            # Get all tabs
            window_handles = driver.window_handles

            # Switch driver focus to new tab
            new_table_handle = window_handles[-1]
            driver.switch_to.window(new_table_handle)

            site_name = all_votable_sites.get(int(siteid), "")
            module_name = site_name.lower().replace("-", "")

            try:
                log.info(f"Voting on site: {site_name} (id: {siteid})")
                module = importlib.import_module(module_name)
                getattr(module, "vote")(driver, wait, log)
                log.info(f"Cleaning up {site_name} tab")
                cleanup(window_handles)
            except ImportError:
                log.error(f"Module {module_name} not found!")

    save_auth_json()


def save_auth_json():
    log.debug("saving auth")
    current_ip = get_ip()
    votable_sites_dict = check_votable_sites()

    if any(value is False for value in votable_sites_dict.values()):
        log.info("At least one website is votable still!")
        log.info(votable_sites_dict)
        vote()
    else:
        auth_code = get_auth()
        try:
            with open("auth_codes.json", "r") as file:
                data = json.load(file)
        except FileNotFoundError:
            data = {}

        if current_ip in data:
            ip_data = data[current_ip]
        else:
            ip_data = {}

        if auth_code not in ip_data.values():
            authcode_keys = [key for key in ip_data.keys() if key.startswith("auth_")]
            authcode_key = f"auth_{len(authcode_keys) + 1}"

            ip_data[authcode_key] = auth_code

        data[current_ip] = ip_data

        log.info("Saving data to JSON file")
        with open("auth_codes.json", "w") as file:
            json.dump(data, file, indent=4)

        current_region = subprocess.check_output("piactl get region", shell=True).decode("utf-8")
        sql_database.save_data(current_ip, current_region, auth_code, log)


def get_auth():
    try:
        authcode = wait.until(ec.presence_of_element_located((By.CSS_SELECTOR, "#notice-text")))
        driver.refresh()

        while True:
            authcode = wait.until(ec.presence_of_element_located((By.CSS_SELECTOR, "#notice-text")))
            log.info(f"get_auth while loop: {authcode.text}")
            # authcode may be getting stuck here for some reason and not sure why. probably a server issue
            # best to investigate a bit further to confirm and then put a for loop instead and only repeat ~5 times
            # before breaking out of the loop and simply changing IPs
            if authcode.text == "------":
                log.info(authcode.text)
                driver.refresh()
            else:
                break
    except TimeoutException:
        log.warning("Failed to get auth code! Trying again")
        main()

    return authcode.text


def change_ip():
    log.info("Disconnecting from VPN")
    subprocess.check_output("piactl disconnect", shell=True)

    output = subprocess.check_output("piactl get vpnip", shell=True).decode("utf-8")
    log.info("Waiting for VPN to disconnect")
    while output.strip() != "Unknown":
        output = subprocess.check_output("piactl get vpnip", shell=True).decode("utf-8")

    # Remove first entry in dictionary
    vpn_regions_list.pop(0)

    # Change region to connect to the first entry in the dictionary
    region_to_connect = vpn_regions_list[0]

    # Allow VPN to disconnect for long enough before connecting
    time.sleep(1)

    subprocess.check_output(f"piactl set region {region_to_connect}", shell=True)
    subprocess.check_output("piactl connect", shell=True)

    log.info("Waiting for VPN to connect")
    output = subprocess.check_output("piactl get vpnip", shell=True).decode("utf-8")
    while output.strip() == "Unknown":
        output = subprocess.check_output("piactl get vpnip", shell=True).decode("utf-8")

    log.info(f"New IP: {output.strip()}")
    log.info(f"New Region: {region_to_connect}")
    main()


def get_vpn_regions():
    output = subprocess.check_output("piactl get regions", shell=True).decode("utf-8")
    regions = output.strip().split("\n")

    for region in regions[1:]:
        vpn_regions_list.append(region)

    return random.shuffle(vpn_regions_list)


def get_ip():
    vpn_state = subprocess.check_output("piactl get connectionstate", shell=True).decode("utf-8")

    if vpn_state.strip() == "Connected":
        return subprocess.check_output("piactl get vpnip", shell=True).decode("utf-8").strip()
    elif vpn_state.strip() == "Disconnected":
        return subprocess.check_output("piactl get pubip", shell=True).decode("utf-8").strip()
    else:
        log.critical(f"The fuck is the VPN state? {vpn_state.strip()}")
        sys.exit(1)


def check_votable_sites():
    log.info("Checking votable sites")
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


def setup_logging():
    # Pretty colors :)
    formatter = colorlog.ColoredFormatter(
        "%(log_color)s%(asctime)s | %(levelname)-8s | %(message)s",
        log_colors={
            'DEBUG': 'cyan',
            'INFO': 'green',
            'WARNING': 'yellow',
            'ERROR': 'red',
            'CRITICAL': 'bold_red',
        }
    )

    # Configure the logger
    logger = log.getLogger()
    logger.setLevel(log.INFO)

    # Create a console handler
    console_handler = log.StreamHandler()
    console_handler.setLevel(log.DEBUG)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # Create a file handler
    file_handler = log.FileHandler('debug.log')
    file_handler.setLevel(log.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)


def cleanup(window_handles):
    driver.close()

    main_tab_handle = window_handles[0]
    driver.switch_to.window(main_tab_handle)


def application_exit():
    log.info("Exiting application and cleaning up")
    driver.quit()
    subprocess.check_output("piactl disconnect", shell=True)


setup_logging()
atexit.register(application_exit)
get_vpn_regions()
change_ip()
main()
driver.quit()
