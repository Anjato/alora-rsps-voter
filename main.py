# my modules
import sql_database
from driver_utils import create_driver, create_wait

# other modules
import atexit
import colorlog
import concurrent
import importlib
import json
import logging as log
import random
import requests
import subprocess
import sys
import time
from concurrent.futures import ProcessPoolExecutor
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as ec

# Set vote url
vote_url = "https://www.alora.io/vote/"
all_votable_sites = {1: "RuneLocus", 2: "", 3: "TopG", 4: "RSPS-List", 5: "", 6: "", 7: "MoparScape", 8: "", 9: ""}
vpn_regions_list = []
voted_sites = []


def main():
    setup_logging()
    atexit.register(application_exit)

    get_vpn_regions()
    change_ip()

    driver = create_driver()
    wait = create_wait(driver, 10)
    driver.set_window_size(1920, 1080)
    driver.get(vote_url)

    while True:
        driver.refresh()
        voted_sites.clear()

        while True:
            vote(wait)

            if len(voted_sites) != 4:
                log.warning("At least one website is votable still!")
                log.warning(voted_sites)
            else:
                break

        log.info("Completed voting. Saving auth code1")
        save_auth_code(driver, wait)

        change_ip()


def vote(wait):
    current_ip = get_ip()

    votable_sites_dict = check_votable_sites()

    if not votable_sites_dict:
        log.info(f"All sites have already been voted on from {current_ip}!")
        return

    vote_site_url_dict = {}
    for siteid in votable_sites_dict.keys():
        try:
            url_element = wait.until(ec.presence_of_element_located((By.CSS_SELECTOR, f'a[siteid=\'{siteid}\']')))
            url = url_element.get_attribute('href')
            vote_site_url_dict[siteid] = url
        except TimeoutException as e:
            log.critical(f"Unable to find element for siteid: {siteid}. Error: {str(e)}")

    with ProcessPoolExecutor() as executor:
        futures = {executor.submit(vote_site, (siteid, url)): (siteid, url) for siteid, url in vote_site_url_dict.items()}
        for future in concurrent.futures.as_completed(futures):
            siteid, url = futures[future]
            try:
                vote_successful = future.result()
                if vote_successful:
                    voted_sites.append(siteid)
                    log.info(f"Successfully added: {url} to the voted list")
                else:
                    log.error(f"Failed to vote: {url}. Trying again later")
            except Exception as e:
                log.error(f"Site {siteid} generated an exception: {e}")


def vote_site(args):
    siteid, site_url = args

    driver = create_driver()
    wait = create_wait(driver, 10)
    driver.set_window_size(1920, 1080)
    driver.get(site_url)

    site_name = all_votable_sites.get(int(siteid), "")
    module_name = site_name.lower().replace("-", "")

    vote_successful = False

    try:
        try:
            log.info(f"Voting on site: {site_name} (id: {siteid})")
            module = importlib.import_module(module_name)
            getattr(module, "vote")(driver, wait, log)
            log.info(f"Cleaning up {site_name} tab")
            driver.quit()
        except ImportError:
            log.error(f"Module {module_name} not found!")
            driver.quit()

        vote_successful = True
    except Exception as e:
        pass

    return vote_successful


def save_auth_code(driver, wait):
    log.debug("saving auth")
    current_ip = get_ip()

    if len(voted_sites) != 4:
        log.info("At least one website is votable still!")
        vote(wait)
    else:
        auth_code = get_auth(driver, wait)
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


def get_auth(driver, wait):
    try:
        authcode = wait.until(ec.presence_of_element_located((By.CSS_SELECTOR, "#notice-text")))
        driver.refresh()

        while True:
            authcode = wait.until(ec.presence_of_element_located((By.CSS_SELECTOR, "#notice-text")))
            if authcode.text == "------":
                log.info(authcode.text)
                driver.refresh()
            else:
                break
    except TimeoutException:
        log.warning("Failed to get auth code! Trying again")
        return False

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

    votable_sites_dict = {}

    for key, value in all_votable_sites.items():
        if value and data.get(str(key)) == 0:
            votable_sites_dict[key] = value

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


def application_exit():
    log.info("Exiting application and cleaning up")
    #subprocess.check_output("piactl disconnect", shell=True)


main()
