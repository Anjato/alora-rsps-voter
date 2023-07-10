import sys
from captchasolver import recaptcha2_solver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as ec


def vote(driver, wait, *args):

    captcha = wait.until(ec.element_to_be_clickable((By.CSS_SELECTOR, ".g-recaptcha")))
    hidden_recaptcha_response = wait.until(ec.invisibility_of_element_located((By.CSS_SELECTOR, '[name="g-recaptcha-response"]')))
    submit_vote_button = wait.until(ec.element_to_be_clickable((By.CSS_SELECTOR, "button.btn:nth-child(5)")))

    sitekey = captcha.get_attribute("data-sitekey")
    url = driver.current_url

    print("Solving MoparScape captcha...")

    while True:
        captcha_result = recaptcha2_solver(sitekey, url)

        if captcha_result != False:
            break

    driver.execute_script("arguments[0].value = arguments[1];", hidden_recaptcha_response, captcha_result)

    submit_vote_button.click()

    try:
        vote_success = wait.until(ec.presence_of_element_located((By.CSS_SELECTOR, ".alert-success")))
        print("Voted on MoparScape successfully!")
    except TimeoutException:
        try:
            vote_failed = wait.until(ec.presence_of_element_located((By.CSS_SELECTOR, ".alert-danger")))
            print(f"ERROR: {vote_failed.text}")
        except TimeoutException:
            print("FATAL: Could not retrieve vote status!")
            print(driver.page_source)
            sys.exit(1)
