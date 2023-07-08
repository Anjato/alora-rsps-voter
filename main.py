# my modules
from driver_utils import create_driver, create_wait

# other modules
import importlib
import json
import requests
import subprocess
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as ec


driver = create_driver()
wait = create_wait(driver, 10)
driver.set_window_size(1920, 1080)

# Set vote url
vote_url = "https://www.alora.io/vote/"
ip_url = "https://api.my-ip.io/ip"
all_votable_sites = {1: "RuneLocus", 2: "", 3: "TopG", 4: "RSPS-List", 5: "", 6: "", 7: "MoparScape", 8: "", 9: ""}
vpn_regions_dict = {}


def main():
    vote()
    saveauth()
    changeip()


def vote():
    current_ip = getip()
    driver.get(vote_url)

    try:
        # Check if already voted on all websites
        already_voted_element = ".vote_content > h2:nth-child(2)"
        already_voted = wait.until(ec.presence_of_element_located((By.CSS_SELECTOR, already_voted_element)))
        print(f"{current_ip} | {already_voted.text}")
        saveauth()
    except TimeoutException as e:
        print(f"{current_ip} | You have not voted on all sites within the past 12 hours. Proceeding to vote...")

    votable_sites_dict = check_votable_sites()

    for siteid, value in votable_sites_dict.items():
        if not value:
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
                print(f"Voting on site: {site_name} (id: {siteid})")
                module = importlib.import_module(module_name)
                getattr(module, "vote")(driver, wait)
                print(f"Cleaning up {site_name} tab.")
                cleanup(window_handles)
            except ImportError:
                print(f"Module {module_name} not found!")


def saveauth():
    current_ip = getip()
    auth_code = getauth()
    votable_sites_dict = check_votable_sites()

    if any(value is False for value in votable_sites_dict.values()):
        print("At least one website is votable still!")
        print(votable_sites_dict)
    else:
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

        with open("auth_codes.json", "w") as file:
            json.dump(data, file, indent=4)


def getauth():
    authcode = wait.until(ec.presence_of_element_located((By.CSS_SELECTOR, "#notice-text")))
    return authcode.text


def changeip():
    output = subprocess.check_output("piactl get regions", shell=True).decode("utf-8")
    regions = output.strip().split("\n")

    vpn_regions_dict.clear()
    for index, region in enumerate(regions[1:], start=1):
        vpn_regions_dict[index] = region

    print("Disconnecting from VPN")
    subprocess.check_output("piactl disconnect", shell=True)

    output = subprocess.check_output("piactl get vpnip", shell=True).decode("utf-8")
    while output.strip() != "Unknown":
        output = subprocess.check_output("piactl get vpnip", shell=True).decode("utf-8")
        print("Waiting for VPN to disconnect.")
        print(output.strip() == "Unknown")

    region_to_connect = vpn_regions_dict[1] if len(vpn_regions_dict) >= 2 else vpn_regions_dict.get(1)

    subprocess.check_output(f"piactl set region {region_to_connect}", shell=True)
    subprocess.check_output("piactl connect", shell=True)

    output = subprocess.check_output("piactl get vpnip", shell=True).decode("utf-8")
    while output.strip() == "Unknown":
        output = subprocess.check_output("piactl get vpnip", shell=True).decode("utf-8")
        print("Waiting for VPN to connect.")
        print(output.strip())

    main()


def getip():
    return requests.get(ip_url).text


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


def cleanup(window_handles):
    driver.close()

    main_tab_handle = window_handles[0]
    driver.switch_to.window(main_tab_handle)


main()
driver.quit()
