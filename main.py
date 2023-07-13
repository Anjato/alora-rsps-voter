# my modules
import sql_database
from driver_utils import create_driver, create_wait
from runelocus import test_split_tunnel
# other modules
import atexit
import colorlog
import concurrent
import datetime
import importlib
import json
import logging as log
import random
import requests
import select
import subprocess
import sys
import time
from bs4 import BeautifulSoup
from concurrent.futures import ProcessPoolExecutor
from retry import retry
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as ec

# Set vote url
vote_url = "https://www.alora.io/vote/"
all_votable_sites = {1: "RuneLocus", 3: "TopG", 4: "RSPS-List", 7: "MoparScape"}
vpn_regions_list = []
voted_sites = []


def main():
    setup_logging()

    get_vpn_regions()
    change_ip()

    driver = create_driver()
    atexit.register(application_exit, driver)
    wait = create_wait(driver, 10)
    driver.set_window_size(1920, 1080)
    driver.get(vote_url)

    while True:
        max_retries = 0
        voted_sites.clear()
        driver.refresh()

        while True:
            vote(wait)

            while max_retries <= 3:
                if len(voted_sites) != 4:
                    log.warning("At least one website is votable still!")
                    log.warning(voted_sites)
                    max_retries += 1
                    vote(wait)
                else:
                    log.info("No more votable sites found!")
                    max_retries = 0
                    break

            if max_retries >= 3:
                voting_failed = True
            else:
                voting_failed = False

            if voting_failed:
                log.error("Unknown error! Critical failure on at least one site. Possibly a bad or banned VPN IP address.")
                log.info("Changing IP address")
                change_ip()
            else:
                log.info("Completed voting. Saving auth code")
                save_auth_code(driver, wait)
                change_ip()

            break


def vote(wait):
    current_ip = get_ip()

    try:
        votable_sites_dict = check_votable_sites()
    except ConnectionError:
        change_ip()
        return

    if not votable_sites_dict:
        log.info(f"All sites have already been voted on from {current_ip}!")
        return

    vote_site_url_dict = {}
    for siteid in votable_sites_dict.keys():
        if siteid in voted_sites:
            log.info(f"Site {siteid} already voted, skipping...")
            continue
        try:
            url_element = wait.until(ec.presence_of_element_located((By.CSS_SELECTOR, f'a[siteid=\'{siteid}\']')))
            url = url_element.get_attribute('href')
            vote_site_url_dict[siteid] = url
        except TimeoutException as e:
            # This means it cannot find the button on the main page. Most likely an issue with the network/vpn so
            # changing the IP here is kinda the only workaround.
            log.critical(f"Unable to find element for siteid: {siteid}. Error: {str(e)}")
            voted_sites.clear()
            return

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
            vote_successful = True
        except ImportError:
            log.error(f"Module {module_name} not found!")
            driver.quit()
    except Exception:
        pass
    finally:
        log.info(f"Cleaning up {site_name} tab")
        driver.quit()

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
                log.critical("If this loop is stuck, it means there is a logic error elsewhere!")
                log.critical("Find where this was called and manually trace back")
                log.info(authcode.text)
                driver.refresh()
            else:
                break
    except TimeoutException:
        log.warning("Failed to get auth code! Trying again")
        return False

    return authcode.text


@retry(subprocess.CalledProcessError, tries=3, delay=5)
def change_ip():
    region_to_connect = []

    log.info("Disconnecting from VPN")
    subprocess.check_output("piactl disconnect", shell=True)

    # Start monitoring
    monitor_process = subprocess.Popen(['piactl', 'monitor', 'vpnip'], stdout=subprocess.PIPE, universal_newlines=True)

    vpn_regions_list.pop(0)

    try:
        region_to_connect = vpn_regions_list[0]
    except IndexError:
        log.warning("Ran out of VPN regions! Refreshing region list")
        get_vpn_regions()

    time.sleep(2)

    log.info("Connecting to VPN")
    subprocess.check_output(f"piactl set region {region_to_connect}", shell=True)
    subprocess.check_output("piactl connect", shell=True)

    start_time = time.time()
    try:
        while True:
            # Check if there's output from the monitor process
            if select.select([monitor_process.stdout], [], [], 0.0)[0]:
                line = monitor_process.stdout.readline().strip()
                if line != "Unknown":
                    log.info(f"New IP: {line}")
                    log.info(f"New Region: {region_to_connect}")
                    break
            elif time.time() - start_time > 30:  # If 30 seconds have passed
                log.error("VPN cannot connect. Trying again")
                raise subprocess.CalledProcessError(-1, "piactl connect", "VPN connect failed")
            else:
                time.sleep(0.5)
    finally:
        monitor_process.terminate()


@retry(subprocess.CalledProcessError, tries=3, delay=5)
def get_vpn_regions():
    output = subprocess.check_output("piactl get regions", shell=True).decode("utf-8")
    regions = output.strip().split("\n")

    for region in regions[1:]:
        vpn_regions_list.append(region)

    return random.shuffle(vpn_regions_list)


def get_ip():
    monitor_process = subprocess.Popen(['piactl', 'monitor', 'vpnip'], stdout=subprocess.PIPE, universal_newlines=True)

    start_time = time.time()
    timeout = 30  # timeout after 30 seconds

    try:
        while True:
            if select.select([monitor_process.stdout], [], [], 0.0)[0]:
                output = monitor_process.stdout.readline().strip()
                if output != "Unknown":
                    return output
            if time.time() - start_time > timeout:
                break
    finally:
        # Terminate the process if it's still running
        monitor_process.terminate()

    log.critical("Wtf is the VPN state? Could not get IP.")
    sys.exit(1)


def check_votable_sites():
    log.info("Checking votable sites")

    try:
        response = requests.get('https://www.alora.io/vote_includes/load.php?id=vote_data&bypasscache=')
    except requests.exceptions.ConnectionError:
        log.error("TCP/IP error trying to establish network connection to web server!")
        raise ConnectionError

    current_ip = get_ip()
    max_retries = 0

    while max_retries <= 5:
        try:
            json_data = response.json()

            data = json_data['data']

            votable_sites_dict = {}

            for key, value in all_votable_sites.items():
                if value and data.get(str(key)) == 0:
                    votable_sites_dict[key] = value
            return votable_sites_dict

        except requests.exceptions.JSONDecodeError:
            soup = BeautifulSoup(response.text, "html.parser")
            server_bad_query = soup.find("h2").text
            log.error(server_bad_query)
            max_retries += 1
            time.sleep(3)

    log.error(f"Unknown error! Server refusing to return query for IP {current_ip}")
    raise ConnectionError


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

    # Standard formatter for file handler
    file_formatter = log.Formatter("%(asctime)s | %(levelname)-8s | %(message)s")

    # Configure the logger
    logger = log.getLogger()
    logger.setLevel(log.INFO)

    # Create a console handler
    console_handler = log.StreamHandler()
    console_handler.setLevel(log.DEBUG)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # Create a file handler
    file_handler = log.FileHandler(f'logs/{datetime.date.today()}.log')
    file_handler.setLevel(log.DEBUG)
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)


def application_exit(driver):
    log.info("Exiting application and cleaning up")
    driver.quit()
    #subprocess.check_output("piactl disconnect", shell=True)


main()
