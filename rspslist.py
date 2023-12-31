from captchasolver import recaptcha2_solver, hcaptcha_solver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as ec


def vote(driver, wait, log):
    captcha_type = None
    captcha = None
    hidden_recaptcha_response = None

    # Spam check, refreshes page to get rid of it :D
    try:
        spam_check = wait.until(ec.presence_of_element_located((By.CSS_SELECTOR, "#captcha-image")))
        driver.refresh()
        while spam_check is not None:
            log.info("RSPS-List | Spam check exists! Bypassing...")
            spam_check = wait.until(ec.presence_of_element_located((By.CSS_SELECTOR, "#captcha-image")))
            driver.refresh()
    except TimeoutException:
        log.info("RSPS-List | Spam check does not exist. Proceeding with voting!")

    # Check for reCaptchaV2
    try:
        captcha = wait.until(ec.presence_of_element_located((By.CSS_SELECTOR, ".g-recaptcha:nth-child(1)")))
        hidden_recaptcha_response = wait.until(ec.invisibility_of_element_located((By.CSS_SELECTOR, "#g-recaptcha-response")))
        captcha_type = "recaptcha"
    except TimeoutException:
        captcha_type = None
        log.warning("RSPS-List | reCaptchaV2 not found! Trying hCaptcha...")

    if captcha_type is None:
        # Check for hCaptcha
        try:
            captcha = wait.until(ec.presence_of_element_located((By.CSS_SELECTOR, ".h-captcha:nth-child(1)")))
            hidden_recaptcha_response = wait.until(ec.invisibility_of_element_located((By.CSS_SELECTOR, '[name="h-captcha-response"]')))
            captcha_type = "hcaptcha"
        except TimeoutException:
            captcha_type = None
            log.error("RSPS-List | hCaptcha not found!")

    if captcha_type is None:
        log.error("RSPS-List | Cannot find reCaptcha or hCaptcha elements!")

    submit_vote_button = wait.until(ec.presence_of_element_located((By.CSS_SELECTOR, "#vote-btn")))
    driver.execute_script("arguments[0].removeAttribute('disabled')", submit_vote_button)

    if captcha is not None:
        sitekey = captcha.get_attribute("data-sitekey")
    else:
        log.error("RSPS-List | Captcha element not found! Trying again later")
        return

    url = driver.current_url
    log.info("RSPS-List | Solving RSPS-List captcha...")

    while True:
        if captcha_type == "recaptcha":
            captcha_result = recaptcha2_solver(sitekey, url, log)
        else:
            captcha_result = hcaptcha_solver(sitekey, url, log)

        # Python is fucking weird. Even though it returns a solution, an empty string is considered 'falsy' and
        # a non-empty string is considered 'truthy'. What the hell???????????
        if captcha_result:
            break

    if hidden_recaptcha_response is not None:
        driver.execute_script("arguments[0].value = arguments[1];", hidden_recaptcha_response, captcha_result)
    else:
        log.error("Hidden captcha response element not found! Trying again later")
        return

    submit_vote_button.click()

    try:
        vote_success = wait.until(ec.presence_of_element_located((By.CSS_SELECTOR, ".alert-success")))
        log.info("RSPS-List | Voted on RSPS-List successfully!")
    except TimeoutException:
        try:
            vote_failed = wait.until(ec.presence_of_element_located((By.CSS_SELECTOR, ".alert-danger")))
            log.error(f"RSPS-List | {vote_failed.text}")
        except TimeoutException:
            log.error("RSPS-List | Could not retrieve vote status!")
            raise Exception
