from captchasolver import hcaptcha_solver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as ec


def vote(driver, wait):
    captcha = wait.until(ec.element_to_be_clickable((By.CSS_SELECTOR, ".h-captcha")))
    hidden_element_one = wait.until(ec.invisibility_of_element_located((By.CSS_SELECTOR, '[name="g-recaptcha-response"]')))
    hidden_element_two = wait.until(ec.invisibility_of_element_located((By.CSS_SELECTOR, '[name="h-captcha-response"]')))
    submit_vote_button = wait.until(ec.element_to_be_clickable((By.CSS_SELECTOR, "#submit")))

    sitekey = captcha.get_attribute("data-sitekey")
    url = driver.current_url

    print("Solving TopG captcha...")
    captcha_result = hcaptcha_solver(sitekey, url)

    driver.execute_script("arguments[0].value = arguments[1];", hidden_element_one, captcha_result)
    driver.execute_script("arguments[0].value = arguments[1];", hidden_element_two, captcha_result)

    submit_vote_button.click()

    try:
        vote_success = wait.until(ec.presence_of_element_located((By.CSS_SELECTOR, ".alert-success")))
        print("Voted on TopG successfully!")
    except TimeoutException as e:
        vote_failed = wait.until(ec.presence_of_element_located((By.CSS_SELECTOR, ".alert-danger")))
        print("TopG vote FAILED!")
        print(f"ERROR: {e}")

