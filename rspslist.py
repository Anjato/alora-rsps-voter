import sys
from captchasolver import recaptcha2_solver, hcaptcha_solver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as ec


def vote(driver, wait, log):
    captcha_type = ""

    # Spam check, refreshes page to get rid of it :D
    try:
        spam_check = wait.until(ec.presence_of_element_located((By.CSS_SELECTOR, "#captcha-image")))
        driver.refresh()
        while spam_check is not None:
            log.info("Spam check exists! Bypassing...")
            spam_check = wait.until(ec.presence_of_element_located((By.CSS_SELECTOR, "#captcha-image")))
            driver.refresh()
    except TimeoutException:
        log.info("Spam check does not exist. Proceeding with voting!")


    # Check for reCaptchaV2
    try:
        captcha = wait.until(ec.presence_of_element_located((By.CSS_SELECTOR, ".g-recaptcha:nth-child(1)")))
        hidden_recaptcha_response = wait.until(ec.invisibility_of_element_located((By.CSS_SELECTOR, "#g-recaptcha-response")))
        captcha_type = "recaptcha"
    except TimeoutException:
        captcha_type = None
        log.warning("reCaptchaV2 not found! Trying hCaptcha...")

    if captcha_type is None:
        # Check for hCaptcha
        try:
            captcha = wait.until(ec.presence_of_element_located((By.CSS_SELECTOR, ".h-captcha:nth-child(1)")))
            hidden_recaptcha_response = wait.until(ec.invisibility_of_element_located((By.CSS_SELECTOR, '[name="h-captcha-response"]')))
            captcha_type = "hcaptcha"
        except TimeoutException:
            captcha_type = None
            log.error("hCaptcha not found!")

    if captcha_type is None:
        log.critical("Cannot find reCaptcha or hCaptcha elements! Exiting application!")
        sys.exit(1)

    submit_vote_button = wait.until(ec.presence_of_element_located((By.CSS_SELECTOR, "#vote-btn")))
    driver.execute_script("arguments[0].removeAttribute('disabled')", submit_vote_button)

    sitekey = captcha.get_attribute("data-sitekey")
    url = driver.current_url
    log.info("Solving RSPS-List captcha...")

    while True:
        if captcha_type == "recaptcha":
            captcha_result = recaptcha2_solver(sitekey, url)
        else:
            captcha_result = hcaptcha_solver(sitekey, url)

        log.info(captcha_result)

        if captcha_result != False:
            break

    log.info(hidden_recaptcha_response)
    driver.execute_script("arguments[0].value = arguments[1];", hidden_recaptcha_response, captcha_result)

    submit_vote_button.click()

    try:
        vote_success = wait.until(ec.presence_of_element_located((By.CSS_SELECTOR, ".alert-success")))
        log.info("Voted on RSPS-List successfully!")
    except TimeoutException:
        try:
            vote_failed = wait.until(ec.presence_of_element_located((By.CSS_SELECTOR, ".alert-danger")))
            log.error(vote_failed.text)
        except TimeoutException:
            log.critical("Could not retrieve vote status!")
            log.info(driver.page_source)
            sys.exit(1)
